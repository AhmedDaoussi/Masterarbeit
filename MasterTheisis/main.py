from Evaluation import Evaluation

from Simulation import Simulation
def main():






    #kw_dict = {4832: 'pv_2033_DE00', 4823: 'pv_2033_FR00', 4855: 'pv_2033_NL00', 4878: 'pv_2033_PL00', 3678: 'pv_2033_ITCN', 4865: 'pv_2033_ITN1', 4805: 'csp_2033_ES00', 4803: 'pv_2033_ES00', 4797: 'pv_2033_BG00', 3295: 'pv_2033_ITCS', 3675: 'pv_2033_ITS1', 4863: 'pv_2033_ITSI', 2923: 'pv_2033_ITSA', 663: 'pv_2033_ITCA', 4748: 'wind_on_2033_DE00_shape_a', 4739: 'wind_on_2033_FR00_shape_a', 4770: 'wind_on_2033_NL00_shape_a', 4796: 'wind_on_2033_PL00_shape_a', 4715: 'wind_on_2033_ITCN_shape_a', 4781: 'wind_on_2033_ITN1_shape_a', 4721: 'wind_on_2033_ES00_shape_a', 4713: 'wind_on_2033_BG00_shape_a', 4719: 'wind_on_2033_ITCS_shape_a', 4723: 'wind_on_2033_ITSI_shape_a', 4726: 'wind_on_2033_ITS1_shape_a', 4728: 'wind_on_2033_ITSA_shape_a', 679: 'wind_on_2033_ITCA_shape_a', 4718: 'wind_on_2033_ITCN_shape_b', 4714: 'wind_on_2033_ITN1_shape_b', 4720: 'wind_on_2033_ITCS_shape_b', 4724: 'wind_on_2033_ITS1_shape_b', 4727: 'wind_on_2033_ITSI_shape_b', 4729: 'wind_on_2033_ITSA_shape_b', 1289: 'wind_on_2033_ITCA_shape_b', 4732: 'wind_on_2033_DE00_shape_b', 4737: 'wind_on_2033_FR00_shape_b', 4750: 'wind_on_2033_NL00_shape_b', 4751: 'wind_on_2033_PL00_shape_b', 4765: 'wind_on_2033_ES00_shape_b', 4772: 'wind_on_2033_BG00_shape_b', 4746: 'wind_off_2033_DE00_shape_a', 4738: 'wind_off_2033_FR00_shape_a', 4771: 'wind_off_2033_NL00_shape_a', 4794: 'wind_off_2033_PL00_shape_a', 4784: 'wind_off_2033_DE00_shape_b', 955: 'wind_off_2033_ES00_shape_a', 1646: 'wind_off_2033_ITSA_shape_a', 1642: 'wind_off_2033_ITSI_shape_a'}

    #for start_year in [2025,2030]:
        #simulation = Simulation(folder_path='E:/results/',
               #weather_years= range(1987,2019),start_year=start_year,life_time=20,inflation_rate=0.08)
        #for kwid in kw_dict.keys():
            #all_df = simulation.read_contribution_margins()
            #df = simulation.monte_carlo_simulation(all_df,kwid)
            #simulation.plot_cumulative_distribution(df,kwid)
    for weather_year in [2014]:
    #     #process_raw_data = ProcessRawData()
    #     #process_raw_data.format_and_transform_raw_data()
    #
    #     #create_shape_a = CreateShapeAFiles()
    #     #create_shape_a.transform(source='Wind_Offshore')
    #     #create_shape_a.transform(source='Wind_Onshore')
    #     #create_shape_a.rename_shape_a_files()
    #
    #     #rename = RenameFilesNames()
    #     #rename.rename_file_names()
    #     #prepare = PrepareDataBaseFiles(input_path=r'C:\Users\ahmed\Desktop\Masterarbeit2\Test_data\processed_data2'
    #     #                      , output_path=r'C:\Users\ahmed\Desktop\Masterarbeit\Weather_Year_Files_test',
    #     #                      weather_years=list(range(1993, 1994)))
    #     #prepare.prepare_data_base_files_1()
         evaluate = Evaluation(
             folder_path='E:/Masterarbeit_zip',
             weather_year=weather_year,

             start_year=2023,
             end_year=2050
         )
         evaluate.evaluate_power_plant_files()
         #evaluate.compute_hr_prices()
         #result_df = evaluate.concatenate_and_process_yearly_data()
    #
    #     #pivot_df = result_df.pivot_table(index='REGID', columns='JAHR', values='FINAL_MARKTPREIS', aggfunc='mean')
    #     #evaluate.plot_yearly_prices(result_df)
    #     #evaluate.plot_price_duration_curve(result_df)





if __name__ == "__main__":
    main()

