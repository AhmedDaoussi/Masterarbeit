import re
import os
import pandas as pd

class GeneralTasks:
    def __init__(self):
        self.comparison_directory = "C:\\Users\\ahmed\\Desktop\\Masterarbeit\\Test_data\\comparison_data_2016"
        self.directory = "C:\\Users\\ahmed\\Desktop\\Masterarbeit\\Test_data\\pv_on_off_dfs"
        self.df_pv = pd.read_excel("C:\\Users\\ahmed\\Desktop\\Masterarbeit\\Test_data\\pv_on_off_dfs\\pv_df.xlsx")
        self.df_on = pd.read_pickle(os.path.join(self.directory, 'df_on.pkl'))
        self.df_off = pd.read_pickle(os.path.join(self.directory, 'df_off.pkl'))
        self.weather_years = range(1982,2020)


    @staticmethod
    def process_column_name(name):
        # If the column name starts with 'ES' after any initial numbers/underscores
        if re.match(r'^[\d_]*ES', name):
            return name

        # Special handling for 'IT' followed by a syllable, possibly separated by an underscore
        it_match = re.search(r'[\d_]*IT_?([A-Za-z]+)', name)
        if it_match:
            return 'IT' + it_match.group(1)  # Concatenating 'IT' with the syllable without underscore

        s_match = re.search(r'\b(SE0)(\d{1,2,3,4})\b', name)
        if s_match:
            return s_match.group(1)

        # Default case: Remove all characters until the first letter, keep letters until the next underscore
        match = re.search(r'[\d_]*([A-Za-z]+)', name)
        if match:
            return match.group(1)  # Return the first group of letters found
        return name  # Return original if no matches

    def calculate_mean_years(self, df):
        # Calculate the mean for each row from the third column onwards
        df['mean_years_eraa'] = df.iloc[:, 2:].mean(axis=1)
        return df['mean_years_eraa']
    def filter_shpb(self, df):
        # Drop columns that do not contain 'ShpB' in their names
        df = df.loc[:, df.columns.str.contains('ShpB')]
        return df
#
    def compare_2016(self, technology, target_year):
        # Extract column names from DataFrame

        comp_summary = pd.DataFrame({'Power_Price_Code': ['sum actuals', 'sum eraa', 'sum difference', 'mean actuals','mean eraa','variance in actuals', 'variance in eraa']})
        comp_summary.set_index('Power_Price_Code', inplace=True)

        # Determine the directory and search terms based on technology
        if technology == 'wind_off':
            search_terms = [f'PECD_Wind_Offshore_{target_year}', 'number']
            directory = "C:\\Users\\ahmed\\Desktop\\Masterarbeit\\Test_data\\transformed_data"
            df_actuals = self.df_off
            df_actuals = [self.process_column_name(col) for col in df_actuals.columns]
            column_names = df_actuals.columns.tolist()
        elif technology == 'wind_on':
            search_terms = [f'PECD_Wind_Onshore_{target_year}', 'number']
            directory = "C:\\Users\\ahmed\\Desktop\\Masterarbeit\\Test_data\\transformed_data"
            df_actuals = self.df_on
            df_actuals = [self.process_column_name(col) for col in df_actuals.columns]
            column_names = df_actuals.columns.tolist()
        elif technology == 'pv':
            search_terms = [f'PECD_LFSolarPV_{target_year}_', 'number']
            directory = "C:\\Users\\ahmed\\Desktop\\Masterarbeit\\Test_data\\processed_data"
            df_actuals = self.df_pv
            df_actuals = [self.process_column_name(col) for col in df_actuals.columns]
            column_names = df_actuals.columns.tolist()
        else:
            raise ValueError("Technology must be 'wind_on', 'wind_off', or 'pv'.")

        # Search for files and process them
        for file in os.listdir(directory):
            for code in column_names:
                search_terms1 = search_terms + [f'{code}']
                if all(term in file for term in search_terms1):
                    df_eraa = pd.read_excel(os.path.join(directory, file))
                    sum_actuals = df_actuals[code].sum()
                    mean_actuals = df_actuals[code].mean()
                    var_actuals = df_actuals[code].var()
                    eraa_mean_all_years = self.calculate_mean_years(df_eraa)

                    sum_eraa = eraa_mean_all_years.sum()
                    mean_eraa = eraa_mean_all_years.mean()
                    var_eraa = eraa_mean_all_years.var()

                    comparison_df = df_actuals[code]
                    comparison_df['eraa_mean'] = eraa_mean_all_years
                    comparison_path = os.path.join(self.comparison_directory,
                                                f'{code}_{technology}_Nichtverfügbarkeit_Vergleich.xlsx')
                    #comparison_df.to_excel(comparison_path)

                    # Store comparison results
                    new_column = [sum_actuals,sum_eraa,(sum_eraa-sum_actuals), mean_actuals, mean_eraa, var_actuals,
                                  var_eraa]
                    comp_summary[code] = new_column

        # Export summary to Excel
        summary_path = os.path.join(self.comparison_directory, f'Summary_{technology}_Nichtverfügbarkeit.xlsx')
        comp_summary.to_excel(summary_path)
        print(f"Comparison summary saved to {summary_path}")
    # compare atuals of 2016 with mean of all weather years of a specific target year
    def compare_mean_all_years(self, technology):
        # Extract column names from DataFrame

        comp_summary = pd.DataFrame({'Power_Price_Code': ['sum actuals', 'sum eraa', 'sum difference', 'mean actuals',
                                                          'mean eraa', 'variance in actuals', 'variance in eraa']})
        comp_summary.set_index('Power_Price_Code', inplace=True)

        # Determine the directory and search terms based on technology
        if technology == 'wind_off':
            search_terms = [f'PECD_Wind_Offshore_2025', 'number']
            directory = "C:\\Users\\ahmed\\Desktop\\Masterarbeit\\Test_data\\transformed_data"
            df_actuals = self.df_off
            column_names = df_actuals.columns.tolist()
        elif technology == 'wind_on':
            search_terms = [f'PECD_Wind_Onshore_2025', 'number']
            directory = "C:\\Users\\ahmed\\Desktop\\Masterarbeit\\Test_data\\transformed_data"
            df_actuals = self.df_on
            column_names = df_actuals.columns.tolist()
        elif technology == 'pv':
            search_terms = [f'PECD_LFSolarPV_2025_', 'number']
            directory = "C:\\Users\\ahmed\\Desktop\\Masterarbeit\\Test_data\\processed_data"
            df_actuals = self.df_pv
            column_names = df_actuals.columns.tolist()
        else:
            raise ValueError("Technology must be 'wind_on', 'wind_off', or 'pv'.")

        # Search for files and process them
        for file in os.listdir(directory):
            for code in column_names:
                search_terms1 = search_terms + [f'{code}']
                if all(term in file for term in search_terms1):
                    df_eraa = pd.read_excel(os.path.join(directory, file))
                    sum_actuals = df_actuals[code].sum()
                    mean_actuals = df_actuals[code].mean()
                    var_actuals = df_actuals[code].var()

                    eraa_mean_all_years = self.calculate_mean_years(df_eraa)
                    sum_eraa = eraa_mean_all_years.sum()
                    mean_eraa = eraa_mean_all_years.mean()
                    var_eraa = eraa_mean_all_years.var()

                    comparison_df = df_actuals[code].copy()  # Ensure it's a copy
                    comparison_df['eraa_mean'] = eraa_mean_all_years.values  # Assigning the values to the new column
                    comparison_path = os.path.join(self.comparison_directory,
                                                   f'{code}_{technology}_Nichtverfügbarkeit_Vergleich.xlsx')
                    #comparison_df.to_excel(comparison_path)

                    new_column = [sum_actuals, sum_eraa, (sum_eraa - sum_actuals), mean_actuals, mean_eraa, var_actuals,
                                  var_eraa]
                    comp_summary[code] = new_column

        # Export summary to Excel
        summary_path = os.path.join(self.comparison_directory, f'Summary_{technology}_Nichtverfügbarkeit.xlsx')
        comp_summary.to_excel(summary_path)
        print(f"Comparison summary saved to {summary_path}")

    def process_and_save(self):
        # Process and save the filtered and renamed DataFrames
        self.df_on = self.filter_shpb(self.df_on)

        self.df_pv.columns = [self.process_column_name(col) for col in self.df_pv.columns]
        self.df_on.columns = [self.process_column_name(col) for col in self.df_on.columns]
        self.df_off.columns = [self.process_column_name(col) for col in self.df_off.columns]

        output_dir = "C:\\Users\\ahmed\\Desktop\\Masterarbeit\\Test_data\\pv_on_off_dfs"
        os.makedirs(output_dir, exist_ok=True)

        self.df_pv.to_excel(os.path.join(output_dir, 'pv_df.xlsx'))
        self.df_on.to_excel(os.path.join(output_dir, 'pv_on.xlsx'))
        self.df_off.to_excel(os.path.join(output_dir, 'pv_off.xlsx'))
        print(f"Processed DataFrames saved to {output_dir}")
