import zipfile
import pandas as pd
import os
import re  # Reguläre Ausdrücke für das Muster-Matching
class KWResultsProcessor:
    def __init__(self, folder_path, weather_year, kw_dict_selc,start_year,end_year):
        self.folder_path = folder_path  # Basisverzeichnis für ZIP-Dateien
        self.weather_year = weather_year  # Wetterjahr
        self.kw_dict_selc = kw_dict_selc
        self.start_year = start_year
        self.end_year = end_year

    def compute_hr_prices(self):
        for year in range(self.start_year, self.end_year + 1):
            all_dataframes = []

            # ZIP-Dateien für beide möglichen Formate durchsuchen
            zip_files = [f"{self.folder_path}/{self.weather_year}/daoussi_Wetterjahr_{x}_{self.weather_year}.zip" for x
                         in ["a", "b"]]

            # Regulärer Ausdruck für das Dateiformat: SQLLoader_KWResults_YYYY_0_XXX.dat
            pattern = re.compile(r"daoussi_Wetterjahr_[a|b]_\d{4}/SQLLoader/SQLLoader_RegResults_\d{4}_0_\d+\.dat")

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
folder_path = 'C:/Users/ahmed/Desktop/ltmp_rech' # Basisverzeichnis
weather_year = 1989  # Beispieljahr
kw_dict_selc = {4832: 'pv_2033_DE00', 4823: 'pv_2033_FR00', 4855: 'pv_2033_NL00', 4878: 'pv_2033_PL00',
                3678: 'pv_2033_ITCN', 4865: 'pv_2033_ITN1', 4805: 'csp_2033_ES00', 4803: 'pv_2033_ES00',
                4797: 'pv_2033_BG00', 3295: 'pv_2033_ITCS', 3675: 'pv_2033_ITS1', 4863: 'pv_2033_ITSI',
                2923: 'pv_2033_ITSA', 663: 'pv_2033_ITCA', 4748: 'wind_on_2033_DE00_shape_a',
                4739: 'wind_on_2033_FR00_shape_a', 4770: 'wind_on_2033_NL00_shape_a', 4796: 'wind_on_2033_PL00_shape_a',
                4715: 'wind_on_2033_ITCN_shape_a', 4781: 'wind_on_2033_ITN1_shape_a', 4721: 'wind_on_2033_ES00_shape_a',
                4713: 'wind_on_2033_BG00_shape_a', 4719: 'wind_on_2033_ITCS_shape_a', 4723: 'wind_on_2033_ITSI_shape_a',
                4726: 'wind_on_2033_ITS1_shape_a', 4728: 'wind_on_2033_ITSA_shape_a', 679: 'wind_on_2033_ITCA_shape_a',
                4718: 'wind_on_2033_ITCN_shape_b', 4714: 'wind_on_2033_ITN1_shape_b', 4720: 'wind_on_2033_ITCS_shape_b',
                4724: 'wind_on_2033_ITS1_shape_b', 4727: 'wind_on_2033_ITSI_shape_b', 4729: 'wind_on_2033_ITSA_shape_b',
                1289: 'wind_on_2033_ITCA_shape_b', 4732: 'wind_on_2033_DE00_shape_b', 4737: 'wind_on_2033_FR00_shape_b',
                4750: 'wind_on_2033_NL00_shape_b', 4751: 'wind_on_2033_PL00_shape_b', 4765: 'wind_on_2033_ES00_shape_b',
                4772: 'wind_on_2033_BG00_shape_b', 4746: 'wind_off_2033_DE00_shape_a',
                4738: 'wind_off_2033_FR00_shape_a', 4771: 'wind_off_2033_NL00_shape_a',
                4794: 'wind_off_2033_PL00_shape_a', 4784: 'wind_off_2033_DE00_shape_b',
                955: 'wind_off_2033_ES00_shape_a', 1646: 'wind_off_2033_ITSA_shape_a',
                1642: 'wind_off_2033_ITSI_shape_a'}
start_year = 2023
end_year = 2050
processor = KWResultsProcessor(folder_path, weather_year, kw_dict_selc, start_year, end_year)
df = processor.compute_hr_prices()
print('a')