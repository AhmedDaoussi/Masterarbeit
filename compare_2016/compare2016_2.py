import pandas as pd
import os

# Directory containing the Excel files
eraa_data_directory = "C:\\Users\\ahmed\\Desktop\\Masterarbeit\\Test_data\\pv_on_off_dfs"
actuals_path = "C:\\Users\\ahmed\\Desktop\\Masterarbeit\\Modell\\Nichtverfuegbarkeitsvektoren.xlsx"
comparison_directory = "C:\\Users\\ahmed\\Desktop\\Masterarbeit\\Test_data\\comparison_data_2016"

# Load the Excel files into DataFrames
df_pv = pd.read_excel(os.path.join(eraa_data_directory, 'df_pv.xlsx'))
df_on = pd.read_excel(os.path.join(eraa_data_directory, 'df_on.xlsx'))
df_off = pd.read_excel(os.path.join(eraa_data_directory, 'df_off.xlsx'))

# Save DataFrames as Pickle files (more efficient than reading Excel files)
df_pv.to_pickle(os.path.join(eraa_data_directory, 'df_pv.pkl'))
df_on.to_pickle(os.path.join(eraa_data_directory, 'df_on.pkl'))
df_off.to_pickle(os.path.join(eraa_data_directory, 'df_off.pkl'))

# Load DataFrames from Pickle files
df_pv = pd.read_pickle(os.path.join(eraa_data_directory, 'df_pv.pkl'))
df_on = pd.read_pickle(os.path.join(eraa_data_directory, 'df_on.pkl'))
df_off = pd.read_pickle(os.path.join(eraa_data_directory, 'df_off.pkl'))

def find_excel_files(df_actuals, technology):
    # Extract column names from DataFrame
    global search_terms
    column_names = df_actuals.columns.tolist()
    # List to store found file paths
    comp_summary = pd.DataFrame({'Power_Price_Code':['vlh_sum_eraa','vlh_sum_actuals','vlh_sum_difference', 'variance in eraa','variance in actuals']})
    comp_summary.set_index('Power_Price_Code', inplace=True)
    nicht_verfueg_summary = comp_summary.copy()
    verfueg_summary = comp_summary.copy()


    # Search in the given directory
    if technology == 'wind_off':
        search_terms = ['PECD_Wind_Offshore_2025', 'number']
        directory = "C:\\Users\\ahmed\\Desktop\\Masterarbeit\\Test_data\\transformed_data"
    elif technology == 'wind_on':
        search_terms = ['PECD_Wind_Onshore_2025', 'number']
        directory = "C:\\Users\\ahmed\\Desktop\\Masterarbeit\\Test_data\\transformed_data"
    elif technology == 'pv':
        search_terms = ['PECD_LFSolarPV_2025_', 'number']
        directory = "C:\\Users\\ahmed\\Desktop\\Masterarbeit\\Test_data\\processed_data"
    for code in column_names:
        for file in os.listdir(directory):

            search_terms1 = search_terms + [f'{code}']
            if all(term in file for term in search_terms1):
                df_eraa = pd.read_excel(f'{directory}\\{file}')
                sum_actuals = df_actuals[code].sum()
                mean_actuals = df_actuals[code].mean()
                var_actuals = df_actuals[code].var()

                sum_eraa = df_eraa.iloc[:,36].sum()
                mean_eraa = df_eraa.iloc[:,36].mean()
                var_eraa = df_eraa.iloc[:,36].var()
                # Store comparison results
                results = {
                    'Sum Difference': sum_eraa - sum_actuals,
                    'Mean Difference': mean_eraa - mean_actuals,
                    'Variance Difference': var_eraa - var_actuals
                }
                nicht_ver_column = [sum_eraa,sum_actuals
                    ,(sum_eraa - sum_actuals),var_eraa,var_actuals]
                ver_column = [8760 - sum_eraa, 8760 - sum_actuals, sum_actuals - sum_eraa,None,None]
                nicht_verfueg_summary[code] = nicht_ver_column
                verfueg_summary[code] = ver_column


    nicht_verfueg_summary.to_excel(os.path.join(comparison_directory, f'Summary_{technology}_Nichtverfügbarkeit.xlsx'))
    verfueg_summary.to_excel(os.path.join(comparison_directory, f'Summary_{technology}_Verfügbarkeit.xlsx'))


find_excel_files(df_on, technology='wind_on')
find_excel_files(df_off, technology='wind_off')
find_excel_files(df_pv, technology='pv')
