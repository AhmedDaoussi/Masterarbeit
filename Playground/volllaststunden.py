import os
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
# =========================
# 1. Mapping & Pivot laden
# =========================

mapping = pd.read_excel(
    r"C:\Users\ahmed\Desktop\Data_pfad\2023\helping_files\kwid_reg_mapping.xlsx"
)
excel_file = r"C:\Users\ahmed\Desktop\Masterarbeit_alt\Hilfs_dateien_berechnungen\Nichtverfuegbarkeitsvektoren.xlsx"
sheets = ['PV_Vektor', 'Onshore_Vektor', 'Offshore_Vektor']

pivot_dfs = {}

for tec in sheets:
    df = pd.read_excel(excel_file, sheet_name=tec)

    # --- KW_NAME & KWID ---
    kw_names = df.columns
    kw_id = pd.to_numeric(df.iloc[0], errors='coerce').fillna(0).astype('Int64')

    # --- Vollaststunden berechnen ---
    vollaststunden_2016 = 8760 - pd.to_numeric(df.iloc[1:8761].sum(), errors='coerce')
    excel_row = 8762 if tec == 'PV_Vektor' else 8761

    pivot_df = pd.DataFrame({
        'KW_NAME': kw_names,
        'KWID': kw_id,
        'vollaststunden_2016': vollaststunden_2016
    })

    # Mapping hinzufügen
    pivot_df['KWID'] = pd.to_numeric(pivot_df['KWID'], errors='coerce').fillna(0).astype('Int64')
    pivot_df = pd.merge(pivot_df, mapping, on='KWID', how='left')

    # Index auf KWID setzen für schnellen Join
    pivot_df = pivot_df.set_index('KWID')

    pivot_dfs[tec] = pivot_df

# Basis-DF für alle Technologien
base_df = pd.concat([
    pivot_dfs['PV_Vektor'],
    pivot_dfs['Onshore_Vektor'],
    pivot_dfs['Offshore_Vektor']
])

# 🔸 WICHTIG: ShapeType für PV auffüllen, damit sie bei groupby nicht verloren gehen
base_df['ShapeType'] = base_df['ShapeType'].fillna('NoShape')

# =========================
# 2. Ausgabepfade
# =========================

out_dir = r"C:\Users\ahmed\Desktop\Data_pfad\2023\Comparison_2016"
os.makedirs(out_dir, exist_ok=True)

output_file_years = os.path.join(out_dir, "comparison_weather_years.xlsx")
output_file_stats = os.path.join(out_dir, "delta_stunden_statistik.xlsx")
output_file_avg = os.path.join(out_dir, "comparison_weather_avg.xlsx")
output_file_stats_avg = os.path.join(out_dir, "delta_stunden_statistik_avg.xlsx")

# Container für Durchschnittsberechnung
weather_year_values = []

# =========================
# 3. Jahresloop
# =========================

with pd.ExcelWriter(output_file_years) as writer1, pd.ExcelWriter(output_file_stats) as writer2:
    for year in range(1982, 2020):
        file_path = fr"C:\Users\ahmed\Desktop\Data_pfad\2023\Weather_Year_Files\{year}\WeatherYear_{year}.csv"
        weather_year = pd.read_csv(file_path, usecols=['KWID', 'REVNV'])

        # Summe pro KWID
        result_df = weather_year.groupby('KWID', as_index=True)['REVNV'].sum()
        result_df = 8760 - result_df
        result_df = result_df.rename('full load hours_weather_year')

        # Speichern für Durchschnitt
        weather_year_values.append(result_df)

        # Vergleich
        comparison_df = base_df.join(result_df, how='left')
        comparison_df['delta_stunden'] = (
            comparison_df['full load hours_weather_year'] - comparison_df['vollaststunden_2016']
        )

        comparison_df = comparison_df.round({
            'full load hours_weather_year': 1,
            'vollaststunden_2016': 1,
            'delta_stunden': 1
        })

        # Statistik nach ShapeType & Tech_Abb
        stat_df = (
            comparison_df
            .groupby(['ShapeType', 'Tech_Abb'])['delta_stunden']
            .mean()
            .reset_index()
            .round({'delta_stunden': 1})
        )

        # Export Detail
        comparison_df.reset_index().to_excel(writer1, sheet_name=str(year), index=False)

        # Export Statistik
        stat_df.to_excel(writer2, sheet_name=str(year), index=False)

        print(f"✅ Jahr {year} fertig.")

# =========================
# 4. Durchschnitt über alle Wetterjahre
# =========================

weather_avg = pd.concat(weather_year_values, axis=1).mean(axis=1)
weather_avg = weather_avg.rename('vollaststunden_avg')

# =========================
# 5. Vergleich 2016 vs. Durchschnitt
# =========================

comparison_avg_df = base_df.join(weather_avg, how='left')
comparison_avg_df['delta_stunden_avg'] = (
    comparison_avg_df['vollaststunden_avg'] - comparison_avg_df['vollaststunden_2016']
)
comparison_avg_df = comparison_avg_df.round({
    'vollaststunden_avg': 1,
    'vollaststunden_2016': 1,
    'delta_stunden_avg': 1
})

# =========================
# 6. Statistik nach ShapeType / Tech_Abb
# =========================

stat_avg_df = (
    comparison_avg_df
    .groupby(['ShapeType', 'Tech_Abb'])['delta_stunden_avg']
    .mean()
    .reset_index()
    .round({'delta_stunden_avg': 1})
)

# =========================
# 7. Export Durchschnittsergebnisse
# =========================

with pd.ExcelWriter(output_file_avg) as writer3:
    comparison_avg_df.reset_index().to_excel(writer3, sheet_name="AVG", index=False)

with pd.ExcelWriter(output_file_stats_avg) as writer4:
    stat_avg_df.to_excel(writer4, sheet_name="AVG", index=False)

print(f"📊 Export aller Detaildaten pro Jahr: {output_file_years}")
print(f"📈 Export aller Statistik pro Jahr: {output_file_stats}")
print(f"📊 Export Vergleich 2016 vs. Durchschnitt: {output_file_avg}")
print(f"📈 Export Statistik 2016 vs. Durchschnitt: {output_file_stats_avg}")


out_dir = r"C:\Users\ahmed\Desktop\Data_pfad\2023\Comparison_2016"
plot_dir = os.path.join(out_dir, "plots_boxplots")
os.makedirs(plot_dir, exist_ok=True)

# ==========================================
# 🧮 Daten vorbereiten
# ==========================================
# Wetterjahre-Matrix: Index = KWID, Spalten = Jahre
years = list(range(1982, 2020))
weather_matrix = pd.concat(weather_year_values, axis=1)
weather_matrix.columns = years

# 2016-Werte je KWID
vollast_2016 = base_df['vollaststunden_2016']

# Gruppierungsinfo für Tech und Shape
group_info = base_df[['Tech_Abb', 'ShapeType']].copy()
group_info['ShapeType'] = group_info['ShapeType'].fillna('NoShape')

# ==========================================
# 📊 Alle Kombis (Tech_Abb / ShapeType)
# ==========================================
groups = []
for (tech, shape), idx in group_info.groupby(['Tech_Abb', 'ShapeType']).groups.items():
    if len(idx) == 0:
        continue
    vals = weather_matrix.loc[idx].values.flatten()
    vals = vals[~np.isnan(vals)]
    if vals.size == 0:
        continue
    groups.append((tech, shape, idx))

if not groups:
    raise RuntimeError("Keine Gruppen mit Daten gefunden (Tech_Abb/ShapeType).")

# Boxplot-Daten sammeln
box_data = []
labels = []
y2016_points = []
hist_means = []

for (tech, shape, idx) in groups:
    all_vals = weather_matrix.loc[idx].values.flatten()
    all_vals = all_vals[~np.isnan(all_vals)]
    box_data.append(all_vals)
    labels.append(f"{shape}/{tech}")
    y2016_points.append(vollast_2016.loc[idx].mean())
    hist_means.append(np.mean(all_vals))  # 🟩 Historischer Mittelwert

# ==========================================
# 📈 Plot erstellen (ALLE Kombis)
# ==========================================
n = len(box_data)
fig_w = max(10, n * 1.2)
plt.figure(figsize=(fig_w, 6))

bp = plt.boxplot(
    box_data,
    vert=True,
    patch_artist=True,
    showfliers=True
)

# Styling
for patch in bp['boxes']:
    patch.set_facecolor('#9ecae1')
    patch.set_edgecolor('black')
for whisker in bp['whiskers']:
    whisker.set_color('black')
for cap in bp['caps']:
    cap.set_color('black')
for median in bp['medians']:
    median.set_color('black')

positions = np.arange(1, n + 1)
plt.scatter(positions, y2016_points, s=60, c='red', marker='o', zorder=3, label='2016')
plt.scatter(positions, hist_means, s=60, c='green', marker='D', zorder=3, label='Mean_Weather_Years')

plt.xticks(positions, labels, rotation=45, ha='right')
plt.ylabel("Full-Load Hours")
plt.xlabel("Combination (ShapeType / Tech_Abb)")
plt.title("Average Full-Load Hours Distribution For All Regions:\n 1982–2019 Weather Years (Boxplot) vs. Historical Average (Green) and 2016 Typical Weather Year (Red)")
plt.grid(axis='y', alpha=0.3)
plt.legend(loc='upper right')

plt.tight_layout()

# 📤 Export
outfile = os.path.join(plot_dir, "boxplot_alle_kombis.png")
plt.savefig(outfile, dpi=300)
plt.close()

print(f"📊 Boxplot aller Kombis exportiert: {outfile}")

# ==========================================
# 📊 Regionale Boxplots
# ==========================================
plot_dir_regions = os.path.join(out_dir, "plots_boxplots_by_region")
os.makedirs(plot_dir_regions, exist_ok=True)

# Gruppierungsinfos erweitern um Region
group_info = base_df[['Tech_Abb', 'ShapeType', 'Region']].copy()
group_info['ShapeType'] = group_info['ShapeType'].fillna('NoShape')

# Alle eindeutigen Regionen ermitteln
regionen = group_info['Region'].dropna().unique()

for region in regionen:
    region_idx = group_info[group_info['Region'] == region].index
    if len(region_idx) == 0:
        continue

    # Gruppieren nach Tech/Shape innerhalb der Region
    region_groups = []
    for (tech, shape), idx in group_info.loc[region_idx].groupby(['Tech_Abb', 'ShapeType']).groups.items():
        vals = weather_matrix.loc[idx].values.flatten()
        vals = vals[~np.isnan(vals)]
        if vals.size == 0:
            continue
        region_groups.append((tech, shape, idx))

    if not region_groups:
        continue

    # Daten sammeln
    box_data = []
    labels = []
    y2016_points = []
    hist_means = []

    for (tech, shape, idx) in region_groups:
        all_vals = weather_matrix.loc[idx].values.flatten()
        all_vals = all_vals[~np.isnan(all_vals)]
        box_data.append(all_vals)
        labels.append(f"{shape}/{tech}")
        y2016_points.append(vollast_2016.loc[idx].mean())
        hist_means.append(np.mean(all_vals))

    # Plot erstellen
    n = len(box_data)
    fig_w = max(10, n * 1.2)
    plt.figure(figsize=(fig_w, 6))

    bp = plt.boxplot(
        box_data,
        vert=True,
        patch_artist=True,
        showfliers=True
    )

    for patch in bp['boxes']:
        patch.set_facecolor('#9ecae1')
        patch.set_edgecolor('black')
    for whisker in bp['whiskers']:
        whisker.set_color('black')
    for cap in bp['caps']:
        cap.set_color('black')
    for median in bp['medians']:
        median.set_color('black')

    positions = np.arange(1, n + 1)
    plt.scatter(positions, y2016_points, s=60, c='red', marker='o', zorder=3, label='2016')
    plt.scatter(positions, hist_means, s=60, c='green', marker='D', zorder=3, label='Mittelwert_Wetterjahre')

    plt.xticks(positions, labels, rotation=45, ha='right')
    plt.ylabel("Full-Load Hours")
    plt.xlabel("Combination (ShapeType / Tech_Abb)")
    plt.title(f"Region: {region}\nFull-Load Hours Distribution: 1982–2019 Weather Years (Boxplot) vs. Historical Average (Green)\n and 2016 Typical Weather Year (Red))")
    plt.grid(axis='y', alpha=0.3)
    plt.legend()

    plt.tight_layout()

    safe_region = str(region).replace("/", "_").replace(" ", "_")
    filepath = os.path.join(plot_dir_regions, f"boxplot_{safe_region}.png")
    plt.savefig(filepath, dpi=300)
    plt.close()

    print(f"📊 Boxplot für Region '{region}' exportiert: {filepath}")

print("✅ Alle regionalen Boxplots erfolgreich erstellt!")