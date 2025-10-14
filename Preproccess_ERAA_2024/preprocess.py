import re
import yaml
import shutil
import pandas as pd
from pathlib import Path
from collections import defaultdict
import numpy as np
import bisect


# 📄 Regex für Projekttyp 2024 (CapacityFactors)
FILENAME_RE_2024 = re.compile(
    r'^(?P<zone>[A-Z0-9]+)_CapacityFactors_(?P<tech>LFSolarPV|Wind_Onshore|Wind_Offshore|Solar PV farm|CSP_noStorage|CSP_noStorage_0h_dispatched)_(?P<year>\d{4})$'
)

# Technologie-Abkürzungen für Output-Dateien
TECH_ABBREVIATIONS = {
    "LFSolarPV": "pv",
    "Solar PV farm": "pv",  # 🇮🇹 Italien
    "Wind_Onshore": "wind_on",
    "Wind_Offshore": "wind_off",
    "CSP_noStorage": "csp",
    "CSP_noStorage_0h_dispatched": "csp"  # 🇪🇸 Spanien
}


class Preprocess:
    def __init__(self, config_path: str = "config.yaml"):
        self.config = self._load_config(config_path)
        self.input_path = Path(self.config["pecd_paths"]["2024"])
        self.target_year = str(self.config["target_year"])
        self.region_mapping = self.config["region_zone_mapping"]
        self.weather_years = self.config["weather_years"]["list"]  # 📌 WS1–WS36 aus Config
        self.chosen_dir = self.input_path.parent / "chosen_pecd_files"
        self.unavailability_dir = self.input_path.parent / "unavailability_files"

    def _load_config(self, path: str):
        with open(path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f)

    def _parse_filename(self, path: Path):
        m = FILENAME_RE_2024.match(path.stem)
        if not m:
            return None
        return m.group("tech"), m.group("year"), m.group("zone")

    def get_valid_zone_tech_pairs(self, verbose=True):
        valid_pairs = set()
        for _, tech_dict in self.region_mapping.items():
            for tech, tech_data in tech_dict.items():
                if "source_zones" not in tech_data:
                    continue
                if tech in ("Wind_Onshore", "Wind_Offshore"):
                    if tech_data.get("kwid_shape_a") is None:
                        continue
                elif tech in ("LFSolarPV", "Solar PV farm", "CSP_noStorage", "CSP_noStorage_0h_dispatched"):
                    if tech_data.get("kwid") is None:
                        continue
                for zone in tech_data["source_zones"]:
                    valid_pairs.add((zone, tech))
        if verbose:
            print(f"🧮 Total number of valid (zone, tech) pairs: {len(valid_pairs)}")
        return valid_pairs

    def filter_relevant_files(self):
        valid_pairs = self.get_valid_zone_tech_pairs(verbose=True)
        self.chosen_dir.mkdir(exist_ok=True)
        matched_pairs = set()
        count = 0

        for file in self.input_path.iterdir():
            if file.suffix.lower() != ".csv":
                continue
            parsed = self._parse_filename(file)
            if not parsed:
                continue
            tech, year, zone = parsed
            pair = (zone, tech)
            if year == self.target_year and pair in valid_pairs:
                shutil.copy2(file, self.chosen_dir / file.name)
                matched_pairs.add(pair)
                count += 1

        missing_pairs = valid_pairs - matched_pairs
        print(f"✅ {count} relevante Dateien kopiert nach: {self.chosen_dir}")
        print(f"❌ {len(missing_pairs)} gültige Paare konnten keiner Datei zugeordnet werden")
        if missing_pairs:
            missing_by_tech = defaultdict(list)
            for zone, tech in missing_pairs:
                missing_by_tech[tech].append(zone)
            print("📄 Fehlende Paare gruppiert nach Technologie:")
            for tech, zones in missing_by_tech.items():
                print(f"   - {tech}: {', '.join(sorted(zones))}")

    def process_unavailability_files(self):
        self.unavailability_dir.mkdir(exist_ok=True)
        processed_count = 0
        failed_files = []

        for file in self.chosen_dir.iterdir():
            if file.suffix.lower() != ".csv":
                continue
            parsed = self._parse_filename(file)
            if not parsed:
                failed_files.append(file.name)
                continue

            tech, year, zone = parsed
            tech_abbr = TECH_ABBREVIATIONS.get(tech, tech)
            parts = [tech_abbr, year, zone]
            if tech in ("Wind_Onshore", "Wind_Offshore"):
                parts.append("shape_a")
            new_name = "_".join(parts) + ".csv"
            out_path = self.unavailability_dir / new_name

            try:
                df = pd.read_csv(file, header=10)
                df.columns = df.columns.str.strip()
                df.reset_index(drop=True, inplace=True)
                df.iloc[:, 2:] = df.iloc[:, 2:].apply(
                    lambda x: 1 - pd.to_numeric(x, errors="coerce")
                ).round(4)
                df.to_csv(out_path, index=False, float_format="%.4f")
                processed_count += 1
            except Exception as e:
                print(f"❌ Fehler bei {file.name}: {e}")
                failed_files.append(file.name)

        print(f"📊 {processed_count} Dateien verarbeitet → {self.unavailability_dir}")
        if failed_files:
            print("❌ Fehlerhafte Dateien:")
            for fname in failed_files:
                print(f"   - {fname}")

    def generate_shape_b_files(self):
        """
        Generiert Shape-B-Dateien basierend auf Shape-A-Dateien.
        - Windtechnologien: Transformation Shape A -> Shape B
        - PV & CSP: Kopieren unverändert
        - Berücksichtigt Weather Years als WS1..WS36 (keine Umwandlung in Zahlen nötig)
        - helping_files Pfad über Projektbasis
        - Robuste Behandlung von nicht-numerischen Werten
        """
        import time
        from pathlib import Path
        import shutil

        start_all = time.time()

        # 📂 Verzeichnisse
        shape_a_dir = self.input_path.parent / "unavailability_files_plus_special"
        shape_b_dir = self.input_path.parent / "shape_b_files"
        shape_b_dir.mkdir(exist_ok=True)

        # 📁 helping_files liegt direkt im Projektverzeichnis
        helping_dir = Path(__file__).resolve().parent / "helping_files"
        offshore_dic_path = helping_dir / "shpab_offshore.xlsx"
        onshore_dic_path = helping_dir / "shpab_onshore.xlsx"
        kwid_mapping_path = helping_dir / "kwid_reg_mapping.xlsx"

        # 🧭 Mapping-Dateien laden (erste Zeile überspringen & numerisch umwandeln)
        offshore = pd.read_excel(offshore_dic_path, header=None).iloc[1:].copy()
        onshore = pd.read_excel(onshore_dic_path, header=None).iloc[1:].copy()

        offshore[0] = pd.to_numeric(offshore[0].astype(str).str.replace(',', '.'), errors='coerce')
        offshore[1] = pd.to_numeric(offshore[1].astype(str).str.replace(',', '.'), errors='coerce')
        onshore[0] = pd.to_numeric(onshore[0].astype(str).str.replace(',', '.'), errors='coerce')
        onshore[1] = pd.to_numeric(onshore[1].astype(str).str.replace(',', '.'), errors='coerce')

        # 🧮 Hilfsfunktion für eindeutige & sortierte Stützstellen
        def extract_unique_mapping(df):
            a_vals = df[1].to_numpy()
            b_vals = df[0].to_numpy()
            unique_a = []
            unique_b = []
            prev_a = None
            for a_val, b_val in zip(a_vals, b_vals):
                if prev_a is None or a_val < prev_a:
                    unique_a.append(a_val)
                    unique_b.append(b_val)
                    prev_a = a_val
            if len(unique_a) > 1 and unique_a[0] > unique_a[-1]:
                unique_a = unique_a[::-1]
                unique_b = unique_b[::-1]
            return np.array(unique_b), np.array(unique_a)

        offshore_b, offshore_a = extract_unique_mapping(offshore)
        onshore_b, onshore_a = extract_unique_mapping(onshore)

        mapping_dict = {
            "wind_off": (offshore_b, offshore_a),
            "wind_on": (onshore_b, onshore_a)
        }

        # 🧾 KWID-Mapping laden
        kwid_map = pd.read_excel(kwid_mapping_path)
        kwid_map.columns = [c.strip().lower() for c in kwid_map.columns]

        required_cols = ['region', 'technology', 'kwid', 'shapetype', 'regid', 'tech_abb']
        for col in required_cols:
            if col not in kwid_map.columns:
                raise ValueError(f"❌ Erwartete Spalte '{col}' fehlt in der Mapping-Datei.")

        # Wind Shape A Zeilen für Transformation
        shape_a_rows = kwid_map[
            kwid_map['shapetype'].str.contains('a', case=False, na=False) &
            kwid_map['tech_abb'].isin(['wind_on', 'wind_off'])
            ]

        year = self.config.get('target_year')

        # 📋 Vorprüfung auf fehlende Shape-A-Dateien
        print("\n📋 Vorprüfung auf Shape-A-Dateien (Wind):")
        missing_before = []
        for _, row in shape_a_rows.iterrows():
            tech = row['tech_abb']
            region = row['region']
            shape_a_file = shape_a_dir / f"{tech}_{year}_{region}_shape_a.csv"
            if not shape_a_file.exists():
                missing_before.append(shape_a_file.name)
        if missing_before:
            print(f"⚠️ {len(missing_before)} fehlende Shape-A-Dateien:")
            for f in missing_before:
                print(f"  - {f}")
        else:
            print("✅ Alle benötigten Shape-A-Dateien vorhanden.")

        generated_count = 0
        copied_count = 0
        failed_pairs = []

        # 🌀 Hauptloop — Wind Transformation
        for _, row in shape_a_rows.drop_duplicates(subset=['region', 'tech_abb']).iterrows():
            tech = row['tech_abb']
            region = row['region']
            shape_a_file = shape_a_dir / f"{tech}_{year}_{region}_shape_a.csv"
            shape_b_file = shape_b_dir / f"{tech}_{year}_{region}_shape_b.csv"

            if not shape_a_file.exists():
                failed_pairs.append((region, tech))
                continue

            try:
                df_raw = pd.read_csv(shape_a_file, header=None)
                header = df_raw.iloc[0].tolist()
                df_data = df_raw.iloc[1:].copy()

                # 📌 Erste 2 Spalten unverändert übernehmen
                df_first_columns = df_data.iloc[:, :2].copy()
                # 🧮 Ab Spalte 3 Werte numerisch konvertieren
                df_numeric = df_data.iloc[:, 2:].apply(pd.to_numeric, errors="coerce")

                shape_b_values, shape_a_values = mapping_dict[tech]
                df_transformed = df_numeric.copy()

                for col in df_transformed.columns:
                    col_values = df_transformed[col].to_numpy()
                    transformed = np.array([
                        self._find_nearest_b(val, shape_a_values, shape_b_values)
                        if not np.isnan(val) else np.nan
                        for val in col_values
                    ])
                    df_transformed[col] = transformed

                df_result = pd.concat([df_first_columns, df_transformed], axis=1)
                df_result.loc[-1] = header
                df_result.index = df_result.index + 1
                df_result = df_result.sort_index()

                # 📌 Header WS1..WS36 unverändert beibehalten
                cleaned_header = [str(val).strip() for val in header]
                df_result.iloc[0] = cleaned_header

                df_result.to_csv(shape_b_file, index=False, header=False)
                generated_count += 1
                print(f"✅ {shape_b_file.name} erzeugt")

            except Exception as e:
                print(f"❌ Fehler bei {shape_a_file.name}: {e}")
                failed_pairs.append((region, tech))

        # 🪄 PV / CSP Dateien einfach kopieren (unverändert)
        for file in shape_a_dir.glob("*.csv"):
            if "wind_on" in file.name or "wind_off" in file.name:
                continue  # Wind wurde oben schon verarbeitet
            target_file = shape_b_dir / file.name
            if file != target_file:
                shutil.copy2(file, target_file)
            copied_count += 1
            print(f"📋 Nicht-Wind Datei kopiert: {file.name}")

        # 📊 Zusammenfassung
        elapsed_total = time.time() - start_all
        print("\n📊 Shape-B-Zusammenfassung:")
        print(f"✅ {generated_count} Wind-Dateien transformiert")
        print(f"📋 {copied_count} Nicht-Wind-Dateien kopiert")
        print(f"⏳ Dauer: {self._format_time(elapsed_total)}")
        if failed_pairs:
            print(f"❌ {len(failed_pairs)} fehlgeschlagen:")
            for region, tech in failed_pairs:
                print(f"  - {region} / {tech}")

    def _find_nearest_b(self, value, a_values, b_values):
        """Robuste Version — wandelt Strings in Float um und handhabt NaN sicher."""
        try:
            value = float(value)
        except (ValueError, TypeError):
            return np.nan

        if np.isnan(value):
            return np.nan
        if value <= a_values[0]:
            return b_values[0]
        if value >= a_values[-1]:
            return b_values[-1]

        pos = bisect.bisect_left(a_values, value)
        before = a_values[pos - 1]
        after = a_values[pos]
        return b_values[pos] if after - value < value - before else b_values[pos - 1]

    def _format_time(self, seconds):
        """Formatiert Sekunden in ein lesbares Format (z. B. 0h 5m 32s)."""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        return f"{hours}h {minutes}m {secs}s"

    def calculate_special_region_files(self):
        """
        Erstellt aggregierte Unavailability-CSV-Dateien für Spezialregionen
        (mit mehreren Quellzonen & Gewichten) und kopiert Single-Zone-Dateien unverändert
        in den Zielordner.

        Unterstützt 2024-Technologien:
        - LFSolarPV
        - Solar PV farm
        - Wind_Onshore
        - Wind_Offshore
        - CSP_noStorage
        - CSP_noStorage_0h_dispatched
        """
        import shutil

        special_out_dir = self.input_path.parent / "unavailability_files_plus_special"
        special_out_dir.mkdir(exist_ok=True)

        processed_special = 0
        processed_copied = 0
        failed = []

        print("\n🧮 Starte Berechnung der Spezialregionen...")
        print(f"📂 Ausgabeordner: {special_out_dir}\n")

        for region, tech_dict in self.region_mapping.items():
            for tech, tech_data in tech_dict.items():
                # 🪄 Windtechnologien ohne shape_a überspringen
                if tech in ("Wind_Onshore", "Wind_Offshore") and tech_data.get("kwid_shape_a") is None:
                    continue

                # Technologie-Abkürzung ermitteln
                tech_abbr = TECH_ABBREVIATIONS.get(tech, tech)
                parts = [tech_abbr, self.target_year, region]
                if tech in ("Wind_Onshore", "Wind_Offshore"):
                    parts.append("shape_a")
                out_name = "_".join(parts) + ".csv"
                out_path = special_out_dir / out_name

                # 🎯 Spezialregion (mehrere Zonen)
                if "zones" in tech_data and len(tech_data["zones"]) > 1:
                    try:
                        combined_df = None
                        used_files = []

                        for zone, values in tech_data["zones"].items():
                            weight = float(values["weight"])
                            file_name_parts = [tech_abbr, self.target_year, zone]
                            if tech in ("Wind_Onshore", "Wind_Offshore"):
                                file_name_parts.append("shape_a")
                            file_name = "_".join(file_name_parts) + ".csv"
                            file_path = self.unavailability_dir / file_name

                            if not file_path.exists():
                                print(f"⚠️ Fehlende Quelldatei für Spezialregion: {file_name}")
                                continue

                            df = pd.read_csv(file_path)
                            used_files.append((zone, weight, file_name))

                            # Struktur übernehmen
                            if combined_df is None:
                                combined_df = df.copy()
                                combined_df.iloc[:, 2:] = 0

                            # Gewichtet aufaddieren (ab Spalte 3)
                            combined_df.iloc[:, 2:] += df.iloc[:, 2:].apply(
                                pd.to_numeric, errors="coerce"
                            ) * weight

                        if combined_df is None:
                            raise ValueError("Keine gültigen Quelldateien gefunden")

                        combined_df.iloc[:, 2:] = combined_df.iloc[:, 2:].round(4)
                        combined_df.to_csv(out_path, index=False, float_format="%.4f")
                        processed_special += 1

                        print(f"✅ Spezialdatei erzeugt: {out_name}")
                        for z, w, fname in used_files:
                            print(f"   └─ verwendet {fname} (Zone {z}, Gewicht {w})")

                    except Exception as e:
                        print(f"❌ Fehler bei Spezialregion {region}-{tech}: {e}")
                        failed.append(f"{region}-{tech}")

                # 📋 Single-Zone Region → Datei einfach kopieren
                elif "source_zones" in tech_data and len(tech_data["source_zones"]) == 1:
                    try:
                        zone = tech_data["source_zones"][0]
                        file_name_parts = [tech_abbr, self.target_year, zone]
                        if tech in ("Wind_Onshore", "Wind_Offshore"):
                            file_name_parts.append("shape_a")
                        file_name = "_".join(file_name_parts) + ".csv"

                        src_file = self.unavailability_dir / file_name
                        if not src_file.exists():
                            print(f"⚠️ Fehlende Single-Zone-Datei: {file_name}")
                            failed.append(f"{region}-{tech}")
                            continue

                        shutil.copy2(src_file, out_path)
                        processed_copied += 1
                        print(f"📋 Datei kopiert: {file_name} → {out_name}")

                    except Exception as e:
                        print(f"❌ Fehler beim Kopieren für {region}-{tech}: {e}")
                        failed.append(f"{region}-{tech}")

        # 📝 Zusammenfassung
        print("\n📊 Spezialregionen Zusammenfassung:")
        print(f"   ✅ {processed_special} Spezialdateien erstellt")
        print(f"   📋 {processed_copied} Single-Zone-Dateien kopiert")
        if failed:
            print(f"   ❌ {len(failed)} fehlgeschlagen:")
            for f in failed:
                print(f"      - {f}")

    def generate_weather_year_files(self):
        """
        Erzeugt für jedes Wetterjahr (WS1–WS36) eine konsolidierte CSV-Datei.
        - Weather-Year-Labels werden aus dem Header (ab Spalte 3) gelesen
        - Dateien können aus Shape-A oder Shape-B stammen (Wind, PV, CSP)
        - helping_files Pfad wird relativ zum Projekt aufgelöst
        """
        import logging
        from pathlib import Path

        # 📂 Pfade
        shape_b_dir = self.input_path.parent / "shape_b_files"
        shape_a_dir = self.input_path.parent / "unavailability_files_plus_special"
        helping_dir = Path(__file__).resolve().parent / "helping_files"
        mapping_file = helping_dir / "kwid_reg_mapping.xlsx"
        output_base = self.input_path.parent / "Weather_Year_Files"
        output_base.mkdir(exist_ok=True)

        # 📅 Wetterjahre aus Config
        weather_cfg = self.config["weather_years"]
        if "count" in weather_cfg:
            weather_years = [f"WS{i}" for i in range(1, weather_cfg["count"] + 1)]
        elif "list" in weather_cfg:
            weather_years = [str(y) for y in weather_cfg["list"]]
        else:
            raise ValueError("❌ Kein gültiger Eintrag für weather_years in config.yaml gefunden.")

        if not weather_years:
            raise ValueError("❌ Keine Wetterjahre gefunden (erwarte WS1…WS36).")

        # 🧭 Mapping laden
        kwid_map = pd.read_excel(mapping_file)
        kwid_map.columns = [c.strip().lower() for c in kwid_map.columns]
        required_cols = ['kwid', 'region', 'tech_abb', 'shapetype']
        for col in required_cols:
            if col not in kwid_map.columns:
                raise ValueError(f"❌ Spalte '{col}' fehlt in der Mapping-Datei {mapping_file}")

        logging.info(f"✅ KWID Mapping geladen: {len(kwid_map)} Einträge")

        total_added = 0
        missing_files = []
        missing_year_cols = []
        successful_years = []
        failed_years = []

        # 🌀 Hauptloop über Wetterjahre (WS1 ... WS36)
        for wy in weather_years:
            result_df = pd.DataFrame(columns=['VARID', 'KWID', 'PKTNR', 'REVNV', 'RID'])
            logging.info(f"🌦️ Verarbeitung Wetterjahr {wy}")

            for _, row in kwid_map.iterrows():
                kwid = row['kwid']
                tech = row['tech_abb']
                region = row['region']
                target_year = str(self.target_year)

                # 🧭 shapetype prüfen
                if pd.isna(row['shapetype']):
                    shapetype = None
                else:
                    shapetype_str = str(row['shapetype']).strip().lower()
                    shapetype = shapetype_str if shapetype_str not in ("", "nan") else None

                # 📄 Dateiname bauen
                if shapetype is None:
                    filename = f"{tech}_{target_year}_{region}.csv"
                else:
                    filename = f"{tech}_{target_year}_{region}_{shapetype}.csv"

                # 📁 Pfad abhängig vom shapetype
                if shapetype == "b":
                    shape_dir = shape_b_dir
                elif shapetype == "a":
                    shape_dir = shape_a_dir
                else:
                    shape_dir = shape_b_dir if (shape_b_dir / filename).exists() else shape_a_dir

                shape_file = shape_dir / filename

                if not shape_file.exists():
                    missing_files.append((kwid, filename))
                    logging.warning(f"❌ Datei fehlt: {filename}")
                    continue

                # 📥 Header-Zeile einlesen
                try:
                    header_row = pd.read_csv(shape_file, nrows=1, header=None).iloc[0].tolist()
                except Exception as e:
                    logging.error(f"❌ Fehler beim Lesen des Headers von {filename}: {e}")
                    continue

                # 📅 Headerlabels (WS1..WS36)
                header_years = [str(h).strip() for h in header_row[2:]]

                if wy not in header_years:
                    missing_year_cols.append((kwid, filename, wy))
                    logging.warning(f"⚠️ Wetterjahr {wy} nicht in Datei {filename}")
                    continue

                # Index der Spalte mit dem Jahr ermitteln (+2, weil ab Spalte 3)
                year_index = header_years.index(wy) + 2
                usecols = [0, 1, year_index]

                # 📥 Relevante Spalten laden
                try:
                    df = pd.read_csv(shape_file, usecols=usecols, skiprows=[0], header=None)
                except Exception as e:
                    logging.error(f"❌ Fehler beim Laden von {filename}: {e}")
                    continue

                values = pd.to_numeric(df.iloc[:, 2], errors='coerce')
                hour_count = len(values)

                temp_df = pd.DataFrame({
                    'VARID': [1003] * hour_count,
                    'KWID': [kwid] * hour_count,
                    'PKTNR': range(1, hour_count + 1),
                    'REVNV': values.round(4),
                    'RID': [''] * hour_count
                })

                result_df = pd.concat([result_df, temp_df], ignore_index=True)
                total_added += 1

            # 📤 Wetterjahr-Datei speichern oder Fehlschlag protokollieren
            if not result_df.empty:
                year_dir = output_base / wy
                year_dir.mkdir(exist_ok=True)
                output_file = year_dir / f"WeatherYear_{wy}.csv"
                result_df.to_csv(output_file, index=False)
                logging.info(f"✅ Wetterjahr {wy} erfolgreich erstellt: {output_file}")
                successful_years.append(wy)
            else:
                logging.warning(f"⚠️ Wetterjahr {wy} konnte nicht erzeugt werden (keine Daten)")
                failed_years.append(wy)

        # 📝 Zusammenfassung
        print("\n📊 Zusammenfassung Wetterjahres-Erzeugung (2024):")
        print(f"   📁 {total_added} KWIDs erfolgreich verarbeitet")

        if successful_years:
            print(f"   ✅ Erfolgreich erzeugte Wetterjahre: {', '.join(map(str, successful_years))}")
        if failed_years:
            print(f"   ❌ Nicht erzeugte Wetterjahre: {', '.join(map(str, failed_years))}")
        else:
            print("   🎯 Alle Wetterjahre wurden erfolgreich erzeugt.")

        if missing_files:
            print(f"   ⚠️ {len(missing_files)} fehlende Dateien:")
            for kwid, fname in missing_files:
                print(f"      - KWID {kwid}: {fname}")

        if missing_year_cols:
            print(f"   ⚠️ {len(missing_year_cols)} Dateien enthalten das Wetterjahr nicht:")
            for kwid, fname, yr in missing_year_cols:
                print(f"      - KWID {kwid}: {fname} (Wetterjahr {yr} fehlt)")

    def run_full_pipeline(self):
        self.filter_relevant_files()
        self.process_unavailability_files()
        self.generate_shape_b_files()
        self.generate_weather_year_files()
