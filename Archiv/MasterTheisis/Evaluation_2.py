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

    def evaluate_power_plant_files(self):
        kwid_regid_map = pd.read_excel(self.kwid_regid_map)
        all_dataframes = []

        data_folder = os.path.join(self.folder_path, str(self.weather_year), "regresults")
        pattern = re.compile(r"SQLLoader_KWResults_\d{4}_0_\d+\.dat")

        files_to_process = [os.path.join(data_folder, f) for f in os.listdir(data_folder) if pattern.match(f)]

        for file in files_to_process:
            df = pd.read_csv(file, delimiter=',', header=None)
            df1 = df.iloc[10:].reset_index(drop=True)
            df1 = pd.DataFrame([x.split(';') for x in df1[0]])
            df1.columns = ["KWID", "JAHR", "ZENR", "PINSTALL", "EINSATZ", "VARKOSTEN"][:df1.shape[1]]
            df1["KWID"] = pd.to_numeric(df1["KWID"], errors='coerce')
            all_dataframes.append(df1)

        if all_dataframes:
            combined_df = pd.concat(all_dataframes, ignore_index=True)
            combined_df = pd.merge(combined_df, kwid_regid_map, on=['KWID'])
            output_path = os.path.join(self.folder_path,
                                       f"{self.weather_year}/kw_profitability/kw_profitability_{self.weather_year}.xlsx")
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            combined_df.to_excel(output_path, index=False)
            print(f"Results saved to: {output_path}")


    def compute_hr_prices(self):
        low_cut_df = pd.read_excel(self.path_low_cut)

        data_folder = os.path.join(self.folder_path, str(self.weather_year), "regresults")
        pattern = re.compile(r"SQLLoader_RegResults_\d{4}_0_\d+\.dat")

        for year in range(self.start_year, self.end_year + 1):
            all_dataframes = []
            files_to_process = [os.path.join(data_folder, f) for f in os.listdir(data_folder) if pattern.match(f)]

            for file in files_to_process:
                df = pd.read_csv(file, delimiter=',', header=None)
                df1 = df.iloc[10:].reset_index(drop=True)
                df1 = pd.DataFrame([x.split(';') for x in df1[0]])
                df1.columns = ["VARID", "REGID", "SIMID", "JAHR", "ZENR", "MARKTPREIS", "REGIONENMARKUP", "STARTKOSTEN"][
                              :df1.shape[1]]
                all_dataframes.append(df1)

            if all_dataframes:
                combined_df = pd.concat(all_dataframes, ignore_index=True)
                combined_df = pd.merge(combined_df, low_cut_df, on=['JAHR', 'ZENR'])
                combined_df['FINAL_MARKTPREIS'] = (combined_df['MARKTPREIS'] + combined_df['REGIONENMARKUP'] + combined_df[
                    'STARTKOSTEN']) * combined_df['LOW_CUT_TERM']
                output_path = os.path.join(self.folder_path,
                                           f'{self.weather_year}/hourly_prices_for_year_{year}_wy_{self.weather_year}.xlsx')
                os.makedirs(os.path.dirname(output_path), exist_ok=True)
                combined_df.to_excel(output_path, index=False)
                print(f"Hourly prices saved to: {output_path}")
