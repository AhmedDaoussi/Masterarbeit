import os
import pandas as pd
import openpyxl
import matplotlib.pyplot as plt
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

def concatenate_and_process_yearly_data(folder_path, start_year, end_year):
    # Liste für DataFrames
    path_low_cut = "C:/Users/ahmed/Desktop/Masterarbeit/lowcut.xlsx"
    low_cut_df = pd.read_excel(path_low_cut)
    all_dataframes = []

    # Über die Jahre im angegebenen Bereich iterieren
    for year in range(start_year, end_year + 1):
        # Über alle Dateien im Ordner iterieren
        for file_name in os.listdir(folder_path+'/regresults/'):
            # Prüfen, ob die Datei dem Muster entspricht
            if f"RegResults_{year}_" in file_name and file_name.endswith('.dat'):
                file_path = os.path.join(folder_path+'/regresults/', file_name)

                # Datei lesen
                df = pd.read_csv(file_path, delimiter=',', header=None)

                # Bearbeitung der Datei
                df1 = df.iloc[10:].reset_index(drop=True)
                column_names = ['VARID', 'REGID', 'SIMID', 'JAHR', 'ZENR', 'MARKTPREIS','REGIONENMARKUP','STARTKOSTEN']
                df1 = pd.DataFrame([x.split(';') for x in df1[0]])

                # Sicherstellen, dass die Spaltenanzahl passt
                df2 = df1.iloc[:, :6].copy()
                df2.columns = column_names[:df2.shape[1]]
                df2['STARTKOSTEN'] = df1.iloc[:,53]
                df2['REGIONENMARKUP'] = df1.iloc[:,7]
                # Daten zur Liste hinzufügen
                all_dataframes.append(df2)

    # Alle DataFrames zusammenfügen
    if all_dataframes:
        combined_df = pd.concat(all_dataframes, ignore_index=True)
        # Datentypen umwandeln
        for column in combined_df.columns:
            combined_df[column] = pd.to_numeric(combined_df[column], errors='coerce')

        # Sortieren der Daten
        sorted_df = combined_df.sort_values(by=['VARID','JAHR', 'REGID', 'ZENR'], ascending=[True,True, True, True]).reset_index(drop=True)
        # Sicherstellen, dass JAHR und ZENR gültige Werte haben

        sorted_df = sorted_df[sorted_df['ZENR'].between(1, 8760)]  # Stundenzahl im gültigen Bereich

        # Berechnung der DATETIME
        sorted_df['DATETIME'] = pd.to_datetime(
            sorted_df['JAHR'].astype(str) + '-01-01',  # 1. Januar des Jahres
            format='%Y-%m-%d'
        ) + pd.to_timedelta(sorted_df['ZENR'] - 1, unit='h')  # Stunden hinzufügen
        sorted_df.rename(columns={'ZENR':'PKTNR'}, inplace = True)
        sorted_df = pd.merge(sorted_df,low_cut_df, on = ['JAHR','PKTNR'])
        sorted_df['FINAL_MARKTPREIS'] = (sorted_df['MARKTPREIS'] + sorted_df['REGIONENMARKUP'] + sorted_df['STARTKOSTEN'])* sorted_df['LOW_CUT_TERM']
        sorted_df.drop(columns={'VARID_y', 'REGID_y'}, inplace=True)
        sorted_df.rename(columns={'VARID_x': 'VARID', 'REGID_x': 'REGID'}, inplace=True)
        sorted_df = sorted_df[['VARID', 'REGID', 'SIMID', 'JAHR', 'PKTNR', 'DATETIME', 'STARTKOSTEN',
                               'REGIONENMARKUP', 'LOW_CUT_TERM', 'MARKTPREIS', 'FINAL_MARKTPREIS']]
        sorted_df = sorted_df.sort_values(by=['VARID','JAHR', 'REGID', 'PKTNR'], ascending=[True,True, True, True]).reset_index(drop=True)
        return sorted_df
    else:
        print(f"Keine Dateien für die Jahre {start_year} bis {end_year} gefunden.")
        return pd.DataFrame()  # Leerer DataFrame, falls keine Dateien gefunden werden

# Funktion zum Erstellen der Plots
def plot_yearly_prices(pivot_df, output_folder):
    # Sicherstellen, dass der Ordner existiert
    yearly_plots_folder = os.path.join(output_folder, 'Yearly_Prices')
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
        plot_file = os.path.join(yearly_plots_folder, f'{region}_yearly_prices_wy_1983.png')
        plt.savefig(plot_file)
        plt.close()

        print(f"Plot gespeichert für Region: {region} -> {plot_file}")



def plot_price_duration_curve(result_df, output_folder):
    plots_folder = os.path.join(output_folder, 'PRICE_DURATION_CURVE')
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
            file_path = os.path.join(plots_folder , f'{region_name}_{jahr}PRICE_DURATION_CURVE.png')
            plt.savefig(file_path)
            plt.close()
            plt.show()
def evaluate_power_plant_files(start_year, end_year):
    path = 'C:/Users/ahmed/Desktop/ltmp_rech/1983/regresults/SQLLoader'
    all_dataframes = []

    # Über die Jahre im angegebenen Bereich iterieren
    for year in range(start_year, end_year + 1):
        for file_name in os.listdir(path):
            # Prüfen, ob die Datei dem Muster entspricht
            if f"KWResults_{year}_" in file_name and file_name.endswith('.dat'):
                file_path = os.path.join(path, file_name)
                columns = [
                    "VARID",
                    "KWID",
                    "SIMID",
                    "JAHR",
                    "ZENR",
                    "RANGLISTE",
                    "DB",
                    "KAPREVENUE",
                    "SEKRESREVENUE",
                    "MINRESREVENUE",
                    "VARKOSTEN",
                    "PVERF",
                    "PINSTALL",
                    "EINSATZ",
                    "ZWANG",
                    "MINRESERVE",
                    "SEKRESERVE",
                    "FREIELSTG",
                    "VERFB",
                    "REVISIONEN",
                    "AUSFALL",
                    "KONTSTUNDEN",
                    "STARTKOSTEN"
                ]
                # Datei lesen
                df = pd.read_csv(file_path, delimiter=',', header=None)
                df1 = df.iloc[10:].reset_index(drop=True)

                df1 = pd.DataFrame([x.split(';') for x in df1[0]])
                df1.columns = columns[:df1.shape[1]]
                all_dataframes.append(df1)
    if all_dataframes:
        combined_df = pd.concat(all_dataframes, ignore_index=True)
        # Datentypen umwandeln
        for column in combined_df.columns:
            combined_df[column] = pd.to_numeric(combined_df[column], errors='coerce')

start_year = 2023
end_year = 2050

#evaluate_power_plant_files(start_year,end_year)
# Beispielaufruf
folder_path = 'C:/Users/ahmed/Desktop/ltmp_rech/1983'


result_df = concatenate_and_process_yearly_data(folder_path, start_year, end_year)
result_df['REGION_NAME'] = result_df['REGID'].map(region_mapping)

# Ergebnis anzeigen oder speichern
if not result_df.empty:
    print("Verarbeiteter kombinierter DataFrame:")
    print(result_df.head())  # Nur die ersten Zeilen anzeigen
else:
    print("Keine Daten zusammengefügt.")
pivot_df = result_df.groupby(['REGION_NAME', 'JAHR'])['FINAL_MARKTPREIS'].mean().unstack()
pivot_df.to_excel('C:/Users/ahmed/Desktop/ltmp_rech/1983/yearly_values_wy_1983.xlsx')
# Beispielaufruf
output_folder = 'C:/Users/ahmed/Desktop/ltmp_rech/1983'
#plot_yearly_prices(pivot_df, output_folder)
#plot_price_duration_curve(result_df,output_folder)