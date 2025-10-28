import os
import re
import yaml
import zipfile
import logging
import pandas as pd
import time
import gc
from datetime import timedelta
from concurrent.futures import ProcessPoolExecutor

# ----------------------------- Logger Setup -----------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)


# ----------------------------- Evaluation Klasse ------------------------------
class Evaluation:
    def __init__(self, config_path: str):
        """
        Lädt Konfiguration, Pfade und KWID/REGID Mapping.
        Erstellt die Output-Ordnerstruktur automatisch.
        """
        with open(config_path, "r", encoding="utf-8") as f:
            config = yaml.safe_load(f)

        # 📂 Pfad
        self.input_folder_path = config["paths"]["input_folder_path"]
        self.folder_path = config["paths"]["folder_path"]
        self.path_low_cut = config["paths"]["low_cut"]
        self.kwid_region_map = pd.read_excel(
            config["paths"]["kwid_region_map"],
            dtype={"KWID": "int32", "REGID": "int32"}
        )

        # 📅 Jahre
        self.start_year = config["years"]["start_year"]
        self.end_year = config["years"]["end_year"]

        # 📊 Mappings
        self.tech_to_abbr = config["TECH_TO_ABBR"]
        self.region_zone_mapping = config["region_zone_mapping"]
        self.kwid_map = self._extract_kwid_mapping()

        logger.info(f"✅ {len(self.kwid_map)} KWIDs aus Config geladen ({len(self.region_zone_mapping)} Regionen).")

        # 🧾 Pattern für .dat Dateien
        self.reg_pattern_template = r'daoussi_Wetterjahr_[ab]_\d{4}/SQLLoader/SQLLoader_RegResults_\d{4}_0_\d+\.dat'
        self.kw_pattern_template = r'daoussi_Wetterjahr_[ab]_\d{4}/SQLLoader/SQLLoader_KWResults_\d{4}_0_\d+\.dat'

        # 📁 Haupt-Outputordner
        self.results_path = os.path.join(self.folder_path, "results")
        os.makedirs(self.results_path, exist_ok=True)

    # -------------------------------------------------------------------------
    def _extract_kwid_mapping(self):
        """Extrahiert alle KWIDs aus region_zone_mapping."""
        kwids = set()
        for region, techs in self.region_zone_mapping.items():
            for tech, info in techs.items():
                if info.get("kwid_shape_a"):
                    kwids.add(info["kwid_shape_a"])
                if info.get("kwid_shape_b"):
                    kwids.add(info["kwid_shape_b"])
                if info.get("kwid"):
                    kwids.add(info["kwid"])
        return kwids

    # -------------------------------------------------------------------------
    @staticmethod
    def _process_zip(zip_file, year, reg_pattern_template, kw_pattern_template, kwid_filter: set, low_cut_df, output_base_path):
        """
        Verarbeitet eine einzelne ZIP-Datei:
        - REG Dateien → Marktpreise berechnen
        - KW Dateien → Erzeugungsdaten extrahieren
        Speichert direkt als Parquet in strukturierte Ordner.
        """
        if not os.path.exists(zip_file):
            logger.warning(f"⚠️ ZIP-Datei nicht gefunden: {zip_file}")
            return

        reg_out_dir = os.path.join(output_base_path, str(year), "reg")
        kw_out_dir = os.path.join(output_base_path, str(year), "kw")
        os.makedirs(reg_out_dir, exist_ok=True)
        os.makedirs(kw_out_dir, exist_ok=True)

        try:
            with zipfile.ZipFile(zip_file, "r") as zf:
                file_list = zf.namelist()
                reg_pat = re.compile(reg_pattern_template)
                kw_pat = re.compile(kw_pattern_template)

                # ---------------- REG FILES ----------------
                reg_files = [f for f in file_list if reg_pat.match(f)]
                if reg_files:
                    reg_dataframes = []
                    for rf in reg_files:
                        with zf.open(rf) as f:
                            df = pd.read_csv(f, delimiter=",", header=None)
                            df1 = df.iloc[10:].reset_index(drop=True)
                            df1 = pd.DataFrame([x.split(";") for x in df1[0]])
                            df2 = df1.iloc[:, :6].copy()
                            df2.columns = ['VARID', 'REGID', 'SIMID', 'JAHR', 'ZENR', 'MARKTPREIS']
                            df2['REGIONENMARKUP'] = df1.iloc[:, 7]
                            df2['STARTKOSTEN'] = df1.iloc[:, 53]

                            df2 = df2[['REGID', 'JAHR', 'ZENR', 'MARKTPREIS', 'REGIONENMARKUP', 'STARTKOSTEN']]
                            df2['ZENR'] = pd.to_numeric(df2['ZENR'], errors='coerce')
                            df2['JAHR'] = pd.to_numeric(df2['JAHR'], errors='coerce')
                            df2.rename(columns={'ZENR': 'PKTNR'}, inplace=True)

                            df2 = pd.merge(
                                df2,
                                low_cut_df[['JAHR', 'PKTNR', 'LOW_CUT_TERM']],
                                on=['JAHR', 'PKTNR']
                            )
                            df2['FINAL_MARKTPREIS'] = (
                                df2['MARKTPREIS'].astype('float32') +
                                df2['REGIONENMARKUP'].astype('float32') +
                                df2['STARTKOSTEN'].astype('float32')
                            ) * df2['LOW_CUT_TERM'].astype('float32')

                            reg_dataframes.append(df2[['REGID', 'JAHR', 'PKTNR', 'FINAL_MARKTPREIS']])

                    out_path = os.path.join(
                        reg_out_dir,
                        f"REG_{os.path.basename(zip_file).replace('.zip', '.parquet')}"
                    )
                    pd.concat(reg_dataframes, ignore_index=True).astype({
                        "REGID": "int32",
                        "JAHR": "int32",
                        "PKTNR": "int32",
                        "FINAL_MARKTPREIS": "float32"
                    }).to_parquet(out_path, compression="snappy")
                    logger.info(f"📊 REG-Dateien aus {zip_file} → {out_path}")

                # ---------------- KW FILES ----------------
                kw_files = [f for f in file_list if kw_pat.match(f)]
                if kw_files:
                    kw_dataframes = []
                    for kf in kw_files:
                        with zf.open(kf) as f:
                            df = pd.read_csv(f, delimiter=",", header=None)
                            df1 = df.iloc[10:].reset_index(drop=True)
                            df1 = pd.DataFrame([x.split(";") for x in df1[0]])
                            df1.columns = [
                                "VARID", "KWID", "SIMID", "JAHR", "ZENR", "RANGLISTE", "DB", "KAPREVENUE",
                                "SEKRESREVENUE", "MINRESREVENUE", "VARKOSTEN", "PVERF", "PINSTALL", "EINSATZ",
                                "ZWANG", "MINRESERVE", "SEKRESERVE", "FREIELSTG", "VERFB", "REVISIONEN", "AUSFALL",
                                "KONTSTUNDEN", "STARTKOSTEN"
                            ][:df1.shape[1]]

                            df1 = df1[["KWID", "JAHR", "ZENR", "PINSTALL", "EINSATZ", "VARKOSTEN"]]
                            df1["KWID"] = pd.to_numeric(df1["KWID"], errors="coerce")
                            df1 = df1[df1["KWID"].isin(kwid_filter)]
                            df1["JAHR"] = pd.to_numeric(df1["JAHR"], errors="coerce")
                            df1.rename(columns={"ZENR": "PKTNR"}, inplace=True)

                            kw_dataframes.append(df1)

                    out_path = os.path.join(
                        kw_out_dir,
                        f"KW_{os.path.basename(zip_file).replace('.zip', '.parquet')}"
                    )
                    pd.concat(kw_dataframes, ignore_index=True).astype({
                        "KWID": "int32",
                        "JAHR": "int32",
                        "PKTNR": "int32",
                        "PINSTALL": "float32",
                        "EINSATZ": "float32",
                        "VARKOSTEN": "float32"
                    }).to_parquet(out_path, compression="snappy")
                    logger.info(f"⚡ KW-Dateien aus {zip_file} → {out_path}")

        except Exception as e:
            logger.error(f"❌ Fehler beim Verarbeiten von {zip_file}: {e}")

    # -------------------------------------------------------------------------
    def generate_parquet_files(self, batch_size=2):
        """
        Liest die ZIP-Dateien ein und erzeugt die Parquet-Dateien (REG & KW).
        """
        years = list(range(self.start_year, self.end_year + 1))
        low_cut_df = pd.read_excel(
            self.path_low_cut,
            dtype={"JAHR": "int32", "PKTNR": "int32", "LOW_CUT_TERM": "float32"}
        )
        total_start = time.time()

        for i in range(0, len(years), batch_size):
            batch_years = years[i:i+batch_size]
            logger.info(f"🚀 Starte Batch {i//batch_size+1}: {batch_years}")

            for year in batch_years:
                start_time = time.time()
                year_out_path = os.path.join(self.results_path, str(year))
                reg_dir = os.path.join(year_out_path, "reg")
                kw_dir = os.path.join(year_out_path, "kw")
                os.makedirs(reg_dir, exist_ok=True)
                os.makedirs(kw_dir, exist_ok=True)

                zip_files = [
                    (f"{self.input_folder_path}/{year}/daoussi_Wetterjahr_a_{year}.zip", year),
                    (f"{self.input_folder_path}/{year}/daoussi_Wetterjahr_b_{year}.zip", year)
                ]

                with ProcessPoolExecutor(max_workers=2) as exe:
                    exe.map(
                        self._process_zip,
                        [p[0] for p in zip_files],
                        [p[1] for p in zip_files],
                        [self.reg_pattern_template] * len(zip_files),
                        [self.kw_pattern_template] * len(zip_files),
                        [self.kwid_map] * len(zip_files),
                        [low_cut_df] * len(zip_files),
                        [self.results_path] * len(zip_files),
                    )

                elapsed_time = time.time() - start_time
                logger.info(f"🕒 Parquet-Erstellung für Jahr {year}: {timedelta(seconds=int(elapsed_time))}")

        total_elapsed = time.time() - total_start
        logger.info(f"⏰ Gesamtzeit für Parquet-Erstellung: {timedelta(seconds=int(total_elapsed))}")

    # -------------------------------------------------------------------------
    def calculate_profitability(self, batch_size=2):
        """
        Berechnet die Profitabilität ausschließlich aus vorhandenen Parquet-Dateien.
        (Kein erneutes Einlesen der ZIP-Dateien!)
        """
        years = list(range(self.start_year, self.end_year + 1))
        total_start = time.time()

        for i in range(0, len(years), batch_size):
            batch_years = years[i:i+batch_size]
            logger.info(f"📊 Starte Profitabilitätsberechnung Batch {i//batch_size+1}: {batch_years}")

            for year in batch_years:
                start_time = time.time()
                year_out_path = os.path.join(self.results_path, str(year))
                reg_dir = os.path.join(year_out_path, "reg")
                kw_dir = os.path.join(year_out_path, "kw")
                profit_dir = os.path.join(year_out_path, "profitability")
                os.makedirs(profit_dir, exist_ok=True)

                # 🧾 Vorhandene Parquet-Dateien laden
                reg_files = [os.path.join(reg_dir, f) for f in os.listdir(reg_dir) if f.endswith(".parquet")]
                kw_files = [os.path.join(kw_dir, f) for f in os.listdir(kw_dir) if f.endswith(".parquet")]

                reg_df = pd.concat(
                    (pd.read_parquet(f, columns=["REGID", "PKTNR", "JAHR", "FINAL_MARKTPREIS"]) for f in reg_files),
                    ignore_index=True
                ).astype({"REGID": "int32", "PKTNR": "int32", "JAHR": "int32", "FINAL_MARKTPREIS": "float32"})

                kw_df = pd.concat(
                    (pd.read_parquet(f, columns=["KWID", "PKTNR", "JAHR", "PINSTALL", "EINSATZ", "VARKOSTEN"]) for f in kw_files),
                    ignore_index=True
                ).astype({
                    "KWID": "int32",
                    "PKTNR": "int32",
                    "JAHR": "int32",
                    "PINSTALL": "float32",
                    "EINSATZ": "float32",
                    "VARKOSTEN": "float32"
                })

                # KWID → REGID Mapping
                kw_df = pd.merge(
                    kw_df,
                    self.kwid_region_map[["KWID", "REGID"]].astype({"KWID": "int32", "REGID": "int32"}),
                    on="KWID", how='left'
                )

                # 🔗 Merge
                merged = pd.merge(kw_df, reg_df, on=["REGID", "PKTNR", "JAHR"],how='left')

                # 💰 Deckungsbeitrag
                merged["Deckungsbeitrag_hr"] = (
                    (merged["FINAL_MARKTPREIS"] + merged["VARKOSTEN"]) * merged["EINSATZ"]
                )

                agg = merged.groupby(["JAHR", "KWID"], as_index=False).agg({
                    "PINSTALL": "mean",
                    "Deckungsbeitrag_hr": "sum"
                })

                mask = agg["PINSTALL"] > 0
                agg["Annual_Profit_per_kw"] = 0
                agg.loc[mask, "Annual_Profit_per_kw"] = (
                    agg.loc[mask, "Deckungsbeitrag_hr"] / (agg.loc[mask, "PINSTALL"] * 1000)
                ).round(1)

                agg = agg.sort_values(by=["JAHR", "Annual_Profit_per_kw"], ascending=[True, False]).reset_index(drop=True)
                out_profit = os.path.join(profit_dir, f"kw_profitability_{year}.xlsx")
                agg['Annual_Profit_per_kw'] = round(agg['Annual_Profit_per_kw'], 2)
                agg = pd.merge(agg, self.kwid_region_map, on='KWID', how='left')
                agg.to_excel(out_profit, index=False)
                logger.info(f"✅ Profitabilität für Jahr {year} gespeichert → {out_profit}")

                elapsed_time = time.time() - start_time
                logger.info(f"🕒 Berechnungszeit für Jahr {year}: {timedelta(seconds=int(elapsed_time))}")

                # 🧹 Speicher freigeben
                del reg_df, kw_df, merged, agg
                gc.collect()

        total_elapsed = time.time() - total_start
        logger.info(f"⏰ Gesamtzeit für Profitabilitätsberechnung: {timedelta(seconds=int(total_elapsed))}")
