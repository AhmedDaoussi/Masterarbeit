import os
import pandas as pd
import matplotlib.pyplot as plt
import zipfile
import tarfile
import zipfile
import pandas as pd
import os
import numpy as np
import re  # Reguläre Ausdrücke für das Muster-Matching
kw_dict = {4832: 'pv_2033_DE00', 4823: 'pv_2033_FR00', 4855: 'pv_2033_NL00', 4878: 'pv_2033_PL00', 3678: 'pv_2033_ITCN', 4865: 'pv_2033_ITN1', 4805: 'csp_2033_ES00', 4803: 'pv_2033_ES00', 4797: 'pv_2033_BG00', 3295: 'pv_2033_ITCS', 3675: 'pv_2033_ITS1', 4863: 'pv_2033_ITSI', 2923: 'pv_2033_ITSA', 663: 'pv_2033_ITCA', 4748: 'wind_on_2033_DE00_shape_a', 4739: 'wind_on_2033_FR00_shape_a', 4770: 'wind_on_2033_NL00_shape_a', 4796: 'wind_on_2033_PL00_shape_a', 4715: 'wind_on_2033_ITCN_shape_a', 4781: 'wind_on_2033_ITN1_shape_a', 4721: 'wind_on_2033_ES00_shape_a', 4713: 'wind_on_2033_BG00_shape_a', 4719: 'wind_on_2033_ITCS_shape_a', 4723: 'wind_on_2033_ITSI_shape_a', 4726: 'wind_on_2033_ITS1_shape_a', 4728: 'wind_on_2033_ITSA_shape_a', 679: 'wind_on_2033_ITCA_shape_a', 4718: 'wind_on_2033_ITCN_shape_b', 4714: 'wind_on_2033_ITN1_shape_b', 4720: 'wind_on_2033_ITCS_shape_b', 4724: 'wind_on_2033_ITS1_shape_b', 4727: 'wind_on_2033_ITSI_shape_b', 4729: 'wind_on_2033_ITSA_shape_b', 1289: 'wind_on_2033_ITCA_shape_b', 4732: 'wind_on_2033_DE00_shape_b', 4737: 'wind_on_2033_FR00_shape_b', 4750: 'wind_on_2033_NL00_shape_b', 4751: 'wind_on_2033_PL00_shape_b', 4765: 'wind_on_2033_ES00_shape_b', 4772: 'wind_on_2033_BG00_shape_b', 4746: 'wind_off_2033_DE00_shape_a', 4738: 'wind_off_2033_FR00_shape_a', 4771: 'wind_off_2033_NL00_shape_a', 4794: 'wind_off_2033_PL00_shape_a', 4784: 'wind_off_2033_DE00_shape_b', 955: 'wind_off_2033_ES00_shape_a', 1646: 'wind_off_2033_ITSA_shape_a', 1642: 'wind_off_2033_ITSI_shape_a'}
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


class Simulation:

    # Constructor (initializer method)
    def __init__(self, folder_path, weather_years, start_year, life_time, inflation_rate):
        # Instance attribute
        self.folder_path = folder_path
        self.weather_years = weather_years
        self.start_year = start_year
        self.life_time = life_time
        self.inflation_rate = inflation_rate
        self.kwid_regid_map = "D:/Masterarbeit/KWID_REGID_MAPPING.xlsx"
        self.num_simulations = 10000

    def read_contribution_margins(self):
        all_dfs = []

        # Loop through each weather year and process the corresponding Excel file
        for year in self.weather_years:

            file_path = os.path.join(self.folder_path, f"{year}/kw_profitability/kw_profitability_{year}.xlsx")


            # Check if the file exists before reading
            if os.path.exists(file_path):
                df = pd.read_excel(file_path)  # Read Excel file into DataFrame
                df["weather_year"] = year  # Add weather_year column
                all_dfs.append(df)  # Append DataFrame to the list
            else:
                print(f"File not found: {file_path}")

        # Concatenate all DataFrames into one
        if all_dfs:
            all_data = pd.concat(all_dfs, ignore_index=True)
            print("All data combined successfully!")
        else:
            print("No files found in the given range.")
            return None

        # Apply discounting for 'Annual_Profit/installed_kw' for all years after 2025
        all_data["Discounted_Profit/installed_kw"] = all_data.apply(
            lambda row: row["Annual_Profit/installed_kw"] / ((1 + self.inflation_rate) ** (row["JAHR"] - self.start_year))
            if row["JAHR"] > self.start_year else row["Annual_Profit/installed_kw"], axis=1
        )
        all_data["Tech_Region"] = all_data["Technology"] + "_" + all_data["Region"]

        # 3. Bedingung für wind_on / wind_off
        mask = all_data["Technology"].isin(["wind_on", "wind_off"])

        # Shape anpassen
        all_data.loc[mask & all_data["JAHR"].between(2023, 2032), "Shape"] = "a"
        all_data.loc[mask & all_data["JAHR"].between(2033, 2050), "Shape"] = "b"

        all_data.to_excel('E:/results/all_data.xlsx', index=False)
        return all_data


    def monte_carlo_simulation(self, df, kwid_target):
        # Filter dataframe for the specific KWID
        df_filtered = df[df['KWID'] == kwid_target].copy()

        if df_filtered.empty:
            raise ValueError(f"No data found for KWID={kwid_target}")

        # Define start year
        start_year = self.start_year

        # Create a DataFrame to store simulation results
        simulation_results = []

        # Run Monte Carlo simulation 1000 times
        for sim in range(self.num_simulations):
            cash_flows = []

            # Generate a random sequence of weather years for the simulation
            sampled_weather_years = np.random.choice(df_filtered['weather_year'], size=self.life_time + 1, replace=True)

            # Extract corresponding 'Annual_Profit/installed_kw' values
            for year in sampled_weather_years:
                sampled_value = df_filtered[df_filtered['weather_year'] == year]['Annual_Profit/installed_kw'].sample(n=1).values[0]
                cash_flows.append(sampled_value)

            # Store the results for this simulation
            simulation_results.append(cash_flows)

        # Convert results to DataFrame
        years = [str(start_year + i) for i in range(self.life_time + 1)]
        simulation_df = pd.DataFrame(simulation_results, columns=years)

        return simulation_df

    def monte_carlo_simulation_ab(self, df, kwid_target):
        # Filter dataframe for the specific KWID
        df_filtered = df[df['KWID'] == kwid_target].copy()

        if df_filtered.empty:
            raise ValueError(f"No data found for KWID={kwid_target}")

        # Define start year
        start_year = self.start_year

        # Create a DataFrame to store simulation results
        simulation_results = []

        # Run Monte Carlo simulation 1000 times
        for sim in range(self.num_simulations):
            cash_flows = []

            # Generate a random sequence of weather years for the simulation
            sampled_weather_years = np.random.choice(df_filtered['weather_year'], size=self.life_time + 1, replace=True)

            # Extract corresponding 'Annual_Profit/installed_kw' values
            for year in sampled_weather_years:
                sampled_value = df_filtered[df_filtered['weather_year'] == year]['Annual_Profit/installed_kw'].sample(n=1).values[0]
                cash_flows.append(sampled_value)

            # Store the results for this simulation
            simulation_results.append(cash_flows)

        # Convert results to DataFrame
        years = [str(start_year + i) for i in range(self.life_time + 1)]
        simulation_df = pd.DataFrame(simulation_results, columns=years)

        return simulation_df

    def monte_carlo_simulation_a(self, df, kwid_target):
        # Filter dataframe for the specific KWID
        df_filtered = df[df['KWID'] == kwid_target].copy()

        if df_filtered.empty:
            raise ValueError(f"No data found for KWID={kwid_target}")

        # Define start year
        start_year = self.start_year

        # Create a DataFrame to store simulation results
        simulation_results = []

        # Run Monte Carlo simulation 1000 times
        for sim in range(self.num_simulations):
            cash_flows = []

            # Generate a random sequence of weather years for the simulation
            sampled_weather_years = np.random.choice(df_filtered['weather_year'], size=self.life_time + 1, replace=True)

            # Extract corresponding 'Annual_Profit/installed_kw' values
            for year in sampled_weather_years:
                sampled_value = df_filtered[df_filtered['weather_year'] == year]['Annual_Profit/installed_kw'].sample(n=1).values[0]
                cash_flows.append(sampled_value)

            # Store the results for this simulation
            simulation_results.append(cash_flows)

        # Convert results to DataFrame
        years = [str(start_year + i) for i in range(self.life_time + 1)]
        simulation_df = pd.DataFrame(simulation_results, columns=years)

        return simulation_df

    def plot_distribution(self, simulation_df, kwid_target, save_folder="E:/monte_carlo_simulation/"):
        """Plots and saves the histogram of total cash flows over all Monte Carlo simulations."""
        total_cash_flows = simulation_df.sum(axis=1)

        plt.figure(figsize=(10, 5))
        bin_width = 10

        # Find the nearest multiple of 100 for the minimum bin edge
        min_edge = (total_cash_flows.min() // 100) * 100

        # Ensure max bin extends to include the highest value
        max_edge = total_cash_flows.max() + bin_width

        # Create bin edges starting from the nearest multiple of 100
        bin_edges = np.arange(min_edge, max_edge + bin_width, bin_width)

        # Plot histogram with adjusted bin edges
        plt.hist(total_cash_flows, bins=bin_edges, alpha=0.7, edgecolor='black')
        plt.xlabel('Total Cash Flow over Lifetime in Euro/kw')
        plt.ylabel('Frequency')
        plt.title(
            f'Distribution of the Total Discounted Cash Flows (NPV) for {kw_dict.get(kwid_target)} start_year {self.start_year} ')
        plt.grid(True)

        # Ensure the save folder exists
        os.makedirs(save_folder, exist_ok=True)

        # Generate a unique filename using timestamp
        filename = f"NPV_Distribution_KWID_{kwid_target}_{kw_dict.get(kwid_target)} for start_year {self.start_year}.png"
        filepath = os.path.join(save_folder, filename)

        # Save the figure
        plt.savefig(filepath, dpi=300, bbox_inches='tight')
        plt.close()  # Close the plot to free memory

        print(f"Plot saved successfully at: {filepath}")

    import os
    import numpy as np
    import matplotlib.pyplot as plt

    def plot_boxplot(self, simulation_df, kwid_target, save_folder="E:/monte_carlo_simulation/"):
        """Plots and saves the boxplot of total cash flows over all Monte Carlo simulations."""

        total_cash_flows = simulation_df.sum(axis=1)

        plt.figure(figsize=(8, 6))

        # Create Boxplot
        plt.boxplot(total_cash_flows, vert=True, patch_artist=True, boxprops=dict(facecolor="lightblue"))
        plt.ylabel('Total Discounted Cash Flow over Lifetime in Euro/kw')
        plt.title(
            f'Boxplot of Total Discounted Cash Flows (NPV) for {kw_dict.get(kwid_target)} '
            f'start_year {self.start_year}'
        )
        plt.grid(True)

        # Ensure the save folder exists
        os.makedirs(save_folder, exist_ok=True)

        # Generate a unique filename using KWID and start year
        filename = f"NPV_Boxplot_KWID_{kwid_target}_{kw_dict.get(kwid_target)}_start_year_{self.start_year}.png"
        filepath = os.path.join(save_folder, filename)

        # Save the figure
        plt.savefig(filepath, dpi=300, bbox_inches='tight')
        plt.close()  # Close the plot to free memory

        print(f"Boxplot saved successfully at: {filepath}")

    def plot_cumulative_distribution(self, simulation_df, kwid_target, save_folder="E:/monte_carlo_simulation/"):
        """Plots and saves the cumulative distribution function (CDF) of total cash flows over all Monte Carlo simulations."""
        total_cash_flows = simulation_df.sum(axis=1)

        # Sort the values
        sorted_cash_flows = np.sort(total_cash_flows)

        # Calculate the cumulative probabilities
        cdf = np.arange(1, len(sorted_cash_flows) + 1) / len(sorted_cash_flows)

        plt.figure(figsize=(10, 5))
        plt.plot(sorted_cash_flows, cdf, marker='.', linestyle='none')
        plt.xlabel('Total Cash Flow over Lifetime in Euro/kw')
        plt.ylabel('Cumulative Probability')
        plt.title(
            f'Cumulative Distribution of Total Discounted Cash Flows (NPV) for {kw_dict.get(kwid_target)} start_year {self.start_year}')
        plt.grid(True)

        # Ensure the save folder exists
        os.makedirs(save_folder, exist_ok=True)

        # Generate a unique filename using timestamp
        filename = f"CDF_NPV_KWID_{kwid_target}_{kw_dict.get(kwid_target)} for start_year {self.start_year}.png"
        filepath = os.path.join(save_folder, filename)

        # Save the figure
        plt.savefig(filepath, dpi=300, bbox_inches='tight')
        plt.close()  # Close the plot to free memory

        print(f"CDF plot saved successfully at: {filepath}")

#E:\monte_carlo_simulation

