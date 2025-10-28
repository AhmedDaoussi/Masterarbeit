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


# ----------------------------- Klasse Evaluation ------------------------------
class Evaluation:
    def __init__(self, config_path: str):
        """
        Konstruktor der Evaluation-Klasse.
        Lädt die Konfigurationsdatei und extrahiert alle benötigten Pfade, Jahre und KWID-Mappings.
        """
        # ---- Config laden ----
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

        # Pattern — kein year.format() mehr notwendig
        self.reg_pattern_template = r'daoussi_Wetterjahr_[ab]_\d{4}/SQLLoader/SQLLoader_RegResults_\d{4}_0_\d+\.dat'
        self.kw_pattern_template = r'daoussi_Wetterjahr_[ab]_\d{4}/SQLLoader/SQLLoader_KWResults_\d{4}_0_\d+\.dat'

        self.kwid_region_map = pd.read_excel(
            config["paths"]["kwid_region_map"],
            dtype={"KWID": int, "REGID": int}
        )
        self.export_yp = config['export_yearly_prices_to_excel']
    # -------------------------------------------------------------------------
    def _extract_kwid_mapping(self):
        """
        Extrahiert eine flache Liste aller KWIDs aus dem verschachtelten region_zone_mapping.
        """
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
        Hauptmethode — kombiniert:
        1) Berechnung stündlicher Marktpreise pro Region
        2) Extraktion KW-Erzeugungsdaten
        3) Profitabilitätsberechnung
        """
        years = list(range(self.start_year, self.end_year + 1))
        zip_year_pairs = [
            (f"{self.folder_path}/{year}/daoussi_Wetterjahr_{x}_{year}.zip", year)
            for year in years
            for x in ["a", "b"]
        ]

        low_cut_df = pd.read_excel(self.path_low_cut)
        results_reg, results_kw = [], []

        with ProcessPoolExecutor() as exe:
            for reg_res, kw_res in exe.map(
                self._process_zip,
                [p[0] for p in zip_year_pairs],                    # zip_file
                [p[1] for p in zip_year_pairs],                    # year
                [self.reg_pattern_template] * len(zip_year_pairs),
                [self.kw_pattern_template] * len(zip_year_pairs),
                [self.kwid_map] * len(zip_year_pairs),
                [low_cut_df] * len(zip_year_pairs),
            ):
                results_reg.append(reg_res)
                results_kw.append(kw_res)

        # ---------------- Preise aggregieren ----------------
        reg_df = pd.concat([x for x in results_reg if x is not None], ignore_index=True)
        for col in reg_df.columns:
            reg_df[col] = pd.to_numeric(reg_df[col], errors="coerce")
        reg_df = reg_df.sort_values(by=["REGID", "JAHR", "PKTNR"]).reset_index(drop=True)
        if self.export_yp =='yes':
            for year, group in reg_df.groupby("JAHR"):
                out_path = os.path.join(
                    self.folder_path,
                    f"{year}/kw_profitability/hourly_prices_for_year_{year}_wy_{self.start_year}.xlsx"
                )
                os.makedirs(os.path.dirname(out_path), exist_ok=True)
                group.to_excel(out_path, index=False)

        # ---------------- Profitabilität ----------------
        kw_df = pd.concat([x for x in results_kw if x is not None], ignore_index=True)
        for col in kw_df.columns:
            kw_df[col] = pd.to_numeric(kw_df[col], errors="coerce")
        kw_df = pd.merge(
            kw_df,
            self.kwid_region_map[["KWID", "REGID"]],
            on="KWID",
            how="left"
        )
        kw_df["REGID"] = pd.to_numeric(kw_df["REGID"], errors="coerce").astype("Int64")
        kw_df["PKTNR"] = pd.to_numeric(kw_df["PKTNR"], errors="coerce").astype("Int64")
        kw_df["JAHR"] = pd.to_numeric(kw_df["JAHR"], errors="coerce").astype("Int64")


        merged = pd.merge(kw_df, reg_df, on=["REGID", "PKTNR", "JAHR"], how="left")
        merged["Deckungsbeitrag_hr"] = (merged["FINAL_MARKTPREIS"] + merged["VARKOSTEN"]) * merged["EINSATZ"]

        result_list = []
        for (year, kwid), group in merged.groupby(["JAHR", "KWID"]):
            pinst = group["PINSTALL"].mean()
            if pinst and pinst > 0:
                profit = group["Deckungsbeitrag_hr"].sum() / (pinst * 1000)
            else:
                profit = 0
            result_list.append({
                "JAHR": year,
                "KWID": kwid,
                "Annual_Profit_per_kw": round(profit, 1)
            })

        final_df = pd.DataFrame(result_list)
        out_profit = os.path.join(
            self.folder_path,
            f"{year}/kw_profitability/kw_profitability_{year}.xlsx"
        )
        final_df.to_excel(out_profit, index=False)
        logger.info(f"💰 Profitabilität gespeichert unter: {out_profit}")

    # -------------------------------------------------------------------------
    @staticmethod
    def _process_zip(zip_file, year, reg_pattern_template, kw_pattern_template, kwid_filter: set, low_cut_df):
        """
        Liest aus einer einzelnen ZIP-Datei:
        - RegResults (Preise)
        - KWResults (Erzeugung)
        für alle Jahre (Pattern erkennt automatisch das Jahr).
        """
        reg_dataframes = []
        kw_dataframes = []

        if not os.path.exists(zip_file):
            logger.warning(f"⚠️ ZIP-Datei nicht gefunden: {zip_file}")
            return None, None

        try:
            with zipfile.ZipFile(zip_file, "r") as zf:
                file_list = zf.namelist()

                reg_pat = re.compile(reg_pattern_template)
                kw_pat = re.compile(kw_pattern_template)

                # ---------------- REG FILES ----------------
                reg_files = [f for f in file_list if reg_pat.match(f)]
                for rf in reg_files:
                    with zf.open(rf) as f:
                        df = pd.read_csv(f, delimiter=",", header=None)
                        df1 = df.iloc[10:].reset_index(drop=True)
                        df1 = pd.DataFrame([x.split(";") for x in df1[0]])
                        df2 = df1.iloc[:, :6].copy()
                        df2.columns = ['VARID', 'REGID', 'SIMID', 'JAHR', 'ZENR', 'MARKTPREIS']
                        df2['REGIONENMARKUP'] = df1.iloc[:, 7]
                        df2['STARTKOSTEN'] = df1.iloc[:, 53]

                        # Nur benötigte Spalten sofort behalten
                        df2 = df2[['REGID', 'JAHR', 'ZENR', 'MARKTPREIS', 'REGIONENMARKUP', 'STARTKOSTEN']]
                        # Typkonvertierungen
                        df2['ZENR'] = pd.to_numeric(df2['ZENR'], errors='coerce')
                        df2['JAHR'] = pd.to_numeric(df2['JAHR'], errors='coerce')
                        df2.rename(columns={'ZENR': 'PKTNR'}, inplace=True)

                        df2 = pd.merge(
                            df2,
                            low_cut_df[['JAHR', 'PKTNR', 'LOW_CUT_TERM']],
                            on=['JAHR', 'PKTNR'],
                            how='left'
                        )

                        df2['FINAL_MARKTPREIS'] = (
                                df2['MARKTPREIS'].astype(float) +
                                df2['REGIONENMARKUP'].astype(float) +
                                df2['STARTKOSTEN'].astype(float)
                        ) * df2['LOW_CUT_TERM'].astype(float)
                        reg_dataframes.append(df2[['REGID', 'JAHR', 'PKTNR', 'FINAL_MARKTPREIS']])

                # ---------------- KW FILES ----------------
                kw_files = [f for f in file_list if kw_pat.match(f)]
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

                        # Schon beim Generator unnötige Spalten kappen
                        df1 = df1[["KWID", "JAHR", "ZENR", "PINSTALL", "EINSATZ", "VARKOSTEN"]]

                        # KWIDs, die uns nicht interessieren, sofort wegfiltern
                        df1["KWID"] = pd.to_numeric(df1["KWID"], errors="coerce")
                        df1 = df1[df1["KWID"].isin(kwid_filter)]

                        df1["JAHR"] = pd.to_numeric(df1["JAHR"], errors="coerce")
                        df1.rename(columns={"ZENR": "PKTNR"}, inplace=True)


                        kw_dataframes.append(df1)

        except Exception as e:
            logger.error(f"❌ Fehler beim Verarbeiten von {zip_file}: {e}")
            return None, None

        reg_df = pd.concat(reg_dataframes, ignore_index=True) if reg_dataframes else None
        kw_df = pd.concat(kw_dataframes, ignore_index=True) if kw_dataframes else None
        return reg_df, kw_df
