import os
import re
import time
import zipfile
import logging
import pandas as pd

# ----------------------------- Logger Setup -----------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

# ----------------------------- Decorator für Zeitmessung ----------------------
def log_runtime(func):
    """Decorator misst Laufzeit und loggt Start/Ende + Dauer."""
    def wrapper(*args, **kwargs):
        start_time = time.time()
        logger.info(f"⏳ Starte {func.__name__} ...")
        result = func(*args, **kwargs)
        end_time = time.time()
        duration = end_time - start_time
        logger.info(f"✅ Fertig: {func.__name__} in {duration:.2f} Sekunden")
        return result
    return wrapper


# ----------------------------- DataLoader Klasse ------------------------------
class DataLoader:
    def __init__(self, config):
        """
        Lädt Pfade und Patterns aus Config.
        """
        self.input_folder_path = config["paths"]["input_folder_path"]
        self.results_path = os.path.join(config["paths"]["folder_path"], "results")

        # Regex Patterns für .dat Dateien
        self.reg_pattern_template = r'daoussi_Wetterjahr_[ab]_\d{4}/SQLLoader/SQLLoader_RegResults_(\d{4})_0_\d+\.dat'
        self.kw_pattern_template  = r'daoussi_Wetterjahr_[ab]_\d{4}/SQLLoader/SQLLoader_KWResults_(\d{4})_0_\d+\.dat'

        # 📦 Speicher für DataFrames
        self.dataframes = {}

        # 📁 Speicherpfad für gefilterte Dateien
        self.filtered_save_path = r"C:\Users\ahmed\Desktop\Meeting"
        os.makedirs(self.filtered_save_path, exist_ok=True)

    # -------------------------------------------------------------------------
    @log_runtime
    def load_parquet_for_weather_year(self, weather_year: int):
        """
        📂 Lädt REG- und KW-Parquet-Dateien für ein gewähltes Wetterjahr.
        Gibt zwei DataFrames zurück: reg_df, kw_df
        """
        year_path = os.path.join(self.results_path, str(weather_year))
        reg_dir = os.path.join(year_path, "reg")
        kw_dir = os.path.join(year_path, "kw")

        if not os.path.exists(reg_dir) or not os.path.exists(kw_dir):
            raise FileNotFoundError(f"❌ Parquet-Verzeichnisse nicht gefunden für Wetterjahr {weather_year}")

        reg_files = [os.path.join(reg_dir, f) for f in os.listdir(reg_dir) if f.endswith(".parquet")]
        kw_files = [os.path.join(kw_dir, f) for f in os.listdir(kw_dir) if f.endswith(".parquet")]

        if not reg_files:
            raise FileNotFoundError(f"❌ Keine REG-Parquet-Dateien für {weather_year}")
        if not kw_files:
            raise FileNotFoundError(f"❌ Keine KW-Parquet-Dateien für {weather_year}")

        reg_df = pd.concat((pd.read_parquet(f) for f in reg_files), ignore_index=True)
        kw_df = pd.concat((pd.read_parquet(f) for f in kw_files), ignore_index=True)

        # 📦 speichern zur späteren Verwendung
        self.dataframes[f"reg_{weather_year}"] = reg_df
        self.dataframes[f"kw_{weather_year}"] = kw_df

        logger.info(f"✅ REG geladen: {len(reg_df):,} Zeilen — Wetterjahr {weather_year}")
        logger.info(f"✅ KW  geladen: {len(kw_df):,} Zeilen — Wetterjahr {weather_year}")

        return reg_df, kw_df

    # -------------------------------------------------------------------------
    @log_runtime
    def load_dat_for_study_year(self, weather_year: int, study_year: int, file_type: str = "both"):
        """
        📦 Öffnet ZIP(s) für ein Wetterjahr und liest alle .dat Dateien,
        deren Study-Jahr (im Dateinamen nach 'RegResults_' oder 'KWResults_') = study_year ist.
        file_type: 'reg', 'kw' oder 'both'
        Gibt die entsprechenden DataFrames zurück.
        """
        weather_dir = os.path.join(self.input_folder_path, str(weather_year))
        zip_a = os.path.join(weather_dir, f"daoussi_Wetterjahr_a_{weather_year}.zip")
        zip_b = os.path.join(weather_dir, f"daoussi_Wetterjahr_b_{weather_year}.zip")

        zip_files = []
        if os.path.exists(zip_a): zip_files.append(zip_a)
        if os.path.exists(zip_b): zip_files.append(zip_b)

        if not zip_files:
            raise FileNotFoundError(f"❌ Keine ZIP-Dateien gefunden für Wetterjahr {weather_year}")

        reg_pattern = re.compile(self.reg_pattern_template)
        kw_pattern = re.compile(self.kw_pattern_template)

        reg_frames = []
        kw_frames = []

        for z in zip_files:
            with zipfile.ZipFile(z, "r") as zf:
                for filename in zf.namelist():
                    # ---------------- REG ----------------
                    if (file_type in ["reg", "both"]) and reg_pattern.match(filename):
                        study_match = reg_pattern.match(filename)
                        if study_match and int(study_match.group(1)) == study_year:
                            with zf.open(filename) as f:
                                df_raw = pd.read_csv(f, delimiter=",", header=None)
                                df_data = df_raw.iloc[10:].reset_index(drop=True)
                                df_data = pd.DataFrame([x.split(";") for x in df_data[0]])
                                reg_frames.append(df_data)

                    # ---------------- KW ----------------
                    if (file_type in ["kw", "both"]) and kw_pattern.match(filename):
                        study_match = kw_pattern.match(filename)
                        if study_match and int(study_match.group(1)) == study_year:
                            with zf.open(filename) as f:
                                df_raw = pd.read_csv(f, delimiter=",", header=None)
                                df_data = df_raw.iloc[10:].reset_index(drop=True)
                                df_data = pd.DataFrame([x.split(";") for x in df_data[0]])
                                kw_frames.append(df_data)

        reg_df = pd.concat(reg_frames, ignore_index=True) if reg_frames else None
        kw_df = pd.concat(kw_frames, ignore_index=True) if kw_frames else None

        if reg_df is not None:
            self.dataframes[f"reg_dat_{study_year}"] = reg_df
            logger.info(f"✅ REG DAT {study_year}: {len(reg_df):,} Zeilen")

        if kw_df is not None:
            self.dataframes[f"kw_dat_{study_year}"] = kw_df
            logger.info(f"✅ KW DAT {study_year}: {len(kw_df):,} Zeilen")

        if file_type in ["reg", "both"] and reg_df is None:
            logger.warning(f"⚠️ Keine REG-DAT Dateien für Study Jahr {study_year} gefunden.")
        if file_type in ["kw", "both"] and kw_df is None:
            logger.warning(f"⚠️ Keine KW-DAT Dateien für Study Jahr {study_year} gefunden.")

        return reg_df, kw_df

    # -------------------------------------------------------------------------
    def interactive_filter(self):
        """
        🧭 Interaktives Filtern von DataFrames nach Spaltenwerten.
        - Fragt, welches DF gefiltert werden soll (nach Namen aus self.dataframes)
        - Erlaubt mehrfaches Filtern nach (Spalte, Wert)
        - Speichert das gefilterte DF unter neuem Namen und zusätzlich als Excel-Datei.
        """
        while True:
            if not self.dataframes:
                print("❌ Keine DataFrames geladen.")
                break

            print("\n📊 Verfügbare DataFrames:")
            for name in self.dataframes.keys():
                print(f"  - {name}")

            df_name = input("\n👉 Welches DataFrame möchtest du filtern? (oder 'exit' zum Abbrechen): ")
            if df_name.lower() == "exit":
                print("🚪 Filtervorgang beendet.")
                break

            if df_name not in self.dataframes:
                print("❌ Ungültiger Name.")
                continue

            df = self.dataframes[df_name]
            filtered_df = df.copy()

            # Mehrfachfilter
            while True:
                print(f"\n📋 Spalten in {df_name}:")
                print(list(filtered_df.columns))
                column = input("\n🪄 Spaltenname für Filter (oder 'done' wenn fertig): ")
                if column.lower() == "done":
                    break
                if column not in filtered_df.columns:
                    print("❌ Spalte nicht gefunden.")
                    continue

                filter_value = input(f"🔸 Wert für Filter in Spalte '{column}': ")

                # Versuch, Zahl zu interpretieren
                if filter_value.isdigit():
                    filter_value = int(filter_value)
                else:
                    try:
                        filter_value = float(filter_value)
                    except ValueError:
                        pass

                # Filtern
                filtered_df = filtered_df[filtered_df[column] == filter_value]
                print(f"✅ Gefiltert: {len(filtered_df):,} Zeilen übrig")

            # Neues gefiltertes DF speichern
            new_name = input(f"💾 Name für gefiltertes DataFrame (Standard: {df_name}_filtered): ") or f"{df_name}_filtered"
            self.dataframes[new_name] = filtered_df
            print(f"✅ Gefiltertes DataFrame unter '{new_name}' gespeichert ({len(filtered_df):,} Zeilen).")

            # 📝 Excel-Datei speichern
            excel_path = os.path.join(self.filtered_save_path, f"{new_name}.xlsx")
            try:
                filtered_df.to_excel(excel_path, index=False)
                print(f"💾 Excel-Datei erfolgreich gespeichert unter: {excel_path}")
            except Exception as e:
                print(f"❌ Fehler beim Speichern als Excel: {e}")

            # Wiederholen?
            again = input("\n🔁 Noch ein DataFrame filtern? (y/n): ")
            if again.lower() != "y":
                print("🏁 Filterprozess abgeschlossen.")
                break
