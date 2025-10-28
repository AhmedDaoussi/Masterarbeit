import os

# =========================
# ERAA templates
# =========================
eraa_a_template = r"C:\Users\ahmed\Desktop\Data_pfad\2023\unavailability_files_plus_special\wind_on_2033_{region}_shape_a.csv"
eraa_b_template = r"C:\Users\ahmed\Desktop\Data_pfad\2023\shape_b_files\wind_on_2033_{region}_shape_b.csv"
eraa_pv_template = r"C:\Users\ahmed\Desktop\Data_pfad\2023\unavailability_files_plus_special\pv_2033_{region}.csv"


# =========================
# Ninja mapping helper
# =========================
def get_best_file(base_path, iso, tech):
    candidates = []

    if tech == "pv":
        candidates = [f"{iso}_pv_national_current_yearly.csv"]

    elif tech == "onshore_a":
        candidates = [
            f"{iso}_wind_onshore_near-termfuture_yearly.csv",
            f"{iso}_wind_national_near-termfuture_yearly.csv"
        ]

    elif tech == "onshore_b":
        candidates = [
            f"{iso}_wind_onshore_long-termfuture_yearly.csv",
            f"{iso}_wind_national_long-termfuture_yearly.csv"
        ]

    elif tech == "offshore_a":
        candidates = [
            f"{iso}_wind_offshore_near-termfuture_yearly.csv",
            f"{iso}_wind_national_near-termfuture_yearly.csv"
        ]

    elif tech == "offshore_b":
        candidates = [
            f"{iso}_wind_offshore_long-termfuture_yearly.csv",
            f"{iso}_wind_national_long-termfuture_yearly.csv"
        ]

    region_folder = os.path.join(base_path, iso)
    for filename in candidates:
        filepath = os.path.join(region_folder, filename)
        if os.path.exists(filepath):
            return filepath
    return None


# =========================
# Build mapping dictionary
# =========================
def build_mapping_dict(ninja_base_path):
    mapping = {}

    for iso in sorted(os.listdir(ninja_base_path)):
        region_folder = os.path.join(ninja_base_path, iso)
        if not os.path.isdir(region_folder):
            continue

        # Ninja mapping
        ninja_paths = {
            "pv": get_best_file(ninja_base_path, iso, "pv"),
            "onshore_a": get_best_file(ninja_base_path, iso, "onshore_a"),
            "onshore_b": get_best_file(ninja_base_path, iso, "onshore_b"),
            "offshore_a": get_best_file(ninja_base_path, iso, "offshore_a"),
            "offshore_b": get_best_file(ninja_base_path, iso, "offshore_b")
        }

        # ERAA mapping
        eraa_paths = {
            "pv": eraa_pv_template.format(region=iso),
            "onshore_a": eraa_a_template.format(region=iso),
            "onshore_b": eraa_b_template.format(region=iso)
            # Note: no offshore in ERAA templates here (can add later if needed)
        }

        # Combine
        mapping[iso] = {
            "ninja": ninja_paths,
            "eraa": eraa_paths
        }

    # remove countries with no ninja mapping at all
    mapping = {k: v for k, v in mapping.items() if any(v["ninja"].values())}
    return mapping


# =========================
# Example usage
# =========================
if __name__ == "__main__":
    ninja_base = r"C:\Users\ahmed\Downloads\ninja_split_yearly"
    mapping_dict = build_mapping_dict(ninja_base)

    for iso, files in mapping_dict.items():
        print(f"{iso}:")
        print("  Ninja:")
        for tech, path in files["ninja"].items():
            print(f"    {tech}: {path}")
        print("  ERAA:")
        for tech, path in files["eraa"].items():
            print(f"    {tech}: {path}")

print('a')