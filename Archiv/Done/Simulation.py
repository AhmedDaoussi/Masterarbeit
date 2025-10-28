# === Datei: Simulation.py ===
import os
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np


class Simulation:
    def __init__(self, folder_path, weather_years, start_year, life_time, inflation_rate):
        self.folder_path = folder_path
        self.weather_years = weather_years
        self.start_year = start_year
        self.life_time = life_time
        self.inflation_rate = inflation_rate
        self.num_simulations = 10000

    def read_contribution_margins(self):
        all_dfs = []
        for year in self.weather_years:
            file_path = os.path.join(
                self.folder_path,
                f"{year}/kw_profitability_kw/kw_profitability_kw_{year}.xlsx"
            )
            if os.path.exists(file_path):
                df = pd.read_excel(file_path)
                df["weather_year"] = year
                all_dfs.append(df)
            else:
                print(f"[SIM] File not found: {file_path}")

        if not all_dfs:
            print("[SIM] No files found in the given range.")
            return None

        all_data = pd.concat(all_dfs, ignore_index=True)
        print("[SIM] All data combined successfully!")

        all_data["Discounted_Profit/installed_kw"] = all_data.apply(
            lambda row: row["Annual_Profit/installed_kw"] /
            ((1 + self.inflation_rate) ** (row["JAHR"] - self.start_year))
            if row["JAHR"] > self.start_year else row["Annual_Profit/installed_kw"], axis=1
        )

        # Shape-Korrektur für Wind
        mask = all_data["Technology"].isin(["wind_on", "wind_off"])
        all_data.loc[mask & all_data["JAHR"].between(2023, 2032), "Shape"] = "a"
        all_data.loc[mask & all_data["JAHR"].between(2033, 2050), "Shape"] = "b"

        # Falls KW nicht existiert, neu erstellen
        if "KW" not in all_data.columns:
            all_data["KW"] = all_data["Region"] + "_" + all_data["Technology"]

        all_data.to_excel('E:/results/all_data_kw.xlsx', index=False)   # << Pfad anpassen
        return all_data

    def monte_carlo_simulation(self, df, kw_target):
        df_filtered = df[df['KW'] == kw_target].copy()
        if df_filtered.empty:
            raise ValueError(f"No data found for KW={kw_target}")

        simulation_results = []
        for sim in range(self.num_simulations):
            cash_flows = []
            sampled_weather_years = np.random.choice(
                df_filtered['weather_year'], size=self.life_time + 1, replace=True
            )
            for year in sampled_weather_years:
                sampled_value = df_filtered[df_filtered['weather_year'] == year]['Annual_Profit/installed_kw'] \
                    .sample(n=1).values[0]
                cash_flows.append(sampled_value)
            simulation_results.append(cash_flows)

        years = [str(self.start_year + i) for i in range(self.life_time + 1)]
        return pd.DataFrame(simulation_results, columns=years)

    def plot_cumulative_distribution(self, simulation_df, kw_target, save_folder="E:/monte_carlo_simulation_kw/"):
        total_cash_flows = simulation_df.sum(axis=1)
        sorted_cash_flows = np.sort(total_cash_flows)
        cdf = np.arange(1, len(sorted_cash_flows) + 1) / len(sorted_cash_flows)

        plt.figure(figsize=(10, 5))
        plt.plot(sorted_cash_flows, cdf, marker='.', linestyle='none')
        plt.xlabel('Total Cash Flow over Lifetime in Euro/kw')
        plt.ylabel('Cumulative Probability')
        plt.title(f'Cumulative Distribution of NPV for {kw_target}, start_year {self.start_year}')
        plt.grid(True)

        os.makedirs(save_folder, exist_ok=True)
        filename = f"CDF_NPV_{kw_target}_start_year_{self.start_year}.png"
        filepath = os.path.join(save_folder, filename)
        plt.savefig(filepath, dpi=300, bbox_inches='tight')
        plt.close()
        print(f"[SIM] CDF plot saved: {filepath}")
