import os
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

# =========================
# 1. Mapping & Pivot laden
# =========================
mapping = pd.read_excel(
    r"C:\Users\ahmed\Desktop\Data_pfad\2024_ty_2026\helping_files\kwid_reg_mapping.xlsx"
)
excel_file = r"C:\Users\ahmed\Desktop\Masterarbeit_alt\Hilfs_dateien_berechnungen\Nichtverfuegbarkeitsvektoren.xlsx"
sheets = ['PV_Vektor', 'Onshore_Vektor', 'Offshore_Vektor']

pivot_dfs = {}

for tec in sheets:
    df = pd.read_excel(excel_file, sheet_name=tec)

    kw_names = df.columns
    kw_id = pd.to_numeric(df.iloc[0], errors='coerce').fillna(0).astype('Int64')

    vollaststunden_2016 = 8760 - pd.to_numeric(df.iloc[1:8761].sum(), errors='coerce')

    pivot_df = pd.DataFrame({
        'KW_NAME': kw_names,
        'KWID': kw_id,
        'vollaststunden_2016': vollaststunden_2016
    })

    pivot_df['KWID'] = pd.to_numeric(pivot_df['KWID'], errors='coerce').fillna(0).astype('Int64')
    pivot_df = pd.merge(pivot_df, mapping, on='KWID', how='left')
    pivot_df = pivot_df.set_index('KWID')

    pivot_dfs[tec] = pivot_df

# Basis-DF für alle Technologien
base_df = pd.concat([
    pivot_dfs['PV_Vektor'],
    pivot_dfs['Onshore_Vektor'],
    pivot_dfs['Offshore_Vektor']
])

# ShapeType für PV auffüllen
base_df['ShapeType'] = base_df['ShapeType'].fillna('NoShape')

# =========================
# 2. Ausgabepfade
# =========================
out_dir = r"C:\Users\ahmed\Desktop\Data_pfad\2024_ty_2026\Comparison_2016"
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
for i in range(1, 37):  # WS1 bis WS36
    ws_label = f"WS{i}"
    file_path = fr"C:\Users\ahmed\Desktop\Data_pfad\2024_ty_2026\Weather_Year_Files\{ws_label}\WeatherYear_{ws_label}.csv"

    weather_year = pd.read_csv(file_path, usecols=['KWID', 'REVNV'])

    result_df = weather_year.groupby('KWID', as_index=True)['REVNV'].sum()
    result_df = 8760 - result_df
    result_df = result_df.rename('vollaststunden_weatheryear')

    weather_year_values.append(result_df)

    comparison_df = base_df.join(result_df, how='left')
    comparison_df['delta_stunden'] = (
        comparison_df['vollaststunden_weatheryear'] - comparison_df['vollaststunden_2016']
    )

    comparison_df = comparison_df.round({
        'vollaststunden_weatheryear': 1,
        'vollaststunden_2016': 1,
        'delta_stunden': 1
    })

    stat_df = (
        comparison_df
        .groupby(['ShapeType', 'Tech_Abb'])['delta_stunden']
        .mean()
        .reset_index()
        .round({'delta_stunden': 1})
    )

    # Excel-Schreibvorgänge verschoben, damit sie nicht pro Loop geöffnet werden
    if i == 1:
        writer1 = pd.ExcelWriter(output_file_years, engine='openpyxl')
        writer2 = pd.ExcelWriter(output_file_stats, engine='openpyxl')

    comparison_df.reset_index().to_excel(writer1, sheet_name=ws_label, index=False)
    stat_df.to_excel(writer2, sheet_name=ws_label, index=False)

    print(f"✅ Wetterjahr {ws_label} fertig.")

writer1.close()
writer2.close()

# =========================
# 4. Durchschnitt über WS1–WS36
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

stat_avg_df = (
    comparison_avg_df
    .groupby(['ShapeType', 'Tech_Abb'])['delta_stunden_avg']
    .mean()
    .reset_index()
    .round({'delta_stunden_avg': 1})
)

# =========================
# 6. Export Durchschnittsergebnisse
# =========================
with pd.ExcelWriter(output_file_avg) as writer3:
    comparison_avg_df.reset_index().to_excel(writer3, sheet_name="AVG", index=False)

with pd.ExcelWriter(output_file_stats_avg) as writer4:
    stat_avg_df.to_excel(writer4, sheet_name="AVG", index=False)

print(f"📊 Export aller Detaildaten pro WS: {output_file_years}")
print(f"📈 Export aller Statistik pro WS: {output_file_stats}")
print(f"📊 Export Vergleich 2016 vs. Durchschnitt: {output_file_avg}")
print(f"📈 Export Statistik 2016 vs. Durchschnitt: {output_file_stats_avg}")

# =========================
# 📊 Boxplots erstellen
# =========================
plot_dir = os.path.join(out_dir, "plots_boxplots")
os.makedirs(plot_dir, exist_ok=True)

# Wetterjahre-Matrix vorbereiten
weather_matrix = pd.concat(weather_year_values, axis=1)
# Safety: nur 36 Spalten übernehmen
weather_matrix = weather_matrix.iloc[:, :36]
weather_matrix.columns = [f"WS{i}" for i in range(1, 37)]

vollast_2016 = base_df['vollaststunden_2016']

group_info = base_df[['Tech_Abb', 'ShapeType']].copy()
group_info['ShapeType'] = group_info['ShapeType'].fillna('NoShape')

# Gruppieren nach Tech_Abb / ShapeType
groups = []
for (tech, shape), idx in group_info.groupby(['Tech_Abb', 'ShapeType']).groups.items():
    vals = weather_matrix.loc[idx].values.flatten()
    vals = vals[~np.isnan(vals)]
    if vals.size == 0:
        continue
    groups.append((tech, shape, idx))

if not groups:
    raise RuntimeError("Keine Gruppen mit Daten gefunden.")

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
    hist_means.append(np.mean(all_vals))

n = len(box_data)
fig_w = max(10, n * 1.2)
plt.figure(figsize=(fig_w, 6))
bp = plt.boxplot(box_data, vert=True, patch_artist=True, showfliers=True)

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
plt.ylabel("Vollaststunden")
plt.xlabel("Kombination (ShapeType / Tech_Abb)")
plt.title("Verteilung Vollaststunden (WS1–WS36)\nmit 2016 (rot) & historischem Mittelwert (grün)")
plt.grid(axis='y', alpha=0.3)
plt.legend(loc='upper right')
plt.tight_layout()

outfile = os.path.join(plot_dir, "boxplot_alle_kombis.png")
plt.savefig(outfile, dpi=300)
plt.close()

print(f"📊 Boxplot aller Kombis exportiert: {outfile}")

# =========================
# 📊 Regionale Boxplots
# =========================
plot_dir_regions = os.path.join(out_dir, "plots_boxplots_by_region")
os.makedirs(plot_dir_regions, exist_ok=True)

group_info = base_df[['Tech_Abb', 'ShapeType', 'Region']].copy()
group_info['ShapeType'] = group_info['ShapeType'].fillna('NoShape')

regionen = group_info['Region'].dropna().unique()

for region in regionen:
    region_idx = group_info[group_info['Region'] == region].index
    if len(region_idx) == 0:
        continue

    region_groups = []
    for (tech, shape), idx in group_info.loc[region_idx].groupby(['Tech_Abb', 'ShapeType']).groups.items():
        vals = weather_matrix.loc[idx].values.flatten()
        vals = vals[~np.isnan(vals)]
        if vals.size == 0:
            continue
        region_groups.append((tech, shape, idx))

    if not region_groups:
        continue

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

    n = len(box_data)
    fig_w = max(10, n * 1.2)
    plt.figure(figsize=(fig_w, 6))

    bp = plt.boxplot(box_data, vert=True, patch_artist=True, showfliers=True)

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
    plt.ylabel("Vollaststunden")
    plt.xlabel("Kombination (ShapeType / Tech_Abb)")
    plt.title(f"Region: {region}\nVerteilung Vollaststunden (WS1–WS36)")
    plt.grid(axis='y', alpha=0.3)
    plt.legend()
    plt.tight_layout()

    safe_region = str(region).replace("/", "_").replace(" ", "_")
    filepath = os.path.join(plot_dir_regions, f"boxplot_{safe_region}.png")
    plt.savefig(filepath, dpi=300)
    plt.close()

    print(f"📊 Boxplot für Region '{region}' exportiert: {filepath}")

print("✅ Alle regionalen Boxplots erfolgreich erstellt!")
