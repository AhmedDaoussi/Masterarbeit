import re
import pandas as pd
import os
# Directory containing the Excel files
actuals_path = "C:\\Users\\ahmed\\Desktop\\Masterarbeit\\Modell\\Nichtverfuegbarkeitsvektoren.xlsx"
comparison_directory = "C:\\Users\\ahmed\\Desktop\\Masterarbeit\\Test_data\\comparison_data_2016"


df_dict = pd.read_excel(actuals_path, sheet_name=None)
df_pv = df_dict['PV_Vektor']
df_on = df_dict['Onshore_Vektor']
df_off = df_dict['Offshore_Vektor']

df_pv = df_pv.drop([0, 8761,8762])
df_on = df_on.drop([0, 8761])
df_off = df_off.drop([0, 8761])



def process_column_name(name):
    # If the column name starts with 'ES' after any initial numbers/underscores
    if re.match(r'^[\d_]*ES', name):
        return name

    # Special handling for 'IT' followed by a syllable, possibly separated by an underscore
    it_match = re.search(r'[\d_]*IT_?([A-Za-z]+)', name)
    if it_match:
        return 'IT' + it_match.group(1)  # Concatenating 'IT' with the syllable without underscore

    s_match = re.search(r'\b(S|SE|SO)(\d{1,2})\b', name)
    if s_match:
        return s_match.group(1)

    # Default case: Remove all characters until the first letter, keep letters until the next underscore
    match = re.search(r'[\d_]*([A-Za-z]+)', name)
    if match:
        return match.group(1)  # Return the first group of letters found
    return name  # Return original if no matches


def find_excel_files(df_actuals, technology):
    # Extract column names from DataFrame
    global search_terms
    column_names = df_actuals.columns.tolist()
    # List to store found file paths
    comp_summary = pd.DataFrame({'Power_Price_Code':['mean actuals','mean eraa','mean diffrence', 'variance in actuals', 'variance in eraa']})
    comp_summary.set_index('Power_Price_Code', inplace=True)

    # Search in the given directory
    if technology == 'wind_on':
        search_terms = ['PECD_Wind_Offshore_2025', 'number']
        directory = "C:\\Users\\ahmed\\Desktop\\Masterarbeit\\Test_data\\transformed_data"
    elif technology == 'wind_off':
        search_terms = ['PECD_Wind_Onshore_2025', 'number']
        directory = "C:\\Users\\ahmed\\Desktop\\Masterarbeit\\Test_data\\transformed_data"
    elif technology == 'pv':
        search_terms = ['PECD_LFSolarPV_2025_', 'number']
        directory = "C:\\Users\\ahmed\\Desktop\\Masterarbeit\\Test_data\\processed_data"
    for file in os.listdir(directory):
        for code in column_names:
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
                new_column = [sum_eraa,sum_actuals
                    ,(sum_eraa - sum_actuals),var_eraa,var_actuals]
                comp_summary[code] = new_column
                # Export results to Excel
                results_df = pd.DataFrame.from_dict(results, orient='index', columns=[code])
                #results_df.to_excel(os.path.join(comparison_directory, f'{code}Wind_On_2016_comparison.xlsx'))
    print(comp_summary)
    comp_summary.to_excel(os.path.join(comparison_directory, f'Summary_{technology}_Nichtverfügbarkeit.xlsx'))
def filter_shpb(df):
    for col in df.columns:
        # Check if 'ShpB' is not in the column name
        if 'ShpB' not in col:
            # Drop the column from the DataFrame
            df.drop(col, axis=1, inplace=True)
    return df


df_on = filter_shpb(df_on)

# Process each column name
new_columns_pv = [process_column_name(col) for col in df_pv.columns]
df_pv.columns = new_columns_pv
new_columns_on = [process_column_name(col) for col in df_on.columns]
df_on.columns = new_columns_on
new_columns_off = [process_column_name(col) for col in df_off.columns]
df_off.columns = new_columns_off
df_pv.to_excel(os.path.join("C:\\Users\\ahmed\\Desktop\\Masterarbeit\\Test_data\\pv_on_off_dfs",'pv_df.xlsx'))
df_on.to_excel(os.path.join("C:\\Users\\ahmed\\Desktop\\Masterarbeit\\Test_data\\pv_on_off_dfs",'pv_on.xlsx'))
df_off.to_excel(os.path.join("C:\\Users\\ahmed\\Desktop\\Masterarbeit\\Test_data\\pv_on_off_dfs",'pv_off.xlsx'))

find_excel_files(df_on, technology='wind_on')


