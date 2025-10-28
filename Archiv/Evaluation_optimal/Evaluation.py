import os
import re
import yaml
import zipfile
import logging
import pandas as pd
import time
import gc
import multiprocessing
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

        # 📂 Pfade
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
        self.kw_pattern_template  = r'daoussi_Wetterjahr_[ab]_\d{4}/SQLLoader/SQLLoader_KWResults_\d{4}_0_\d+\.dat'

        # 📁 Haupt-Outputordner
        self.results_path = os.path.join(self.folder_path, "results")
        os.makedirs(self.results_path, exist_ok=True)

        # Parquet-Optionen
        self.parquet_compression = "zstd"    # schneller & kleiner als snappy
        self.parquet_engine      = "pyarrow" # nutzt pyarrow (empfohlen)

    # -------------------------------------------------------------------------
    def _extract_kwid_mapping(self):
        """Extrahiert alle KWIDs aus region_zone_mapping."""
        kwids = set()
        for _, techs in self.region_zone_mapping.items():
            for _, info in techs.items():
                if info.get("kwid_shape_a"):
                    kwids.add(info["kwid_shape_a"])
                if info.get("kwid_shape_b"):
                    kwids.add(info["kwid_shape_b"])
                if info.get("kwid"):
                    kwids.add(info["kwid"])
        return kwids

    # -------------------------------------------------------------------------
    @staticmethod
    def _read_semicolon_dat_from_zip(zf: zipfile.ZipFile, member_path: str, skip_rows: int = 10) -> pd.DataFrame:
        """
        Liest eine .dat-Datei aus dem ZIP so ein, wie es der Originalcode tut:
        - Die Datei wird zunächst als 'CSV mit 1 Spalte' gelesen (weil ursprünglich ',' als delimiter genutzt wurde),
          dann pro Zeile anhand ';' gesplittet.
        - Wir überspringen die ersten 10 Zeilen (Metadaten) wie im Original.
        Hinweis: Für sehr große Dateien könnte man hier auf echtes Zeilen-Streaming umbauen.
        """
        with zf.open(member_path) as f:
            df_raw = pd.read_csv(f, delimiter=",", header=None)
        # Erste 10 Zeilen verwerfen, danach jede Zeile am ';' splitten:
        df1 = df_raw.iloc[skip_rows:].reset_index(drop=True)
        df1 = pd.DataFrame([x.split(";") for x in df1[0]])
        return df1

    # -------------------------------------------------------------------------
    @staticmethod
    def _ensure_dirs(*dirs):
        for d in dirs:
            os.makedirs(d, exist_ok=True)

    # -------------------------------------------------------------------------
    @staticmethod
    def _safe_concat(frames, dtype_map):
        """
        Speicherschonendes concat mit finalem astype (vermeidet mehrfaches Casting).
        """
        if not frames:
            return None
        out = pd.concat(frames, ignore_index=True, copy=False)
        if dtype_map:
            out = out.astype(dtype_map, copy=False)
        return out

    # -------------------------------------------------------------------------
    @staticmethod
    def _process_zip(zip_file,
                     year,
                     reg_pattern_template,
                     kw_pattern_template,
                     kwid_filter: set,
                     low_cut_df_path: str,
                     output_base_path: str,
                     parquet_engine: str,
                     parquet_compression: str):
        """
        Verarbeitet eine einzelne ZIP-Datei:
        - REG-Dateien → Marktpreise berechnen
        - KW-Dateien  → Erzeugungsdaten extrahieren
        Speichert direkt als Parquet in strukturierte Ordner (pro ZIP eine Datei).
        """
        if not os.path.exists(zip_file):
            logger.warning(f"⚠️ ZIP-Datei nicht gefunden: {zip_file}")
            return

        year_out = os.path.join(output_base_path, str(year))
        reg_out_dir = os.path.join(year_out, "reg")
        kw_out_dir  = os.path.join(year_out, "kw")
        Evaluation._ensure_dirs(reg_out_dir, kw_out_dir)

        # low_cut_df je Prozess laden (vermeidet großes Pickling)
        low_cut_df = pd.read_excel(
            low_cut_df_path,
            dtype={"JAHR": "int32", "PKTNR": "int32", "LOW_CUT_TERM": "float32"}
        )

        try:
            with zipfile.ZipFile(zip_file, "r") as zf:
                file_list = zf.namelist()
                reg_pat = re.compile(reg_pattern_template)
                kw_pat  = re.compile(kw_pattern_template)

                # ---------------- REG FILES ----------------
                reg_files = [f for f in file_list if reg_pat.match(f)]
                if reg_files:
                    reg_frames = []
                    for rf in reg_files:
                        df1 = Evaluation._read_semicolon_dat_from_zip(zf, rf, skip_rows=10)
                        # df1 hat viele Spalten; wir greifen die benötigten Indizes wie im Original zu:
                        # Erste 6 → ['VARID','REGID','SIMID','JAHR','ZENR','MARKTPREIS']
                        df2 = df1.iloc[:, :6].copy()
                        df2.columns = ['VARID', 'REGID', 'SIMID', 'JAHR', 'ZENR', 'MARKTPREIS']
                        # Spalte 7 → REGIONENMARKUP, Spalte 53 → STARTKOSTEN (Null-basiert beachten!)
                        df2['REGIONENMARKUP'] = df1.iloc[:, 7]
                        df2['STARTKOSTEN']    = df1.iloc[:, 53]

                        # Minimal halten:
                        df2 = df2[['REGID', 'JAHR', 'ZENR', 'MARKTPREIS', 'REGIONENMARKUP', 'STARTKOSTEN']]
                        # Typen früh setzen (spart Merge-Kosten)
                        df2['ZENR'] = pd.to_numeric(df2['ZENR'], errors='coerce')
                        df2['JAHR'] = pd.to_numeric(df2['JAHR'], errors='coerce')
                        df2.rename(columns={'ZENR': 'PKTNR'}, inplace=True)

                        df2 = pd.merge(
                            df2,
                            low_cut_df[['JAHR', 'PKTNR', 'LOW_CUT_TERM']],
                            on=['JAHR', 'PKTNR'],
                            how='inner'
                        )

                        # Finalpreis
                        # (float32 spart RAM, reicht hier vollkommen)
                        df2['FINAL_MARKTPREIS'] = (
                            df2['MARKTPREIS'].astype('float32') +
                            df2['REGIONENMARKUP'].astype('float32') +
                            df2['STARTKOSTEN'].astype('float32')
                        ) * df2['LOW_CUT_TERM'].astype('float32')

                        reg_frames.append(df2[['REGID', 'JAHR', 'PKTNR', 'FINAL_MARKTPREIS']])
                        del df1, df2

                    reg_out_path = os.path.join(
                        reg_out_dir,
                        f"REG_{os.path.basename(zip_file).replace('.zip', '.parquet')}"
                    )
                    reg_df = Evaluation._safe_concat(
                        reg_frames,
                        {"REGID": "int32", "JAHR": "int32", "PKTNR": "int32", "FINAL_MARKTPREIS": "float32"}
                    )
                    if reg_df is not None and len(reg_df):
                        reg_df.to_parquet(reg_out_path, compression=parquet_compression, engine=parquet_engine)
                        logger.info(f"📊 REG aus {zip_file} → {reg_out_path} ({len(reg_df):,} Zeilen)")
                    del reg_frames, reg_df

                # ---------------- KW FILES ----------------
                kw_files = [f for f in file_list if kw_pat.match(f)]
                if kw_files:
                    kw_frames = []
                    for kf in kw_files:
                        df1 = Evaluation._read_semicolon_dat_from_zip(zf, kf, skip_rows=10)

                        # Spaltenbelegung wie im Original (auf die existierenden begrenzen)
                        cols = [
                            "VARID", "KWID", "SIMID", "JAHR", "ZENR", "RANGLISTE", "DB", "KAPREVENUE",
                            "SEKRESREVENUE", "MINRESREVENUE", "VARKOSTEN", "PVERF", "PINSTALL", "EINSATZ",
                            "ZWANG", "MINRESERVE", "SEKRESERVE", "FREIELSTG", "VERFB", "REVISIONEN", "AUSFALL",
                            "KONTSTUNDEN", "STARTKOSTEN"
                        ][:df1.shape[1]]
                        df1.columns = cols

                        df1 = df1[["KWID", "JAHR", "ZENR", "PINSTALL", "EINSATZ", "VARKOSTEN"]]
                        # Typen:
                        df1["KWID"] = pd.to_numeric(df1["KWID"], errors="coerce")
                        df1 = df1[df1["KWID"].isin(kwid_filter)]
                        df1["JAHR"] = pd.to_numeric(df1["JAHR"], errors="coerce")
                        df1.rename(columns={"ZENR": "PKTNR"}, inplace=True)

                        kw_frames.append(df1)
                        del df1

                    kw_out_path = os.path.join(
                        kw_out_dir,
                        f"KW_{os.path.basename(zip_file).replace('.zip', '.parquet')}"
                    )
                    kw_df = Evaluation._safe_concat(
                        kw_frames,
                        {
                            "KWID": "int32",
                            "JAHR": "int32",
                            "PKTNR": "int32",
                            "PINSTALL": "float32",
                            "EINSATZ": "float32",
                            "VARKOSTEN": "float32"
                        }
                    )
                    if kw_df is not None and len(kw_df):
                        kw_df.to_parquet(kw_out_path, compression=parquet_compression, engine=parquet_engine)
                        logger.info(f"⚡ KW aus {zip_file} → {kw_out_path} ({len(kw_df):,} Zeilen)")
                    del kw_frames, kw_df

        except Exception as e:
            logger.error(f"❌ Fehler beim Verarbeiten von {zip_file}: {e}")

        gc.collect()

    # -------------------------------------------------------------------------
    def generate_parquet_files(self, batch_size_years=8):
        """
        Liest ALLE ZIP-Dateien (a/b) über alle Jahre und erzeugt Parquet-Dateien (REG & KW).
        Optimiert:
        - Ein globaler ProcessPool mit dynamischen max_workers (CPU voll auslasten)
        - Zstd-Kompression
        - Pro ZIP schreiben (keine riesigen Sammel-DataFrames je Jahr)
        """
        years = list(range(self.start_year, self.end_year + 1))

        # Liste aller (zip_path, year)-Jobs bauen
        jobs = []
        for year in years:
            year_dir = os.path.join(self.input_folder_path, str(year))
            a_zip = os.path.join(year_dir, f"daoussi_Wetterjahr_a_{year}.zip")
            b_zip = os.path.join(year_dir, f"daoussi_Wetterjahr_b_{year}.zip")
            if os.path.exists(a_zip):
                jobs.append((a_zip, year))
            if os.path.exists(b_zip):
                jobs.append((b_zip, year))

        if not jobs:
            logger.warning("⚠️ Keine ZIP-Dateien gefunden. Prüfe input_folder_path/Jahre.")
            return

        total_start = time.time()
        max_workers = max(4, multiprocessing.cpu_count() - 1)  # 8C/16T → 15 Worker
        logger.info(f"🚀 Starte Parquet-Erstellung für {len(jobs)} ZIPs mit {max_workers} Prozessen ...")

        # Parallele Verarbeitung aller ZIPs
        with ProcessPoolExecutor(max_workers=max_workers) as exe:
            exe.map(
                self._process_zip,
                [p[0] for p in jobs],                        # zip_file
                [p[1] for p in jobs],                        # year
                [self.reg_pattern_template] * len(jobs),
                [self.kw_pattern_template] * len(jobs),
                [self.kwid_map] * len(jobs),
                [self.path_low_cut] * len(jobs),             # als Pfad übergeben (pro Subprozess laden)
                [self.results_path] * len(jobs),
                [self.parquet_engine] * len(jobs),
                [self.parquet_compression] * len(jobs),
            )

        total_elapsed = time.time() - total_start
        logger.info(f"⏰ Gesamtzeit Parquet-Erstellung: {timedelta(seconds=int(total_elapsed))}")

    # -------------------------------------------------------------------------
    def calculate_profitability(self, batch_size_years=4):
        """
        Berechnet die Profitabilität ausschließlich aus vorhandenen Parquet-Dateien.
        Optimiert:
        - schnelles Lesen (nur benötigte Spalten)
        - Index-Join statt Merge (bei großen Tabellen schneller)
        """
        years = list(range(self.start_year, self.end_year + 1))
        total_start = time.time()

        for i in range(0, len(years), batch_size_years):
            batch_years = years[i:i+batch_size_years]
            logger.info(f"📊 Starte Profitabilitätsberechnung für Jahre: {batch_years}")

            for year in batch_years:
                start_time = time.time()
                year_out_path = os.path.join(self.results_path, str(year))
                reg_dir = os.path.join(year_out_path, "reg")
                kw_dir  = os.path.join(year_out_path, "kw")
                profit_dir = os.path.join(year_out_path, "profitability")
                os.makedirs(profit_dir, exist_ok=True)

                # 🧾 Parquet-Dateien einsammeln
                reg_files = [os.path.join(reg_dir, f) for f in os.listdir(reg_dir) if f.endswith(".parquet")]
                kw_files  = [os.path.join(kw_dir,  f) for f in os.listdir(kw_dir)  if f.endswith(".parquet")]

                if not reg_files or not kw_files:
                    logger.warning(f"⚠️ Fehlende Parquet-Dateien für {year}: reg={len(reg_files)}, kw={len(kw_files)}")
                    continue

                # REG lesen (nur benötigte Spalten)
                reg_df = pd.concat(
                    (pd.read_parquet(f, columns=["REGID", "PKTNR", "JAHR", "FINAL_MARKTPREIS"]) for f in reg_files),
                    ignore_index=True
                ).astype({"REGID": "int32", "PKTNR": "int32", "JAHR": "int32", "FINAL_MARKTPREIS": "float32"},
                         copy=False)

                # KW lesen (nur benötigte Spalten)
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
                }, copy=False)

                # KWID → REGID Mapping hinzufügen
                kw_df = pd.merge(
                    kw_df,
                    self.kwid_region_map[["KWID", "REGID"]].astype({"KWID": "int32", "REGID": "int32"}, copy=False),
                    on="KWID",
                    how="inner"
                )

                # 🔗 Schneller Join: über Index statt Merge
                kw_df.set_index(["REGID", "PKTNR", "JAHR"], inplace=True)
                reg_df.set_index(["REGID", "PKTNR", "JAHR"], inplace=True)
                merged = kw_df.join(reg_df, how="inner")
                merged.reset_index(inplace=True)

                # 💰 Deckungsbeitrag
                merged["Deckungsbeitrag_hr"] = (merged["FINAL_MARKTPREIS"] + merged["VARKOSTEN"]) * merged["EINSATZ"]

                # Gruppierung pro JAHR und KWID
                agg = merged.groupby(["JAHR", "KWID"], as_index=False, observed=False).agg({
                    "PINSTALL": "mean",
                    "Deckungsbeitrag_hr": "sum"
                })

                # Profit pro kW (robust gegen PINSTALL=0)
                mask = agg["PINSTALL"] > 0
                agg["Annual_Profit_per_kw"] = 0.0
                agg.loc[mask, "Annual_Profit_per_kw"] = (
                    agg.loc[mask, "Deckungsbeitrag_hr"] / (agg.loc[mask, "PINSTALL"] * 1000)
                )

                agg = agg.sort_values(by=["JAHR", "Annual_Profit_per_kw"], ascending=[True, False]).reset_index(drop=True)
                agg = pd.merge(agg, self.kwid_region_map, on='KWID', how='left')
                agg['Annual_Profit_per_kw'] = agg['Annual_Profit_per_kw'].round(1)
                cols_order = [
                    "JAHR",
                    "KWID",
                    "Region",
                    "REGID",
                    "Technology",
                    "Tech_Abb",
                    "ShapeType",
                    "PINSTALL",
                    "Deckungsbeitrag_hr",
                    "Annual_Profit_per_kw"
                ]

                # nur Spalten behalten, die tatsächlich im DataFrame sind
                cols_order = [c for c in cols_order if c in agg.columns]
                agg = agg[cols_order]

                out_profit = os.path.join(profit_dir, f"kw_profitability_{year}.xlsx")
                agg.to_excel(out_profit, index=False)
                logger.info(f"✅ Profitabilität {year} → {out_profit} (KWIDs: {agg['KWID'].nunique()})")

                elapsed_time = time.time() - start_time
                logger.info(f"🕒 Berechnungszeit {year}: {timedelta(seconds=int(elapsed_time))}")

                # 🧹 Speicher freigeben
                del reg_df, kw_df, merged, agg
                gc.collect()

        total_elapsed = time.time() - total_start
        logger.info(f"⏰ Gesamtzeit Profitabilitätsberechnung: {timedelta(seconds=int(total_elapsed))}")
