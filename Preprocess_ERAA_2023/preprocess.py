import re
import yaml
import shutil
import pandas as pd
from pathlib import Path
from collections import defaultdict
import numpy as np
import time
import bisect

# Regex zum Parsen der Originaldateinamen
FILENAME_RE = re.compile(
    r'^PECD_(?P<tech>LFSolarPV|Wind_Onshore|Wind_Offshore|CSP_noStorage)_(?P<year>\d{4})_(?P<zone>[A-Z0-9]+)_edition [\w\.\- ]+$'
)

# Technologie-Abkürzungen
TECH_ABBREVIATIONS = {
    "LFSolarPV": "pv",
    "Wind_Onshore": "wind_on",
    "Wind_Offshore": "wind_off",
    "CSP_noStorage": "csp"
}

class Preprocess:
    def __init__(self, config_path: str = "config.yaml"):
        self.config = self._load_config(config_path)
        self.input_path = Path(self.config["pecd_path"])
        self.target_year = str(self.config["target_year"])
        self.region_mapping = self.config["region_zone_mapping"]
        self.chosen_dir = self.input_path.parent / "chosen_pecd_files"
        self.unavailability_dir = self.input_path.parent / "unavailability_files"  # 🆕 Ordnername geändert

    def _load_config(self, path: str):
        with open(path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f)

    def get_valid_zone_tech_pairs(self, verbose=True):
        valid_pairs = set()
        for _, tech_dict in self.region_mapping.items():
            for tech, tech_data in tech_dict.items():
                if "source_zones" not in tech_data:
                    continue
                # Check für relevante Technologien
                if tech in ("Wind_Onshore", "Wind_Offshore"):
                    if tech_data.get("kwid_shape_a") is None:
                        continue
                elif tech in ("LFSolarPV", "CSP_noStorage"):
                    if tech_data.get("kwid") is None:
                        continue
                for zone in tech_data["source_zones"]:
                    valid_pairs.add((zone, tech))
        if verbose:
            print(f"🧮 Total number of valid (zone, tech) pairs: {len(valid_pairs)}")
        return valid_pairs

    def _parse_filename(self, path: Path):
        m = FILENAME_RE.match(path.stem)
        if not m:
            return None
        return m.group("tech"), m.group("year"), m.group("zone")

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
        print(f"✅ {count} relevant files copied to: {self.chosen_dir}")
        print(f"❌ {len(missing_pairs)} valid pairs could not be matched to a file")

        if missing_pairs:
            missing_by_tech = defaultdict(list)
            for zone, tech in missing_pairs:
                missing_by_tech[tech].append(zone)
            print("📄 Missing pairs grouped by tech:")
            for tech, zones in missing_by_tech.items():
                print(f"   - {tech}: {', '.join(sorted(zones))}")

    def process_unavailability_files(self):
        """
        Verarbeitet die ausgewählten CSV-Dateien (chosen_pecd_files),
        berechnet Unavailability = 1 - Number für alle Werte außer
        der ersten Zeile und Spalte, rundet auf 4 Nachkommastellen
        und speichert die Dateien mit neuer Namenskonvention.
        """
        self.unavailability_dir.mkdir(exist_ok=True)
        processed_count = 0
        failed_files = []

        for file in self.chosen_dir.iterdir():
            if file.suffix.lower() != ".csv":
                continue

            # 🧭 Dateiname parsen
            parsed = self._parse_filename(file)
            if not parsed:
                print(f"⚠️ Could not parse filename: {file.name}")
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
                # 📥 CSV einlesen — Zeile 11 (Index 10) als Header
                df = pd.read_csv(file, header=10)  # oder header=9, wenn du Zeile 10 willst

                # 📊 Number-Daten ab Zeile 12 (Index 11) extrahieren
                df_number = df.copy()
                df_number.columns = df_number.columns.str.strip()
                df_number.reset_index(drop=True, inplace=True)

                # 🧮 Unavailability berechnen (alles außer 1. Zeile & Spalte)
                df_number.iloc[:, 2:] = df_number.iloc[:, 2:].apply(
                    lambda x: 1 - pd.to_numeric(x, errors="coerce")
                ).round(4)

                # 💾 Speichern
                df_number.to_csv(out_path, index=False, float_format="%.4f")
                processed_count += 1
                print(f"✅ {file.name} → {new_name} gespeichert")

            except Exception as e:
                print(f"❌ Fehler beim Verarbeiten von {file.name}: {e}")
                failed_files.append(file.name)

        # 📝 Zusammenfassung
        print(f"📊 {processed_count} files processed and saved to: {self.unavailability_dir}")
        if failed_files:
            print("❌ The following files could not be processed:")
            for fname in failed_files:
                print(f"   - {fname}")

    def calculate_special_region_files(self):

        """
        Erstellt aggregierte Unavailability-CSV-Dateien für Spezialregionen
        (mit mehreren Quellzonen & Gewichten) und kopiert Single-Zone-Dateien unverändert
        in den Zielordner.
        Wind_Onshore / Wind_Offshore-Einträge ohne kwid_shape_a werden übersprungen.
        Nutzt dieselbe Berechnungslogik wie process_unavailability_files.
        """
        import shutil
        import pandas as pd

        special_out_dir = self.input_path.parent / "unavailability_files_plus_special"
        special_out_dir.mkdir(exist_ok=True)

        processed_special = 0
        processed_copied = 0
        failed = []

        print("\n🧮 Starting special region file calculation...")
        print(f"📂 Output folder: {special_out_dir}\n")

        for region, tech_dict in self.region_mapping.items():
            for tech, tech_data in tech_dict.items():

                # 🪄 Skip Wind_Onshore / Wind_Offshore with no shape_a kwid
                if tech in ("Wind_Onshore", "Wind_Offshore") and tech_data.get("kwid_shape_a") is None:
                    continue

                tech_abbr = TECH_ABBREVIATIONS.get(tech, tech)
                parts = [tech_abbr, self.target_year, region]
                if tech in ("Wind_Onshore", "Wind_Offshore"):
                    parts.append("shape_a")
                out_name = "_".join(parts) + ".csv"
                out_path = special_out_dir / out_name

                # 🎯 Spezialregion mit mehreren Quellzonen
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
                                print(f"⚠️ Missing source file for special region: {file_name}")
                                continue

                            df = pd.read_csv(file_path)
                            used_files.append((zone, weight, file_name))

                            # 🧱 Struktur übernehmen
                            if combined_df is None:
                                combined_df = df.copy()
                                combined_df.iloc[:, 2:] = 0

                            # 🧮 Gewichtet aufaddieren — ab Spalte 3, alle Zeilen
                            combined_df.iloc[:, 2:] += df.iloc[:, 2:].apply(
                                pd.to_numeric, errors="coerce"
                            ) * weight

                        if combined_df is None:
                            raise ValueError("No valid source files found for this special region")

                        # 🧮 Runden auf 4 Nachkommastellen
                        combined_df.iloc[:, 2:] = combined_df.iloc[:, 2:].round(4)

                        # 💾 Speichern
                        combined_df.to_csv(out_path, index=False, float_format="%.4f")
                        processed_special += 1

                        print(f"✅ Special file created: {out_name}")
                        for z, w, fname in used_files:
                            print(f"   └─ Used {fname} (zone {z}, weight {w})")

                    except Exception as e:
                        print(f"❌ Failed to calculate special file for {region}-{tech}: {e}")
                        failed.append(f"{region}-{tech}")

                # 📋 Single-Zone Region — Datei einfach kopieren
                elif "source_zones" in tech_data and len(tech_data["source_zones"]) == 1:
                    try:
                        zone = tech_data["source_zones"][0]
                        file_name_parts = [tech_abbr, self.target_year, zone]
                        if tech in ("Wind_Onshore", "Wind_Offshore"):
                            file_name_parts.append("shape_a")
                        file_name = "_".join(file_name_parts) + ".csv"

                        src_file = self.unavailability_dir / file_name
                        if not src_file.exists():
                            print(f"⚠️ Missing single-zone file: {file_name}")
                            failed.append(f"{region}-{tech}")
                            continue

                        shutil.copy2(src_file, out_path)
                        processed_copied += 1
                        print(f"📋 Copied single-zone file: {file_name} → {out_name}")

                    except Exception as e:
                        print(f"❌ Failed to copy file for {region}-{tech}: {e}")
                        failed.append(f"{region}-{tech}")

        # 📝 Zusammenfassung
        print("\n📊 Special region calculation summary:")
        print(f"   ✅ {processed_special} special files created")
        print(f"   📋 {processed_copied} single-zone files copied")
        if failed:
            print(f"   ❌ {len(failed)} failed:")
            for f in failed:
                print(f"      - {f}")

    def generate_shape_b_files(self):
        """
        Generiert Shape-B-Dateien basierend auf Shape-A-Dateien.
        Erste Zeile und die ersten 2 Spalten der Shape-A-Dateien bleiben unverändert.
        Ab Spalte 2 werden Werte mithilfe der Mapping-Dateien transformiert
        (nächstliegender Wert aus shpab_offshore/onshore).
        """
        start_all = time.time()

        # 📂 Verzeichnisse
        shape_a_dir = self.input_path.parent / "unavailability_files_plus_special"
        shape_b_dir = self.input_path.parent / "shape_b_files"
        shape_b_dir.mkdir(exist_ok=True)

        helping_dir = self.input_path.parent / "helping_files"
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
            """
            Extrahiert eindeutige (a,b)-Paare basierend auf den a-Werten.
            Behalte nur den ersten b-Wert pro neu auftretendem a.
            Annahme: a ist fallend oder gleichbleibend.
            """
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
                # Wenn a_val == prev_a → ignorieren

            # Arrays umdrehen, falls absteigend (bisect braucht aufsteigend sortiert)
            if len(unique_a) > 1 and unique_a[0] > unique_a[-1]:
                unique_a = unique_a[::-1]
                unique_b = unique_b[::-1]

            return np.array(unique_b), np.array(unique_a)

        # 🧭 Unique & sortierte Mapping-Arrays erzeugen
        offshore_b, offshore_a = extract_unique_mapping(offshore)
        onshore_b, onshore_a = extract_unique_mapping(onshore)

        mapping_dict = {
            "wind_off": (offshore_b, offshore_a),
            "wind_on": (onshore_b, onshore_a)
        }

        # 🧾 KWID-Mapping laden
        kwid_map = pd.read_excel(kwid_mapping_path)
        kwid_map.columns = [c.strip().lower() for c in kwid_map.columns]

        # Spalten prüfen
        required_cols = ['region', 'technology', 'kwid', 'shapetype', 'regid', 'tech_abb']
        for col in required_cols:
            if col not in kwid_map.columns:
                raise ValueError(f"❌ Erwartete Spalte '{col}' fehlt in der Mapping-Datei.")

        # Nur Shape-A für Windtechnologien
        shape_a_rows = kwid_map[
            kwid_map['shapetype'].str.contains('a', case=False, na=False) &
            kwid_map['tech_abb'].isin(['wind_on', 'wind_off'])
            ]

        # 📋 Vorabprüfung auf fehlende Shape-A-Dateien
        print("\n📋 Vorprüfung auf Shape-A-Dateien:")
        missing_before = []
        for _, row in shape_a_rows.iterrows():
            tech = row['tech_abb']
            region = row['region']
            year = self.config.get('target_year')
            shape_a_file = shape_a_dir / f"{tech}_{year}_{region}_shape_a.csv"
            if not shape_a_file.exists():
                missing_before.append(shape_a_file.name)

        if missing_before:
            print(f"⚠️ {len(missing_before)} fehlende Shape-A-Dateien vor Start:")
            for f in missing_before:
                print(f"  - {f}")
        else:
            print("✅ Alle benötigten Shape-A-Dateien sind vorhanden.")

        generated_count = 0
        missing_files = []
        failed_pairs = []
        expected_shape_b_files = []

        # 🌀 Hauptloop — einzigartig pro Region + Technologie
        for _, row in shape_a_rows.drop_duplicates(subset=['region', 'tech_abb']).iterrows():
            tech = row['tech_abb']
            region = row['region']
            year = self.config.get('target_year')

            shape_a_file = shape_a_dir / f"{tech}_{year}_{region}_shape_a.csv"
            shape_b_file = shape_b_dir / f"{tech}_{year}_{region}_shape_b.csv"
            expected_shape_b_files.append(shape_b_file)

            start_file = time.time()

            if not shape_a_file.exists():
                missing_files.append(shape_a_file)
                continue

            # 📥 Shape A laden – Header + ersten 2 Spalten behalten, Rest transformieren
            try:
                df_raw = pd.read_csv(shape_a_file, header=None)
                header = df_raw.iloc[0].tolist()
                df_data = df_raw.iloc[1:].copy()

                # erste 2 Spalten separieren
                df_first_columns = df_data.iloc[:, :2].copy()

                # numerischen Block isolieren
                df_numeric = df_data.iloc[:, 2:].copy()

                flat_vals = df_numeric.to_numpy().flatten()
                if np.isnan(flat_vals).all():
                    raise ValueError("Keine numerischen Werte in den relevanten Spalten gefunden.")

            except Exception as e:
                print(f"❌ Fehler beim Laden von {shape_a_file.name}: {e}")
                failed_pairs.append((region, tech))
                continue

            # 🧮 Shape B bestimmen
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

            # 🧱 Finale Struktur: Header + erste 2 Spalten + transformierte Werte
            df_result = pd.concat([df_first_columns, df_transformed], axis=1)
            df_result.loc[-1] = header
            df_result.index = df_result.index + 1
            df_result = df_result.sort_index()

            # 📤 Shape-B-Datei schreiben
            try:
                cleaned_header = []
                for i, val in enumerate(header):
                    if i < 2:
                        cleaned_header.append(str(val))  # sicherheitshalber auch String
                    else:
                        try:
                            cleaned_header.append(str(int(float(val))))  # explizit String!
                        except:
                            cleaned_header.append(str(val))

                # Header zurückschreiben
                df_result.iloc[0] = cleaned_header

                # 📤 Datei speichern
                df_result.to_csv(shape_b_file, index=False, header=False)
                generated_count += 1
                elapsed_file = time.time() - start_file
                print(f"✅ {shape_b_file.name} erzeugt in {self._format_time(elapsed_file)}")
            except Exception as e:
                print(f"❌ Fehler beim Schreiben von {shape_b_file.name}: {e}")
                failed_pairs.append((region, tech))

        # 📊 Zusammenfassung
        elapsed_total = time.time() - start_all
        expected_count = len(expected_shape_b_files)

        print("\n📊 Zusammenfassung")
        print(f"⏳ Gesamte Berechnungszeit: {self._format_time(elapsed_total)}")
        print(f"✅ {generated_count}/{expected_count} Shape-B-Dateien erfolgreich erzeugt.")

        if missing_files:
            print(f"⚠️ {len(missing_files)} fehlende Shape-A-Dateien:")
            for f in missing_files:
                print(f"  - {f.name}")

        if failed_pairs:
            print(f"❌ {len(failed_pairs)} Paare konnten nicht verarbeitet werden:")
            for region, tech in failed_pairs:
                print(f"  - {region} / {tech}")

        # Kontrolle: erwartete vs. generierte Dateien
        existing_b_files = {f.name for f in shape_b_dir.glob("*.csv")}
        expected_b_files_set = {f.name for f in expected_shape_b_files}
        missing_b = [f for f in expected_b_files_set if f not in existing_b_files]

        if missing_b:
            print(f"⚠️ {len(missing_b)} erwartete Shape-B-Dateien fehlen nach der Berechnung:")
            for f in missing_b:
                print(f"  - {f}")
        else:
            print("🎯 Alle erwarteten Shape-B-Dateien wurden erfolgreich erzeugt.")

    def _find_nearest_b(self, value, a_values, b_values):
        """
        Findet den nächstgelegenen Wert in a_values und gibt den entsprechenden B-Wert zurück.
        a_values MUSS sortiert sein!
        """
        if np.isnan(value):
            return np.nan

        # Sicherheitscheck für Werte außerhalb des Mappingbereichs
        if value <= a_values[0]:
            return b_values[0]
        if value >= a_values[-1]:
            return b_values[-1]

        pos = bisect.bisect_left(a_values, value)
        before = a_values[pos - 1]
        after = a_values[pos]

        if after - value < value - before:
            return b_values[pos]
        else:
            return b_values[pos - 1]

    def _format_time(self, seconds):
        """
        Formatiert Sekunden in ein lesbares Format (z. B. 0h 5m 32s).
        """
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        return f"{hours}h {minutes}m {secs}s"

    def generate_weather_year_files(self):
        """
        Erzeugt für jedes Wetterjahr eine konsolidierte CSV-Datei (WeatherYear_XXXX.csv),
        indem nur die relevanten Spalten aus Shape-A- oder Shape-B-Dateien geladen werden.
        Wetterjahre befinden sich in der ersten Zeile ab Spalte 3.
        """
        import logging

        # 📂 Pfade
        shape_b_dir = self.input_path.parent / "shape_b_files"
        shape_a_dir = self.input_path.parent / "unavailability_files_plus_special"
        helping_dir = self.input_path.parent / "helping_files"
        mapping_file = helping_dir / "kwid_reg_mapping.xlsx"
        output_base = self.input_path.parent / "Weather_Year_Files"
        output_base.mkdir(exist_ok=True)

        # 📅 Wetterjahre aus Config
        weather_years_cfg = self.config["weather_years"]
        weather_years = list(range(weather_years_cfg["start"], weather_years_cfg["end"]))
        if not weather_years:
            raise ValueError("❌ Keine Wetterjahre in config.yaml (key: weather_years) gefunden.")

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

        # 🌀 Hauptloop über Wetterjahre
        for year in weather_years:
            result_df = pd.DataFrame(columns=['VARID', 'KWID', 'PKTNR', 'REVNV', 'RID'])
            logging.info(f"🌦️ Verarbeitung Wetterjahr {year}")

            for _, row in kwid_map.iterrows():
                kwid = row['kwid']
                tech = row['tech_abb']
                region = row['region']
                target_year = str(self.target_year)

                # 🧭 shapetype prüfen und normalisieren
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
                    # Wenn kein shapetype vorhanden ist → Shape A/B Ordner prüfen
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

                # Wetterjahre beginnen ab Spalte 3 (Index 2)
                header_years = [str(int(float(h))) if str(h).replace('.', '', 1).isdigit() else str(h) for h in
                                header_row[2:]]

                year_str = str(year)
                if year_str not in header_years:
                    missing_year_cols.append((kwid, filename, year))
                    logging.warning(f"⚠️ Jahr {year} nicht in Datei {filename}")
                    continue

                # Index der Spalte mit dem Jahr ermitteln (+2, weil ab Spalte 3)
                year_index = header_years.index(year_str) + 2
                usecols = [0, 1, year_index]

                # 📥 Nur relevante Spalten laden (ohne Header-Zeile)
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
                year_dir = output_base / str(year)
                year_dir.mkdir(exist_ok=True)
                output_file = year_dir / f"WeatherYear_{year}.csv"
                result_df.to_csv(output_file, index=False)
                logging.info(f"✅ Wetterjahr {year} erfolgreich erstellt: {output_file}")
                successful_years.append(year)
            else:
                logging.warning(f"⚠️ Wetterjahr {year} konnte nicht erzeugt werden (keine Daten)")
                failed_years.append(year)

        # 📝 Zusammenfassung
        print("\n📊 Zusammenfassung Wetterjahres-Erzeugung:")
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
                print(f"      - KWID {kwid}: {fname} (Jahr {yr} fehlt)")




