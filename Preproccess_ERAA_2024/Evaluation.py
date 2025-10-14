# === Datei: Evaluation.py ===
import os
import pandas as pd

region_mapping = {
    1: "Germany", 2: "Baltics", 3: "Turkey", 4: "Balkans", 5: "France", 6: "Belgium",
    7: "Austria", 8: "Switzerland", 9: "Netherlands", 10: "Poland", 11: "Czech Republic",
    12: "DenmarkWest", 13: "DenmarkEast", 14: "SloCro", 15: "SWE1and2", 16: "IT_CN",
    17: "England", 18: "IT_N", 19: "Spain", 20: "Romania", 21: "Slovakia", 22: "Hungary",
    23: "Bulgaria", 24: "Greece", 25: "Portugal", 26: "Norway", 27: "Finland",
    28: "IT_CS", 29: "SWE3", 30: "SWE4", 31: "IT_S", 32: "IT_SI", 33: "IT_SA", 34: "IT_CA"
}


class Evaluation:
    def __init__(self, folder_path, weather_year, start_year, end_year):
        self.folder_path = folder_path
        self.weather_year = weather_year
        self.start_year = start_year
        self.end_year = end_year

    def evaluate_power_plant_files(self):
        # Input: bestehende KWID-basierte Profitability-Datei
        input_path = os.path.join(
            self.folder_path,
            f"{self.weather_year}/kw_profitability/kw_profitability_{self.weather_year}.xlsx"
        )

        if not os.path.exists(input_path):
            print(f"[EVAL] Input file not found: {input_path}")
            return

        df = pd.read_excel(input_path)
        print(f"[EVAL] Loaded input file: {input_path}")

        # Falls Region nur als REGID vorliegt
        if "REGID" in df.columns and "Region" not in df.columns:
            df["Region"] = df["REGID"].map(region_mapping)

        # --- Technologie-Spalte harmonisieren ---
        if "Technology" in df.columns:
            df["Technology"] = df["Technology"].astype(str).str.lower()

            df.loc[df["Technology"].str.contains("pv"), "Technology"] = "pv"
            df.loc[df["Technology"].str.contains("csp"), "Technology"] = "pv"
            df.loc[df["Technology"].str.contains("wind_on"), "Technology"] = "wind_on"
            df.loc[df["Technology"].str.contains("wind_off"), "Technology"] = "wind_off"

        result_list = []
        for (year, region, tech), group in df.groupby(["JAHR", "Region", "Technology"]):
            if tech in ["wind_on", "wind_off"]:
                shape = "a" if year <= 2032 else "b"
            elif tech == "pv":
                shape = None
            else:
                shape = None

            new_kw = f"{region}_{tech}"
            avg_profit = group["Annual_Profit/installed_kw"].mean()

            result_list.append({
                "JAHR": year,
                "Region": region,
                "Technology": tech,
                "Shape": shape,
                "KW": new_kw,
                "Annual_Profit/installed_kw": avg_profit
            })

        result_df = pd.DataFrame(result_list)
        result_df["Annual_Profit/installed_kw"] = pd.to_numeric(
            result_df["Annual_Profit/installed_kw"], errors="coerce"
        ).round(1)

        # Neue Ausgabe in separatem Ordner
        output_path = os.path.join(
            self.folder_path,
            f"{self.weather_year}/kw_profitability_kw/kw_profitability_kw_{self.weather_year}.xlsx"
        )
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        result_df.to_excel(output_path, index=False)

        print(f"[EVAL] Results saved to: {output_path}")
