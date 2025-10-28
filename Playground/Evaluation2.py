import os
import re
import yaml
import zipfile
import logging
import pandas as pd
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
        Lädt Config und initialisiert Pfade, Mappings & Jahre.
        Liest low_cut.xlsx einmalig ein.
        """
        # ----------------- Konfiguration laden -----------------
        with open(config_path, "r", encoding="utf-8") as f:
            config = yaml.safe_load(f)

        # Pfade
        self.folder_path = config["paths"]["folder_path"]
        self.path_low_cut = config["paths"]["low_cut"]

        # Jahre
        self.start_year = config["years"]["start_year"]
        self.end_year = config["years"]["end_year"]

        # Mappings
        self.tech_to_abbr = config["TECH_TO_ABBR"]
        self.region_zone_mapping = config["region_zone_mapping"]

        # KWID Mapping extrahieren
        self.kwid_map = self._extract_kwid_mapping()
        logger.info(f"✅ {len(self.kwid_map)} KWIDs aus Config geladen ({len(self.region_zone_mapping)} Regionen).")

        # Pattern-Templates (Jahr wird dynamisch erkannt)
        self.reg_pattern_template = r'daoussi_Wetterjahr_[ab]_\\d{4}/SQLLoader/SQLLoader_RegResults_\\d{4}_0_\\d+\.dat'
        self.kw_pattern_template = r'daoussi_Wetterjahr_[ab]_\\d{4}/SQLLoader/SQLLoader_KWResults_\\d{4}_0_\\d+\.dat'

        # low_cut.xlsx einmalig laden
        self.low_cut_df = pd.read_excel(
            self.path_low_cut,
            dtype={'JAHR': int, 'PKTNR': int, 'LOW_CUT_TERM': float}
        )
        logger.info(f"📊 low_cut.xlsx geladen — {len(self.low_cut_df):,} Zeilen")

    # -------------------------------------------------------------------------
    def _extract_kwid_mapping(self):
        """Extrahiert alle KWIDs aus region_zone_mapping."""
        kwids = set()
        for region, techs in self.region_zone_mapping.items():
            for tech, info in techs.items():
                if "kwid_shape_a" in info and info["kwid_shape_a"] is not None:
                    kwids.add(info["kwid_shape_a"])
                if "kwid_shape_b" in info and info["kwid_shape_b"] is not None:
                    kwids.add(info["kwid_shape_b"])
                if "kwid" in info and info["kwid"] is not None:
                    kwids.add(info["kwid"])
        return kwids

    # -------------------------------------------------------------------------
    def compute_prices_and_profitability(self):
        """
        Hauptmethode:
        - Wetterjahre in 2er-Batches parallel verarbeiten (a/b Varianten pro Jahr)
        - Reg- und KW-Daten RAM-effizient einlesen (Generatoren)
        - Preise und Profitabilität berechnen
        - Ergebnisse speichern
        """
        years = list(range(self.start_year, self.end_year + 1))

        # ZIP-Dateien nach Jahren und Varianten erstellen
        zip_year_pairs = [
            (f"{self.folder_path}/daoussi_Wetterjahr_{x}_{year}.zip", year)
            for year in years
            for x in ["a", "b"]
        ]

        # Jahre in 2er-Batches aufteilen
        batches = [years[i:i + 2] for i in range(0, len(years), 2)]

        for batch in batches:
            logger.info(f"🚀 Starte Verarbeitung für Jahre: {batch}")
            batch_zip_pairs = [
                (f"{self.folder_path}/daoussi_Wetterjahr_{x}_{year}.zip", year)
                for year in batch
                for x in ["a", "b"]
            ]

            results_reg, results_kw = [], []

            # max_workers = 4 (2 Jahre × a/b)
            with ProcessPoolExecutor(max_workers=len(batch_zip_pairs)) as exe:
                for reg_res, kw_res in exe.map(
                    self._process_zip,
                    [p[0] for p in batch_zip_pairs],
                    [p[1] for p in batch_zip_pairs],
                    [self.reg_pattern_template] * len(batch_zip_pairs),
                    [self.kw_pattern_template] * len(batch_zip_pairs),
                    [self.kwid_map] * len(batch_zip_pairs),
                    [self.low_cut_df] * len(batch_zip_pairs),
                ):
                    if reg_res is not None:
                        results_reg.append(reg_res)
                    if kw_res is not None:
                        results_kw.append(kw_res)

            # ---------------- Preise aggregieren ----------------
            reg_df = pd.concat(results_reg, ignore_index=True)
            for col in reg_df.columns:
                reg_df[col] = pd.to_numeric(reg_df[col], errors="coerce")

            reg_df = reg_df.astype({"FINAL_MARKTPREIS": "float32"})
            reg_df = reg_df.sort_values(by=["REGID", "JAHR", "PKTNR"]).reset_index(drop=True)

            # Speichere Preise je Jahr
            for year, group in reg_df.groupby("JAHR"):
                out_path = os.path.join(
                    self.folder_path,
                    f"{year}/kw_profitability/hourly_prices_for_year_{year}_wy_{self.start_year}.xlsx"
                )
                os.makedirs(os.path.dirname(out_path), exist_ok=True)
                group.to_excel(out_path, index=False)

            # ---------------- Profitabilität ----------------
            kw_df = pd.concat(results_kw, ignore_index=True)
            for col in kw_df.columns:
                kw_df[col] = pd.to_numeric(kw_df[col], errors="coerce")

            merged = pd.merge(kw_df, reg_df, on=["REGID", "PKTNR", "JAHR"], how="left")
            merged["Deckungsbeitrag_hr"] = (
                (merged["FINAL_MARKTPREIS"] + merged["VARKOSTEN"]) * merged["EINSATZ"]
            ).astype("float32")

            # Aggregation nach KWID und Jahr
            result_list = []
            for (year, kwid), group in merged.groupby(["JAHR", "KWID"]):
                pinst = group["PINSTALL"].mean()
                profit = group["Deckungsbeitrag_hr"].sum() / (pinst * 1000) if pinst and pinst > 0 else 0
                result_list.append({
                    "JAHR": year,
                    "KWID": kwid,
                    "Annual_Profit_per_kw": round(profit, 1)
                })

            final_df = pd.DataFrame(result_list)
            for year in batch:
                out_profit = os.path.join(
                    self.folder_path,
                    f"{year}/kw_profitability/kw_profitability_{year}.xlsx"
                )
                os.makedirs(os.path.dirname(out_profit), exist_ok=True)
                final_df[final_df["JAHR"] == year].to_excel(out_profit, index=False)
                logger.info(f"💰 Profitabilität gespeichert unter: {out_profit}")

    # -------------------------------------------------------------------------
    @staticmethod
    def _reg_generator(file_list, zf):
        """Liefert vorbereitete REG-DataFrames einzeln (Generator, RAM-effizient)."""
        for rf in file_list:
            with zf.open(rf) as f:
                df = pd.read_csv(f, delimiter=",", header=None)
                df1 = df.iloc[10:].reset_index(drop=True)
                df1 = pd.DataFrame([x.split(";") for x in df1[0]])
                df2 = df1.iloc[:, :6].copy()
                df2.columns = ['VARID', 'REGID', 'SIMID', 'JAHR', 'ZENR', 'MARKTPREIS']
                df2['REGIONENMARKUP'] = df1.iloc[:, 7]
                df2['STARTKOSTEN'] = df1.iloc[:, 53]
                df2['ZENR'] = pd.to_numeric(df2['ZENR'], errors='coerce')
                df2['JAHR'] = pd.to_numeric(df2['JAHR'], errors='coerce')
                df2.rename(columns={'ZENR': 'PKTNR'}, inplace=True)
                yield df2

    @staticmethod
    def _kw_generator(file_list, zf):
        """Liefert vorbereitete KW-DataFrames einzeln (Generator, RAM-effizient)."""
        for kf in file_list:
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
                df1["JAHR"] = pd.to_numeric(df1["JAHR"], errors="coerce")
                df1.rename(columns={"ZENR": "PKTNR"}, inplace=True)
                yield df1

    # -------------------------------------------------------------------------
    @staticmethod
    def _process_zip(zip_file, year, reg_pattern_template, kw_pattern_template, kwid_filter: set, low_cut_df):
        """
        Verarbeitung einer einzelnen ZIP-Datei.
        Nutzt Generatoren → nur eine Datei gleichzeitig im Speicher.
        """
        if not os.path.exists(zip_file):
            logger.warning(f"⚠️ ZIP-Datei nicht gefunden: {zip_file}")
            return None, None

        try:
            with zipfile.ZipFile(zip_file, "r") as zf:
                file_list = zf.namelist()
                reg_pat = re.compile(reg_pattern_template)
                kw_pat = re.compile(kw_pattern_template)

                reg_files = [f for f in file_list if reg_pat.match(f)]
                kw_files = [f for f in file_list if kw_pat.match(f)]

                reg_df = None
                kw_df = None

                # --- REG ---
                if reg_files:
                    reg_df = pd.concat(Evaluation._reg_generator(reg_files, zf), ignore_index=True)
                    reg_df = pd.merge(
                        reg_df,
                        low_cut_df[['JAHR', 'PKTNR', 'LOW_CUT_TERM']],
                        on=['JAHR', 'PKTNR'],
                        how='left'
                    )
                    reg_df['FINAL_MARKTPREIS'] = (
                        reg_df['MARKTPREIS'].astype(float) +
                        reg_df['REGIONENMARKUP'].astype(float) +
                        reg_df['STARTKOSTEN'].astype(float)
                    ) * reg_df['LOW_CUT_TERM'].astype(float)
                    reg_df = reg_df[['REGID', 'JAHR', 'PKTNR', 'FINAL_MARKTPREIS']]

                # --- KW ---
                print('alle reg files wurden eingelesen')
                if kw_files:
                    kw_df = pd.concat(Evaluation._kw_generator(kw_files, zf), ignore_index=True)
                    print('alle kw files wurden eingelesen')
                    kw_df = kw_df[kw_df["KWID"].isin(kwid_filter)]

                return reg_df, kw_df

        except Exception as e:
            logger.error(f"❌ Fehler beim Verarbeiten von {zip_file}: {e}")
            return None, None
