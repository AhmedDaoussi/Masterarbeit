import zipfile
import pandas as pd
import os
import re  # Reguläre Ausdrücke für das Muster-Matching

class KWResultsProcessor:
    def __init__(self, folder_path, weather_year, kw_dict_selc):
        self.folder_path = folder_path  # Basisverzeichnis für ZIP-Dateien
        self.weather_year = weather_year  # Wetterjahr
        self.kw_dict_selc = kw_dict_selc  # Dictionary mit gültigen KWIDs

    def extract_kwresults_from_zip(self):
        """Liest alle KWResults_*.dat-Dateien aus einer ZIP-Datei ein, verarbeitet sie und gibt ein kombiniertes DataFrame zurück."""
        all_dataframes = []

        # ZIP-Dateien für beide möglichen Formate durchsuchen
        zip_files = [f"{self.folder_path}/{self.weather_year}/daoussi_Wetterjahr_{x}_{self.weather_year}.zip" for x in ["a", "b"]]

        # Regulärer Ausdruck für das Dateiformat: SQLLoader_KWResults_YYYY_0_XXX.dat
        pattern = re.compile(r"daoussi_Wetterjahr_[a|b]_\d{4}/SQLLoader/SQLLoader_KWResults_\d{4}_0_\d+\.dat")

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
                        df1 = df1[df1["KWID"].astype(int).isin(self.kw_dict_selc.keys())]

                        all_dataframes.append(df1)

        # Falls Dateien gefunden wurden, alle DataFrames kombinieren
        if all_dataframes:
            combined_df = pd.concat(all_dataframes, ignore_index=True)

            # Alle Spalten in numerische Werte konvertieren (Fehlwerte bleiben erhalten)
            for column in combined_df.columns:
                combined_df[column] = pd.to_numeric(combined_df[column], errors='coerce')

            return combined_df
        else:
            print("Keine passenden Daten gefunden.")
            return None


# **Beispielhafte Nutzung**
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

processor = KWResultsProcessor(folder_path, weather_year, kw_dict_selc)
df = processor.extract_kwresults_from_zip()

if df is not None:
    import ace_tools as tools

    tools.display_dataframe_to_user(name="KWResults Data", dataframe=df)
else:
    print("Keine gültigen Daten extrahiert.")
