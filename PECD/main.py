import pandas as pd
from PECD.GeneralTasks import GeneralTasks
from PECD.Preprocess import Preprocess
from PECD.prepare_model_input import PrepareModelInput


def main():
    input_preparation = PrepareModelInput()
    #input_preparation.create_special_input_files()
    # input_dir = "C:\\Users\\ahmed\\Desktop\\Masterarbeit\\Test_data"
    # output_dir = "C:\\Users\\ahmed\\Desktop\\Masterarbeit\\Test_data"
    # dic_offshore = pd.read_excel("C:\\Users\\ahmed\\Desktop\\Masterarbeit\\Test_data\\raw_data\\shpab_offshore.xlsx")
    # dic_onshore = pd.read_excel("C:\\Users\\ahmed\\Desktop\\Masterarbeit\\Test_data\\raw_data\\shpab_onshore.xlsx")
    # actuals_path = "C:\\Users\\ahmed\\Desktop\\Masterarbeit\\Modell\\Nichtverfuegbarkeitsvektoren.xlsx"
    # comparison_directory = "C:\\Users\\ahmed\\Desktop\\Masterarbeit\\Test_data\\comparison_data_2016"

    #preprocessor = Preprocess(input_dir, output_dir, dic_offshore, dic_onshore)
    #preprocessor.process_files()
    #preprocessor.transform('Wind_Offshore')
    #preprocessor.transform('Wind_Onshore')
    #preprocessor.transform(source='Wind_Onshore')
    #preprocessor.transform(source='Wind_Offshore')
    #general_task = GeneralTasks()
    #general_task.compare_2016(technology='pv',target_year='2025')
    #
    # tasks = GeneralTasks()
    #
    # tasks.compare_mean_all_years(technology ='wind_on')


if __name__ == "__main__":
    main()
