import yaml
from read_files import DataLoader

if __name__ == "__main__":
    with open("config.yaml", "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)

    loader = DataLoader(config)

    # Beispiel: Wetterjahr laden
    wetterjahr = 1992
    loader.load_parquet_for_weather_year(wetterjahr)

    # Beispiel: DAT Study laden
    study_jahr = 2026
    loader.load_dat_for_study_year(wetterjahr, study_jahr, "both")

    # 🧭 Interaktives Filtern starten
    loader.interactive_filter()
print('a')