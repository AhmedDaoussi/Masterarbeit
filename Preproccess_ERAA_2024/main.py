import pandas as pd

from preprocess import Preprocess

from preprocess import Preprocess

def main():
    # 🧭 Preprocess-Objekt erstellen (standardmäßig für 2024 konfiguriert)
    pre = Preprocess("config.yaml")

    # 🧰 Komplette Pipeline ausführen:
    # 1. Relevante Dateien filtern
    # 2. Unavailability Files erzeugen
    # 3. Shape-B Files erzeugen (inkl. Mapping)
    # 4. Wetterjahres-Dateien erzeugen
    # pre.run_full_pipeline()

    # 💡 Falls du nur einzelne Schritte ausführen willst, kannst du das so tun:
    #pre.filter_relevant_files()
    #pre.process_unavailability_files()
    #pre.calculate_special_region_files()
    #pre.generate_shape_b_files()
    pre.generate_weather_year_files()

if __name__ == "__main__":
    main()

