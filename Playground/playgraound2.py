import pandas as pd

df = pd.read_csv(r"C:\Users\ahmed\Downloads\opsd-ninja_pv_wind_profiles-2020-09-16\opsd-ninja_pv_wind_profiles-2020-09-16\ninja_pv_wind_profiles_singleindex.csv")

df_wind_on = df[['DE_wind_national_near-termfuture', 'DE_wind_national_long-termfuture']]
start_year = 1980
end_year = 2019
years = list(range(start_year, end_year + 1))

# 8760 hours for all years
hours_per_year = 8760

# Original columns
cols = df_wind_on.columns  # ['DE_wind_onshore_current', 'DE_wind_onshore_near-termfuture']

for col in cols:
    data = df_wind_on[col].values
    offset = 0
    year_data = {}

    for y in years:
        # Check if leap year and trim extra hours
        n = 8784 if (y % 4 == 0 and (y % 100 != 0 or y % 400 == 0)) else 8760
        year_values = data[offset:offset + n]
        offset += n

        # Trim to 8760 hours if leap year
        year_data[y] = year_values[:hours_per_year]

    # Convert to DataFrame (years as columns)
    yearly_df = pd.DataFrame({str(y): year_data[y] for y in years})

    # Export to CSV
    output_path = fr"C:\Users\ahmed\Downloads\{col}_yearly.csv"
    yearly_df.to_csv(output_path, index=False)

    print(f"✅ Exported {col} to {output_path}")

df_ninja = pd.read_csv(r"C:\Users\ahmed\Downloads\DE_wind_national_long-termfuture_yearly.csv")
df_era = pd.read_csv(r"C:\Users\ahmed\Desktop\Data_pfad\2023\unavailability_files_plus_special\wind_on_2033_Germany_shape_a.csv")

#new_header = df_era.iloc[9]

# Drop all rows up to and including 9
#df_era = df_era[10:]

# Set the new header
#df_era.columns = new_header

# Reset the index (optional, but often useful)
#df_era = df_era.reset_index(drop=True)
df_era = df_era.drop(df_era.columns[:2], axis=1)
df_era = 1-df_era
#df_era.columns = df_era.columns.astype(int)
#df_era.columns = df_era.columns.astype(str)
df_ninja = df_ninja.drop(df_ninja.columns[:2], axis=1)

import pandas as pd
import matplotlib.pyplot as plt

# -------------------------------------------------
# 1. YEARLY ANALYSIS
# -------------------------------------------------

# Yearly mean & median
mean_era = df_era.mean()
mean_ninja = df_ninja.mean()

median_era = df_era.median()
median_ninja = df_ninja.median()

# Yearly Volllaststunden
vls_era = df_era.sum()
vls_ninja = df_ninja.sum()

# Yearly differences
diff_mean = mean_era - mean_ninja
diff_median = median_era - median_ninja
diff_vls = vls_era - vls_ninja

# Yearly comparison table
df_yearly = pd.DataFrame({
    'mean_era': mean_era,
    'mean_ninja': mean_ninja,
    'diff_mean': diff_mean,
    'median_era': median_era,
    'median_ninja': median_ninja,
    'diff_median': diff_median,
    'vls_era': vls_era,
    'vls_ninja': vls_ninja,
    'diff_vls': diff_vls
}).sort_index()

# -------------------------------------------------
# 2. GENERAL (GLOBAL) ANALYSIS
# -------------------------------------------------

# Flatten all values for global stats
era_all_values = df_era.values.flatten()
ninja_all_values = df_ninja.values.flatten()

general_stats = {
    'mean_era_total': era_all_values.mean(),
    'mean_ninja_total': ninja_all_values.mean(),
    'median_era_total': pd.Series(era_all_values).median(),
    'median_ninja_total': pd.Series(ninja_all_values).median(),
    'total_vls_era': vls_era.sum(),
    'total_vls_ninja': vls_ninja.sum(),
    'avg_vls_era': vls_era.mean(),
    'avg_vls_ninja': vls_ninja.mean(),
    'diff_mean_total': era_all_values.mean() - ninja_all_values.mean(),
    'diff_median_total': pd.Series(era_all_values).median() - pd.Series(ninja_all_values).median(),
    'diff_total_vls': vls_era.sum() - vls_ninja.sum(),
    'diff_avg_vls': vls_era.mean() - vls_ninja.mean()
}

df_general = pd.DataFrame.from_dict(general_stats, orient='index', columns=['value'])

# -------------------------------------------------
# 3. EXPORT RESULTS TO EXCEL
# -------------------------------------------------

output_path = r"C:\Users\ahmed\Downloads\weather_comparison_ty_2033.xlsx"

with pd.ExcelWriter(output_path) as writer:
    df_yearly.to_excel(writer, sheet_name="Yearly_Comparison")
    df_general.to_excel(writer, sheet_name="General_Comparison")
    df_era.describe().to_excel(writer, sheet_name="ERA_Stats")
    df_ninja.describe().to_excel(writer, sheet_name="Ninja_Stats")

print(f"✅ Excel file exported to: {output_path}")

# -------------------------------------------------
# 4. VISUALIZATION
# -------------------------------------------------

plt.style.use('seaborn-v0_8-darkgrid')

# --- Plot 1: Volllaststunden yearly ---
plt.figure(figsize=(12, 6))
plt.plot(df_yearly.index, df_yearly['vls_era'], label='ERA', marker='o')
plt.plot(df_yearly.index, df_yearly['vls_ninja'], label='NINJA', marker='o')
plt.title('Volllaststunden per Year (ERA vs NINJA)', fontsize=14)
plt.xlabel('Year')
plt.ylabel('Volllaststunden')
plt.legend()
plt.tight_layout()
plt.show()

# --- Plot 2: Difference in Volllaststunden ---
plt.figure(figsize=(12, 6))
plt.bar(df_yearly.index, df_yearly['diff_vls'])
plt.axhline(0, color='black', linewidth=1)
plt.title('Δ Volllaststunden (ERA - NINJA)', fontsize=14)
plt.xlabel('Year')
plt.ylabel('Difference in Volllaststunden')
plt.tight_layout()
plt.show()

# --- Plot 3: Yearly mean ---
plt.figure(figsize=(12, 6))
plt.plot(df_yearly.index, df_yearly['mean_era'], label='Mean ERA', marker='o')
plt.plot(df_yearly.index, df_yearly['mean_ninja'], label='Mean NINJA', marker='o')
plt.title('Mean Value per Year', fontsize=14)
plt.xlabel('Year')
plt.ylabel('Mean Value')
plt.legend()
plt.tight_layout()
plt.show()

# --- Plot 4: Yearly median ---
plt.figure(figsize=(12, 6))
plt.plot(df_yearly.index, df_yearly['median_era'], label='Median ERA', marker='o')
plt.plot(df_yearly.index, df_yearly['median_ninja'], label='Median NINJA', marker='o')
plt.title('Median Value per Year', fontsize=14)
plt.xlabel('Year')
plt.ylabel('Median Value')
plt.legend()
plt.tight_layout()
plt.show()

# -------------------------------------------------
# 5. GENERAL COMPARISON OUTPUT
# -------------------------------------------------

print("📊 General Comparison Results:")
print(df_general)

print("\n✅ All calculations, Excel export, and plots completed successfully.")


print('a')