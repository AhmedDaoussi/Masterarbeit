import os
import pandas as pd
import matplotlib.pyplot as plt
import zipfile
import tarfile
import zipfile
import pandas as pd
import os
import re  # Reguläre Ausdrücke für das Muster-Matching

region_mapping = {
    1: "Germany",
    2: "Baltics",
    3: "Turkey",
    4: "Balkans",
    5: "France",
    6: "Belgium",
    7: "Austria",
    8: "Switzerland",
    9: "Netherlands",
    10: "Poland",
    11: "Czech Republic",
    12: "DenmarkWest",
    13: "DenmarkEast",
    14: "SloCro",
    15: "SWE1and2",
    16: "IT_CN",
    17: "England",
    18: "IT_N",
    19: "Spain",
    20: "Romania",
    21: "Slovakia",
    22: "Hungary",
    23: "Bulgaria",
    24: "Greece",
    25: "Portugal",
    26: "Norway",
    27: "Finland",
    28: "IT_CS",
    29: "SWE3",
    30: "SWE4",
    31: "IT_S",
    32: "IT_SI",
    33: "IT_SA",
    34: "IT_CA"
}


class Evaluation:

    # Constructor (initializer method)
    def __init__(self, folder_path, weather_year, start_year, end_year):
        # Instance attribute
        self.folder_path = folder_path
        self.weather_year = weather_year
        self.start_year = start_year
        self.end_year = end_year
        self.path_low_cut = "D:/Masterarbeit/lowcut.xlsx"
        self.kwid_regid_map = "D:/Masterarbeit/KWID_REGID_MAPPING.xlsx"

    def concatenate_and_process_yearly_data(self):

        low_cut_df = pd.read_excel(self.path_low_cut)
        all_dataframes = []

        # Über die Jahre im angegebenen Bereich iterieren
        for year in range(self.start_year, self.end_year + 1):
            # Über alle Dateien im Ordner iterieren
            for file_name in os.listdir(self.folder_path + f'/{self.weather_year}/regresults'):
                # Prüfen, ob die Datei dem Muster entspricht
                if f"RegResults_{year}_" in file_name and file_name.endswith('.dat'):
                    file_path = os.path.join(self.folder_path + f'/{self.weather_year}/regresults/', file_name)

                    # Datei lesen
                    df = pd.read_csv(file_path, delimiter=',', header=None)

                    # Bearbeitung der Datei
                    df1 = df.iloc[10:].reset_index(drop=True)
                    column_names = ['VARID', 'REGID', 'SIMID', 'JAHR', 'ZENR', 'MARKTPREIS', 'REGIONENMARKUP',
                                    'STARTKOSTEN']
                    df1 = pd.DataFrame([x.split(';') for x in df1[0]])

                    # Sicherstellen, dass die Spaltenanzahl passt
                    df2 = df1.iloc[:, :6].copy()
                    df2.columns = column_names[:df2.shape[1]]
                    df2['STARTKOSTEN'] = df1.iloc[:, 53]
                    df2['REGIONENMARKUP'] = df1.iloc[:, 7]
                    # Daten zur Liste hinzufügen
                    all_dataframes.append(df2)

        # Alle DataFrames zusammenfügen
        if all_dataframes:
            combined_df = pd.concat(all_dataframes, ignore_index=True)
            # Datentypen umwandeln
            for column in combined_df.columns:
                combined_df[column] = pd.to_numeric(combined_df[column], errors='coerce')

            # Sortieren der Daten
            sorted_df = combined_df.sort_values(by=['VARID', 'JAHR', 'REGID', 'ZENR'],
                                                ascending=[True, True, True, True]).reset_index(drop=True)
            # Sicherstellen, dass JAHR und ZENR gültige Werte haben

            sorted_df = sorted_df[sorted_df['ZENR'].between(1, 8760)]  # Stundenzahl im gültigen Bereich

            # Berechnung der DATETIME
            sorted_df['DATETIME'] = pd.to_datetime(
                sorted_df['JAHR'].astype(str) + '-01-01',  # 1. Januar des Jahres
                format='%Y-%m-%d'
            ) + pd.to_timedelta(sorted_df['ZENR'] - 1, unit='h')  # Stunden hinzufügen
            sorted_df.rename(columns={'ZENR': 'PKTNR'}, inplace=True)
            sorted_df = pd.merge(sorted_df, low_cut_df, on=['JAHR', 'PKTNR'])
            sorted_df['FINAL_MARKTPREIS'] = (sorted_df['MARKTPREIS'] + sorted_df['REGIONENMARKUP'] + sorted_df[
                'STARTKOSTEN']) * sorted_df['LOW_CUT_TERM']
            sorted_df.drop(columns={'VARID_y', 'REGID_y'}, inplace=True)
            sorted_df.rename(columns={'VARID_x': 'VARID', 'REGID_x': 'REGID'}, inplace=True)
            sorted_df = sorted_df[['VARID', 'REGID', 'SIMID', 'JAHR', 'PKTNR', 'DATETIME', 'STARTKOSTEN',
                                   'REGIONENMARKUP', 'LOW_CUT_TERM', 'MARKTPREIS', 'FINAL_MARKTPREIS']]
            sorted_df = sorted_df.sort_values(by=['VARID', 'JAHR', 'REGID', 'PKTNR'],
                                              ascending=[True, True, True, True]).reset_index(drop=True)

            sorted_df['REGION_NAME'] = sorted_df['REGID'].map(region_mapping)
            pivot_df = sorted_df.groupby(['REGION_NAME', 'JAHR'])['FINAL_MARKTPREIS'].mean().unstack()
            pivot_df.to_excel(f'{self.folder_path}' + f'/{self.weather_year}' +
                              f'/yearly_values_wy_{self.weather_year}.xlsx')
            return sorted_df
        else:
            print(f"Keine Dateien für die Jahre {self.start_year} bis {self.end_year} gefunden.")
            return pd.DataFrame()  # Leerer DataFrame, falls keine Dateien gefunden werden

    # Funktion zum Erstellen der Plots
    def plot_yearly_prices(self, result_df):
        pivot_df = result_df.groupby(['REGION_NAME', 'JAHR'])['FINAL_MARKTPREIS'].mean().unstack()

        # Sicherstellen, dass der Ordner existiert
        yearly_plots_folder = os.path.join(self.folder_path + f'/{self.weather_year}/', 'Yearly_Prices_Plots')
        os.makedirs(yearly_plots_folder, exist_ok=True)

        for region in pivot_df.index:  # Iteriere über alle Regionen
            # Daten für die Region
            years = pivot_df.columns  # Jahre
            prices = pivot_df.loc[region].values  # Preise

            # Erstellen des Plots
            plt.figure(figsize=(10, 6))
            plt.step(years, prices, where='mid', label=f'{region}', linewidth=2)
            plt.title(f'Yearly Price Development: {region}')
            plt.xlabel('Year')
            plt.ylabel('Average Price')
            plt.grid(True)
            plt.legend()

            # Speichern des Plots
            plot_file = os.path.join(yearly_plots_folder, f'{region}_yearly_prices_wy_{self.weather_year}.png')
            plt.savefig(plot_file)
            plt.close()

            print(f"Plot gespeichert für Region: {region} -> {plot_file}")

    def plot_price_duration_curve(self, result_df):
        plots_folder = os.path.join(self.folder_path + f'/{self.weather_year}/', 'PRICE_DURATION_CURVE')
        os.makedirs(plots_folder, exist_ok=True)
        for region in result_df['REGION_NAME'].unique():
            for jahr in result_df[result_df['REGION_NAME'] == region]['JAHR'].unique():
                # Filtere Daten für die aktuelle Region und das Jahr
                filtered_df = result_df[(result_df['REGION_NAME'] == region) & (result_df['JAHR'] == jahr)]

                # Überspringe, wenn keine Daten vorhanden
                if filtered_df.empty:
                    continue

                region_name = f"Region_{region}"  # Optional, hier könnte ein Mapping für Region_Name verwendet werden

                # Plot_Price_Duration_curve
                sorted_df = filtered_df.sort_values(by='FINAL_MARKTPREIS', ascending=False).reset_index()
                plt.figure(figsize=(10, 6))
                plt.plot(range(1, len(sorted_df) + 1), sorted_df['FINAL_MARKTPREIS'], label='Descending MARKET_PRICES')
                plt.title(f'Descending MARKET_PRICES ({region_name}, {jahr})')
                plt.xlabel('HOURS (1-8760)')
                plt.ylabel('FINAL_MARKET_PRICES')
                plt.grid(True)
                plt.legend()
                plt.tight_layout()

                # Speichert den Plot im Ordner
                file_path = os.path.join(plots_folder, f'{region_name}_{jahr}PRICE_DURATION_CURVE.png')
                plt.savefig(file_path)
                plt.close()
                plt.show()

    def evaluate_power_plant_files(self):
        kwid_regid_map = pd.read_excel(self.kwid_regid_map)
        kw_dict = {4832: 'pv_2033_DE00', 4866: 'pv_2033_BT', 4852: 'pv_2033_TR00', 4857: 'pv_2033_BA', 4823: 'pv_2033_FR00', 4802: 'pv_2033_BE00', 4819: 'pv_2033_AT00', 4806: 'pv_2033_CH00', 4855: 'pv_2033_NL00', 4878: 'pv_2033_PL00', 4817: 'pv_2033_CZ00', 4824: 'pv_2033_DKW1', 4827: 'pv_2033_DKE1', 4848: 'pv_2033_SC', 4845: 'pv_2033_SE01', 3678: 'pv_2033_ITCN', 4861: 'pv_2033_UK00', 4865: 'pv_2033_ITN1', 4805: 'csp_2033_ES00', 4803: 'pv_2033_ES00', 4809: 'pv_2033_RO00', 4833: 'pv_2033_SK00', 4872: 'pv_2033_HU00', 4797: 'pv_2033_BG00', 4838: 'pv_2033_GR00', 4812: 'pv_2033_PT00', 4869: 'pv_2033_NO', 4875: 'pv_2033_FI00', 3295: 'pv_2033_ITCS', 4839: 'pv_2033_SE03', 4843: 'pv_2033_SE04', 3675: 'pv_2033_ITS1', 4863: 'pv_2033_ITSI', 2923: 'pv_2033_ITSA', 663: 'pv_2033_ITCA', 4748: 'wind_on_2033_DE00_shape_a', 4782: 'wind_on_2033_BT_shape_a', 4767: 'wind_on_2033_TR00_shape_a', 4773: 'wind_on_2033_BA_shape_a', 4739: 'wind_on_2033_FR00_shape_a', 4716: 'wind_on_2033_BE00_shape_a', 4734: 'wind_on_2033_AT00_shape_a', 4722: 'wind_on_2033_CH00_shape_a', 4770: 'wind_on_2033_NL00_shape_a', 4796: 'wind_on_2033_PL00_shape_a', 4731: 'wind_on_2033_CZ00_shape_a', 4740: 'wind_on_2033_DKW1_shape_a', 4743: 'wind_on_2033_DKE1_shape_a', 4764: 'wind_on_2033_SC_shape_a', 4761: 'wind_on_2033_SE01_shape_a', 4715: 'wind_on_2033_ITCN_shape_a', 4776: 'wind_on_2033_UK00_shape_a', 4781: 'wind_on_2033_ITN1_shape_a', 4721: 'wind_on_2033_ES00_shape_a', 4725: 'wind_on_2033_RO00_shape_a', 4749: 'wind_on_2033_SK00_shape_a', 4788: 'wind_on_2033_HU00_shape_a', 4713: 'wind_on_2033_BG00_shape_a', 4752: 'wind_on_2033_GR00_shape_a', 4730: 'wind_on_2033_PT00_shape_a', 4785: 'wind_on_2033_NO_shape_a', 4791: 'wind_on_2033_FI00_shape_a', 4719: 'wind_on_2033_ITCS_shape_a', 4755: 'wind_on_2033_SE03_shape_a', 4758: 'wind_on_2033_SE04_shape_a', 4723: 'wind_on_2033_ITSI_shape_a', 4726: 'wind_on_2033_ITS1_shape_a', 4728: 'wind_on_2033_ITSA_shape_a', 679: 'wind_on_2033_ITCA_shape_a', 4718: 'wind_on_2033_ITCN_shape_b', 4714: 'wind_on_2033_ITN1_shape_b', 4720: 'wind_on_2033_ITCS_shape_b', 4724: 'wind_on_2033_ITS1_shape_b', 4727: 'wind_on_2033_ITSI_shape_b', 4729: 'wind_on_2033_ITSA_shape_b', 1289: 'wind_on_2033_ITCA_shape_b', 4732: 'wind_on_2033_DE00_shape_b', 4733: 'wind_on_2033_BT_shape_b', 4735: 'wind_on_2033_TR00_shape_b', 4736: 'wind_on_2033_BA_shape_b', 4737: 'wind_on_2033_FR00_shape_b', 4742: 'wind_on_2033_BE00_shape_b', 4745: 'wind_on_2033_AT00_shape_b', 4747: 'wind_on_2033_CH00_shape_b', 4750: 'wind_on_2033_NL00_shape_b', 4751: 'wind_on_2033_PL00_shape_b', 4753: 'wind_on_2033_CZ00_shape_b', 4754: 'wind_on_2033_DKW1_shape_b', 4756: 'wind_on_2033_DKE1_shape_b', 4760: 'wind_on_2033_SC_shape_b', 4762: 'wind_on_2033_SE01_shape_b', 4763: 'wind_on_2033_UK00_shape_b', 4765: 'wind_on_2033_ES00_shape_b', 4766: 'wind_on_2033_RO00_shape_b', 4768: 'wind_on_2033_SK00_shape_b', 4769: 'wind_on_2033_HU00_shape_b', 4772: 'wind_on_2033_BG00_shape_b', 4774: 'wind_on_2033_GR00_shape_b', 4775: 'wind_on_2033_PT00_shape_b', 4778: 'wind_on_2033_NO_shape_b', 4779: 'wind_on_2033_FI00_shape_b', 4780: 'wind_on_2033_SE03_shape_b', 4783: 'wind_on_2033_SE04_shape_b', 4746: 'wind_off_2033_DE00_shape_a', 4738: 'wind_off_2033_FR00_shape_a', 4717: 'wind_off_2033_BE00_shape_a', 4771: 'wind_off_2033_NL00_shape_a', 4741: 'wind_off_2033_DKW1_shape_a', 4744: 'wind_off_2033_DKE1_shape_a', 4777: 'wind_off_2033_UK00_shape_a', 4759: 'wind_off_2033_SE04_shape_a', 4757: 'wind_off_2033_SE03_shape_a', 4794: 'wind_off_2033_PL00_shape_a', 4784: 'wind_off_2033_DE00_shape_b', 4786: 'wind_off_2033_UK00_shape_b', 64: 'wind_off_2033_FI00_shape_a', 275: 'wind_off_2033_BT_shape_a', 1639: 'wind_off_2033_NO_shape_a', 955: 'wind_off_2033_ES00_shape_a', 1830: 'wind_off_2033_PT00_shape_a', 1646: 'wind_off_2033_ITSA_shape_a', 1642: 'wind_off_2033_ITSI_shape_a'}

        kw_dict_selc = {4832: 'pv_2033_DE00', 4823: 'pv_2033_FR00', 4855: 'pv_2033_NL00', 4878: 'pv_2033_PL00', 3678: 'pv_2033_ITCN', 4865: 'pv_2033_ITN1', 4805: 'csp_2033_ES00', 4803: 'pv_2033_ES00', 4797: 'pv_2033_BG00', 3295: 'pv_2033_ITCS', 3675: 'pv_2033_ITS1', 4863: 'pv_2033_ITSI', 2923: 'pv_2033_ITSA', 663: 'pv_2033_ITCA', 4748: 'wind_on_2033_DE00_shape_a', 4739: 'wind_on_2033_FR00_shape_a', 4770: 'wind_on_2033_NL00_shape_a', 4796: 'wind_on_2033_PL00_shape_a', 4715: 'wind_on_2033_ITCN_shape_a', 4781: 'wind_on_2033_ITN1_shape_a', 4721: 'wind_on_2033_ES00_shape_a', 4713: 'wind_on_2033_BG00_shape_a', 4719: 'wind_on_2033_ITCS_shape_a', 4723: 'wind_on_2033_ITSI_shape_a', 4726: 'wind_on_2033_ITS1_shape_a', 4728: 'wind_on_2033_ITSA_shape_a', 679: 'wind_on_2033_ITCA_shape_a', 4718: 'wind_on_2033_ITCN_shape_b', 4714: 'wind_on_2033_ITN1_shape_b', 4720: 'wind_on_2033_ITCS_shape_b', 4724: 'wind_on_2033_ITS1_shape_b', 4727: 'wind_on_2033_ITSI_shape_b', 4729: 'wind_on_2033_ITSA_shape_b', 1289: 'wind_on_2033_ITCA_shape_b', 4732: 'wind_on_2033_DE00_shape_b', 4737: 'wind_on_2033_FR00_shape_b', 4750: 'wind_on_2033_NL00_shape_b', 4751: 'wind_on_2033_PL00_shape_b', 4765: 'wind_on_2033_ES00_shape_b', 4772: 'wind_on_2033_BG00_shape_b', 4746: 'wind_off_2033_DE00_shape_a', 4738: 'wind_off_2033_FR00_shape_a', 4771: 'wind_off_2033_NL00_shape_a', 4794: 'wind_off_2033_PL00_shape_a', 4784: 'wind_off_2033_DE00_shape_b', 955: 'wind_off_2033_ES00_shape_a', 1646: 'wind_off_2033_ITSA_shape_a', 1642: 'wind_off_2033_ITSI_shape_a'}
        all_dataframes = []

        # ZIP-Dateien für beide möglichen Formate durchsuchen
        zip_files = [f"{self.folder_path}/{self.weather_year}/daoussi_Wetterjahr_{x}_{self.weather_year}.zip" for x in
                     ["a", "b"]]

        # Regulärer Ausdruck für das Dateiformat: SQLLoader_KWResults_YYYY_0_XXX.dat
        pattern = re.compile(r"daoussi_Wetterjahr_[b]_\d{4}/SQLLoader/SQLLoader_KWResults_\d{4}_0_\d+\.dat")

        for zip_file in zip_files:
            if not os.path.exists(zip_file):
                print(f"ZIP-Datei nicht gefunden: {zip_file}")
                continue

            with zipfile.ZipFile(zip_file, 'r') as zip_ref:
                # Alle Dateien im ZIP-Archiv auflisten
                file_list = zip_ref.namelist()

                # Nur relevante Dateien auswählen, die dem Muster entsprechen
                target_files = [f for f in file_list if pattern.match(f)]

                if not target_files:
                    print(f"Keine passenden Dateien in {zip_file} gefunden.")
                    continue

                columns = [
                    "VARID", "KWID", "SIMID", "JAHR", "ZENR", "RANGLISTE", "DB", "KAPREVENUE", "SEKRESREVENUE",
                    "MINRESREVENUE", "VARKOSTEN", "PVERF", "PINSTALL", "EINSATZ", "ZWANG", "MINRESERVE",
                    "SEKRESERVE", "FREIELSTG", "VERFB", "REVISIONEN", "AUSFALL", "KONTSTUNDEN", "STARTKOSTEN"
                ]

                # Dateien verarbeiten
                for file in target_files:
                    with zip_ref.open(file) as f:
                        df = pd.read_csv(f, delimiter=',', header=None)
                        df1 = df.iloc[10:].reset_index(drop=True)  # Entfernt die ersten 10 Zeilen

                        # Spalten aufteilen, falls CSV mit `;` getrennt ist
                        df1 = pd.DataFrame([x.split(';') for x in df1[0]])
                        df1.columns = columns[:df1.shape[1]]

                        # Relevante Spalten auswählen
                        df1 = df1[["KWID", "JAHR", "ZENR", "PINSTALL", "EINSATZ", "VARKOSTEN"]]

                        # KWID in numerischen Typ umwandeln
                        df1["KWID"] = pd.to_numeric(df1["KWID"], errors='coerce')

                        # Filter: Nur KWIDs, die im `self.kw_dict_selc` vorhanden sind
                        df1 = df1[df1["KWID"].astype(int).isin(kw_dict_selc.keys())]

                        all_dataframes.append(df1)
        if all_dataframes:
            combined_df = pd.concat(all_dataframes, ignore_index=True)
            for column in combined_df.columns:
                combined_df[column] = pd.to_numeric(combined_df[column], errors='coerce')
            #sorted_df = combined_df.sort_values(by='ZENR', ascending=True)

            sorted_df = pd.merge(combined_df, kwid_regid_map, on=['KWID'])
            sorted_df.rename(columns={'ZENR':'PKTNR'},inplace=True)
            market_price_data = []
            for year in range(2023, 2051):
                # Read the market price data for the given year
                temp_df = pd.read_excel(os.path.join(
                    self.folder_path, f'{self.weather_year}/hourly_prices_for_year_{year}_wy_{self.weather_year}.xlsx'
                ))

                # Append to the list
                market_price_data.append(temp_df)

            # Concatenate all data into a single DataFrame
            market_price_all_df = pd.concat(market_price_data, ignore_index=True)

            # Convert 'JAHR' to integer (important for merging)
            market_price_all_df['JAHR'] = market_price_all_df['JAHR'].astype(int)
            sorted_df = sorted_df.merge(market_price_all_df, on=['REGID', 'PKTNR', 'JAHR'], how='left')

            sorted_df['Deckungsbeitrag_hr'] = (sorted_df['FINAL_MARKTPREIS'] +sorted_df['VARKOSTEN']) * sorted_df[
                'EINSATZ']
            result_list = []
            for (year, kwid), group in sorted_df.groupby(['JAHR', 'KWID']):
                if group['PINSTALL'].mean() > 0:
                    denominator = (group['PINSTALL'].mean() * 1000)
                    if pd.notna(denominator) and denominator != 0:
                        average_profit = group['Deckungsbeitrag_hr'].sum() / denominator
                    else:
                        average_profit = 0  # Oder ein geeigneter Standardwert
                else:
                    average_profit = 'PINSTALL = 0'  # Mark the issue for the entry
                result_list.append({'JAHR': year, 'KWID': kwid, 'Annual_Profit/installed_kw': average_profit})

            result_df = pd.DataFrame(result_list)
            result_df['Kraftwerk'] = result_df['KWID'].map(kw_dict)
            result_df["Technology"] = result_df["Kraftwerk"].apply(
                lambda x: "_".join(x.split("_")[:2]) if pd.notna(x) else None
            )
            result_df["Shape"] = result_df["Kraftwerk"].apply(
                lambda x: "shape_a" if "shape_a" in x else ("shape_b" if "shape_b" in x else "pv") if pd.notna(
                    x) else None
            )
            result_df = pd.merge(result_df, kwid_regid_map, on='KWID')
            result_df['Region'] = result_df['REGID'].map(region_mapping)
            result_df = result_df[['JAHR', 'Region', 'REGID', 'Technology', 'Shape', 'KWID', 'Kraftwerk',
                                   'Annual_Profit/installed_kw']]

            if isinstance(result_df, list):
                result_df = pd.DataFrame(result_df)  # Konvertiere Liste in DataFrame
            if 'REGID' in result_df.columns:
                result_df['REGID'] = result_df['REGID'].astype(int)
            else:
                print("Warnung: Spalte 'REGID' existiert nicht im DataFrame")
            result_df['Annual_Profit/installed_kw'] = pd.to_numeric(result_df['Annual_Profit/installed_kw'],
                                                                    errors='coerce')
            result_df['Annual_Profit/installed_kw'] = result_df['Annual_Profit/installed_kw'].round(1)
            output_path = os.path.join(
                self.folder_path,
                f"{self.weather_year}/kw_profitability_2/kw_profitability_{self.weather_year}.xlsx"
            )
            os.makedirs(os.path.dirname(output_path), exist_ok=True)  # Ensure the directory exists
            result_df.to_excel(output_path, index=False)

            # Confirm save operation
            print(f"Results saved to: {output_path}")





    def compute_hr_prices(self):

        low_cut_df = pd.read_excel(self.path_low_cut)
        # Über die Jahre im angegebenen Bereich iterieren
        for year in range(self.start_year, self.end_year + 1):
            all_dataframes = []

            # ZIP-Dateien für beide möglichen Formate durchsuchen
            zip_files = [f"{self.folder_path}/{self.weather_year}/daoussi_Wetterjahr_{x}_{self.weather_year}.zip" for x
                         in ["a", "b"]]

            # Regulärer Ausdruck für das Dateiformat: SQLLoader_KWResults_YYYY_0_XXX.dat
            pattern = re.compile(r'daoussi_Wetterjahr_[ab]_\d{4}/SQLLoader/SQLLoader_RegResults_' + str(year) + r'_0_\d+\.dat')

            for zip_file in zip_files:
                if not os.path.exists(zip_file):
                    print(f"ZIP-Datei nicht gefunden: {zip_file}")
                    continue

                with zipfile.ZipFile(zip_file, 'r') as zip_ref:
                    # Alle Dateien im ZIP-Archiv auflisten
                    file_list = zip_ref.namelist()

                    # Nur relevante Dateien auswählen, die dem Muster entsprechen
                    target_files = [f for f in file_list if pattern.match(f)]

                    if not target_files:
                        print(f"Keine passenden Dateien in {zip_file} gefunden.")
                        continue

                    columns = [
                        "VARID", "KWID", "SIMID", "JAHR", "ZENR", "RANGLISTE", "DB", "KAPREVENUE", "SEKRESREVENUE",
                        "MINRESREVENUE", "VARKOSTEN", "PVERF", "PINSTALL", "EINSATZ", "ZWANG", "MINRESERVE",
                        "SEKRESERVE", "FREIELSTG", "VERFB", "REVISIONEN", "AUSFALL", "KONTSTUNDEN", "STARTKOSTEN"
                    ]

                    # Dateien verarbeiten
                    for file in target_files:
                        with zip_ref.open(file) as f:
                            df = pd.read_csv(f, delimiter=',', header=None)

                            # Bearbeitung der Datei
                            df1 = df.iloc[10:].reset_index(drop=True)
                            column_names = ['VARID', 'REGID', 'SIMID', 'JAHR', 'ZENR', 'MARKTPREIS', 'REGIONENMARKUP',
                                            'STARTKOSTEN']
                            df1 = pd.DataFrame([x.split(';') for x in df1[0]])

                            # Sicherstellen, dass die Spaltenanzahl passt
                            df2 = df1.iloc[:, :6].copy()
                            df2.columns = column_names[:df2.shape[1]]
                            df2['STARTKOSTEN'] = df1.iloc[:, 53]
                            df2['REGIONENMARKUP'] = df1.iloc[:, 7]
                            # Daten zur Liste hinzufügen
                            all_dataframes.append(df2)

        # Alle DataFrames zusammenfügen
            if all_dataframes:
                combined_df = pd.concat(all_dataframes, ignore_index=True)
                for column in combined_df.columns:
                    combined_df[column] = pd.to_numeric(combined_df[column], errors='coerce')

                # Sortieren der Daten
                sorted_df = combined_df.sort_values(by=['VARID', 'JAHR', 'REGID', 'ZENR'],
                                                    ascending=[True, True, True, True]).reset_index(drop=True)
                # Sicherstellen, dass JAHR und ZENR gültige Werte haben

                sorted_df = sorted_df[sorted_df['ZENR'].between(1, 8760)]  # Stundenzahl im gültigen Bereich

                # Berechnung der DATETIME
                sorted_df['DATETIME'] = pd.to_datetime(
                    sorted_df['JAHR'].astype(str) + '-01-01',  # 1. Januar des Jahres
                    format='%Y-%m-%d'
                ) + pd.to_timedelta(sorted_df['ZENR'] - 1, unit='h')  # Stunden hinzufügen
                sorted_df.rename(columns={'ZENR': 'PKTNR'}, inplace=True)
                sorted_df = pd.merge(sorted_df, low_cut_df, on=['JAHR', 'PKTNR'])
                sorted_df['FINAL_MARKTPREIS'] = (sorted_df['MARKTPREIS'] + sorted_df['REGIONENMARKUP'] + sorted_df[
                    'STARTKOSTEN']) * sorted_df['LOW_CUT_TERM']
                sorted_df.drop(columns={'VARID_y', 'REGID_y'}, inplace=True)
                sorted_df.rename(columns={'VARID_x': 'VARID', 'REGID_x': 'REGID'}, inplace=True)
                sorted_df = sorted_df[['VARID', 'REGID', 'SIMID', 'JAHR', 'PKTNR', 'DATETIME', 'STARTKOSTEN',
                                       'REGIONENMARKUP', 'LOW_CUT_TERM', 'MARKTPREIS', 'FINAL_MARKTPREIS']]
                sorted_df = sorted_df.sort_values(by=['VARID', 'JAHR', 'REGID', 'PKTNR'],
                                                  ascending=[True, True, True, True]).reset_index(drop=True)

                sorted_df['REGION_NAME'] = sorted_df['REGID'].map(region_mapping)
                sorted_df = sorted_df[['REGID','JAHR','PKTNR','FINAL_MARKTPREIS']]


                sorted_df.to_excel(f'{self.folder_path}' + f'/{self.weather_year}' +
                                  f'/hourly_prices_for_year_{year}_wy_{self.weather_year}.xlsx')

                print('a')



