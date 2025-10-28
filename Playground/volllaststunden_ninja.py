import os
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

# ===============================
# CONFIG
# ===============================
INCLUDE_SHAPE_B = False   # ✅ Toggle this to include or exclude Shape B

# ===============================
# REGION-CODE-MAPPING
# ===============================
REGION_TO_COUNTRY_CODE = {
    "Austria": "AT",
    "Belgium": "BE",
    "Bulgaria": "BG",
    "SloCro": "HR",
    "Czech Republic": "CZ",
    "DenmarkEast": "DK",
    "Finland": "FI",
    "France": "FR",
    "Germany": "DE",
    "Greece": "GR",
    "Hungary": "HU",
    "IT_CS": "IT",
    "Netherlands": "NL",
    "Norway": "NO",
    "Poland": "PL",
    "Portugal": "PT",
    "Romania": "RO",
    "Balkans": "RS",
    "Slovakia": "SK",
    "Spain": "ES",
    "SWE1and2": "SE",
    "Switzerland": "CH",
    "England": "GB"
}

# ===============================
# LIMIT TO SPECIFIC TECHNOLOGIES PER REGION
# ===============================
LIMITED_REGIONS_TECHS = {
    "Austria": ["pv", "onshore"],
    "Balkans": ["pv"],
    "Belgium": ["pv", "onshore", "offshore"],
    "Bulgaria": ["pv", "onshore"],
    "Czech Republic": ["pv", "onshore"],
    "DenmarkEast": ["pv", "onshore", "offshore"],
    "England": ["pv", "onshore", "offshore"],
    "Finland": ["pv", "onshore", "offshore"],
    "France": ["pv", "onshore", "offshore"],
    "Germany": ["pv", "onshore", "offshore"],
    "Greece": ["pv", "onshore"],
    "Hungary": ["pv", "onshore"],
    "IT_CS": ["pv", "onshore"],
    "Netherlands": ["pv", "onshore", "offshore"],
    "Norway": ["pv", "onshore", "offshore"],
    "Poland": ["pv", "onshore", "offshore"],
    "Portugal": ["pv", "onshore", "offshore"],
    "Romania": ["pv", "onshore"],
    "SloCro": ["pv", "onshore"],
    "Slovakia": ["pv", "onshore"],
    "Spain": ["pv", "onshore", "offshore"],
    "SWE1and2": ["pv", "onshore"],
    "Switzerland": ["pv", "onshore"]
}

# ===============================
# FILE PATHS
# ===============================
ninja_base_path = r"C:\Users\ahmed\Downloads\ninja_split_yearly"

eraa_pv_template   = r"C:\Users\ahmed\Desktop\Data_pfad\2023\unavailability_files_plus_special\pv_2033_{region}.csv"
eraa_on_a_template = r"C:\Users\ahmed\Desktop\Data_pfad\2023\unavailability_files_plus_special\wind_on_2033_{region}_shape_a.csv"
eraa_on_b_template = r"C:\Users\ahmed\Desktop\Data_pfad\2023\shape_b_files\wind_on_2033_{region}_shape_b.csv"
eraa_off_a_template= r"C:\Users\ahmed\Desktop\Data_pfad\2023\unavailability_files_plus_special\wind_off_2033_{region}_shape_a.csv"
eraa_off_b_template= r"C:\Users\ahmed\Desktop\Data_pfad\2023\shape_b_files\wind_off_2033_{region}_shape_b.csv"

output_dir = r"C:\Users\ahmed\Desktop\Data_pfad\2023\Comparison_Ninja_AllRegions_Boxplots"
os.makedirs(output_dir, exist_ok=True)

# ===============================
# HELPERS
# ===============================
HOURS_PER_YEAR = 8760
MAX_REASONABLE = 8000  # upper filter threshold

def _warn(msg):
    print(f"⚠️  {msg}")

def get_ninja_path(iso, tech):
    """Return the best matching Ninja file for a region and tech."""
    region_folder = os.path.join(ninja_base_path, iso)
    candidates = []
    if tech == "pv":
        candidates = [f"{iso}_pv_national_current_yearly.csv"]
    elif tech == "onshore_a":
        candidates = [f"{iso}_wind_onshore_near-termfuture_yearly.csv",
                      f"{iso}_wind_national_near-termfuture_yearly.csv", f"{iso}_wind_national_current_yearly.csv"]
    elif tech == "onshore_b":
        candidates = [f"{iso}_wind_onshore_long-termfuture_yearly.csv",
                      f"{iso}_wind_national_long-termfuture_yearly.csv"]
    elif tech == "offshore_a":
        candidates = [f"{iso}_wind_offshore_near-termfuture_yearly.csv",
                      f"{iso}_wind_national_near-termfuture_yearly.csv", f"{iso}_wind_national_current_yearly.csv"]
    elif tech == "offshore_b":
        candidates = [f"{iso}_wind_offshore_long-termfuture_yearly.csv",
                      f"{iso}_wind_national_long-termfuture_yearly.csv"]

    for f in candidates:
        p = os.path.join(region_folder, f)
        if os.path.exists(p):
            return p
    return None

def load_flh(file_path, *, invert=False):
    """
    Load CSV and compute Full Load Hours per asset (column).

    ERAA (invert=True): values are UNAVAILABILITY (0/1 per hour) -> FLH = 8760 - sum(unavailability)
    Ninja (invert=False): values are AVAILABILITY (0/1 per hour)  -> FLH = sum(availability)
    """
    if file_path is None or not os.path.exists(file_path):
        return None

    df = pd.read_csv(file_path, index_col=0)
    df = df.apply(pd.to_numeric, errors='coerce')
    df = df.dropna(axis=1, how='all')

    n_rows = df.shape[0]
    if n_rows != HOURS_PER_YEAR:
        if n_rows > HOURS_PER_YEAR:
            _warn(f"{os.path.basename(file_path)} has {n_rows} rows; trimming to {HOURS_PER_YEAR}.")
            df = df.iloc[:HOURS_PER_YEAR, :]
        else:
            _warn(f"{os.path.basename(file_path)} has only {n_rows} rows (expected {HOURS_PER_YEAR}). Results may be biased.")

    sums = df.sum(axis=0)
    flh = (HOURS_PER_YEAR - sums) if invert else sums

    flh = flh.replace([np.inf, -np.inf], np.nan).dropna()
    flh = flh.clip(lower=0, upper=HOURS_PER_YEAR)
    flh = flh[flh <= MAX_REASONABLE]

    return flh.values if len(flh) > 0 else None

def plot_boxplot(region, title_suffix, data_list, label_list, out_name):
    """Plot and save a single boxplot for one technology group."""
    if not data_list:
        print(f"⚠️ Keine Daten für {region} - {title_suffix}")
        return

    n = len(data_list)
    fig_w = max(8, n * 1.2)
    plt.figure(figsize=(fig_w, 6))

    bp = plt.boxplot(data_list, vert=True, patch_artist=True, showfliers=False)

    colors = ['#fdae6b' if 'ERAA' in lbl else '#9ecae1' for lbl in label_list]
    for patch, col in zip(bp['boxes'], colors):
        patch.set_facecolor(col)
        patch.set_edgecolor('black')
    for whisker in bp['whiskers']:
        whisker.set_color('black')
    for cap in bp['caps']:
        cap.set_color('black')
    for median in bp['medians']:
        median.set_color('black')

    max_flh = max([arr.max() for arr in data_list if len(arr) > 0])
    plt.ylim(0, max_flh * 1.05)

    plt.xticks(np.arange(1, n + 1), label_list, rotation=30, ha='right')
    plt.ylabel("Full Load Hours")
    plt.title(f"{region} — {title_suffix} (Ninja vs ERAA)")
    plt.grid(axis='y', alpha=0.3)
    plt.tight_layout()

    safe_region = str(region).replace("/", "_").replace(" ", "_")
    plot_path = os.path.join(output_dir, f"{safe_region}_{out_name}.png")
    plt.savefig(plot_path, dpi=300)
    plt.close()

    print(f"✅ Boxplot für {region} ({title_suffix}) exportiert: {plot_path}")

# ===============================
# STORAGE FOR STATS
# ===============================
region_stats = []  # per region
overall_stats = {}  # aggregated by tech

# ===============================
# MAIN LOOP
# ===============================
for region, iso in REGION_TO_COUNTRY_CODE.items():
    if region not in LIMITED_REGIONS_TECHS:
        continue

    allowed_techs = LIMITED_REGIONS_TECHS[region]

    def record_mean(tech, eraadata, ninjadata):
        eraamean = np.mean(eraadata) if eraadata is not None else np.nan
        ninjamean = np.mean(ninjadata) if ninjadata is not None else np.nan
        region_stats.append({
            "Region": region,
            "Technology": tech,
            "ERAA_mean": eraamean,
            "Ninja_mean": ninjamean
        })
        if tech not in overall_stats:
            overall_stats[tech] = {"eraa_vals": [], "ninja_vals": []}
        if not np.isnan(eraamean):
            overall_stats[tech]["eraa_vals"].append(eraamean)
        if not np.isnan(ninjamean):
            overall_stats[tech]["ninja_vals"].append(ninjamean)

    # PV
    if "pv" in allowed_techs:
        pv_eraa = load_flh(eraa_pv_template.format(region=region), invert=True)
        pv_ninja = load_flh(get_ninja_path(iso, "pv"), invert=False)
        record_mean("PV", pv_eraa, pv_ninja)
        plot_boxplot(region, "PV",
                     [d for d in [pv_eraa, pv_ninja] if d is not None],
                     [l for d, l in zip([pv_eraa, pv_ninja], ["PV - ERAA", "PV - Ninja"]) if d is not None],
                     "pv")

    # Onshore
    if "onshore" in allowed_techs:
        on_a_eraa = load_flh(eraa_on_a_template.format(region=region), invert=True)
        on_a_ninja = load_flh(get_ninja_path(iso, "onshore_a"), invert=False)
        record_mean("Onshore A", on_a_eraa, on_a_ninja)

        onshore_data = [d for d in [on_a_eraa, on_a_ninja] if d is not None]
        onshore_labels = [l for d, l in zip([on_a_eraa, on_a_ninja], ["Onshore A - ERAA", "Onshore A - Ninja"]) if d is not None]

        if INCLUDE_SHAPE_B:
            on_b_eraa = load_flh(eraa_on_b_template.format(region=region), invert=True)
            on_b_ninja = load_flh(get_ninja_path(iso, "onshore_b"), invert=False)
            record_mean("Onshore B", on_b_eraa, on_b_ninja)
            for d, l in zip([on_b_eraa, on_b_ninja], ["Onshore B - ERAA", "Onshore B - Ninja"]):
                if d is not None:
                    onshore_data.append(d)
                    onshore_labels.append(l)

        plot_boxplot(region, "Onshore", onshore_data, onshore_labels, "onshore")

    # Offshore
    if "offshore" in allowed_techs:
        off_a_eraa = load_flh(eraa_off_a_template.format(region=region), invert=True)
        off_a_ninja = load_flh(get_ninja_path(iso, "offshore_a"), invert=False)
        record_mean("Offshore A", off_a_eraa, off_a_ninja)

        offshore_data = [d for d in [off_a_eraa, off_a_ninja] if d is not None]
        offshore_labels = [l for d, l in zip([off_a_eraa, off_a_ninja], ["Offshore A - ERAA", "Offshore A - Ninja"]) if d is not None]

        if INCLUDE_SHAPE_B:
            off_b_eraa = load_flh(eraa_off_b_template.format(region=region), invert=True)
            off_b_ninja = load_flh(get_ninja_path(iso, "offshore_b"), invert=False)
            record_mean("Offshore B", off_b_eraa, off_b_ninja)
            for d, l in zip([off_b_eraa, off_b_ninja], ["Offshore B - ERAA", "Offshore B - Ninja"]):
                if d is not None:
                    offshore_data.append(d)
                    offshore_labels.append(l)

        plot_boxplot(region, "Offshore", offshore_data, offshore_labels, "offshore")

# ===============================
# SAVE METRICS TO EXCEL
# ===============================
region_df = pd.DataFrame(region_stats)
region_df = region_df.sort_values(by=["Technology", "Region"])
region_output_file = os.path.join(output_dir, "comparison_means_by_region.xlsx")
region_df.to_excel(region_output_file, index=False)
print(f"📊 Region-wise mean comparison saved to: {region_output_file}")

overall_rows = []
for tech, vals in overall_stats.items():
    eraa_mean = np.mean(vals["eraa_vals"]) if vals["eraa_vals"] else np.nan
    ninja_mean = np.mean(vals["ninja_vals"]) if vals["ninja_vals"] else np.nan
    overall_rows.append({
        "Technology": tech,
        "ERAA_mean_avg": eraa_mean,
        "Ninja_mean_avg": ninja_mean
    })

overall_df = pd.DataFrame(overall_rows)
overall_output_file = os.path.join(output_dir, "comparison_means_overall.xlsx")
overall_df.to_excel(overall_output_file, index=False)
print(f"📈 Overall mean comparison saved to: {overall_output_file}")
