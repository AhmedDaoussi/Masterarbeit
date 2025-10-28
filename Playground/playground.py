import os
import pandas as pd

def load_existing_parquets(results_path, years):
    """
    Lädt alle REG- und KW-Parquet-Dateien aus den angegebenen Jahren,
    merged sie mit dem Mapping und berechnet Annual_Profit/installed_kw pro KWID & Jahr.
    """
    all_reg_dfs = []
    all_kw_dfs = []

    for year in years:
        reg_dir = os.path.join(results_path, str(year), "reg")
        kw_dir = os.path.join(results_path, str(year), "kw")

        # --- REG ---
        if os.path.exists(reg_dir):
            reg_files = [os.path.join(reg_dir, f) for f in os.listdir(reg_dir) if f.endswith(".parquet")]
            if reg_files:
                reg_df = pd.concat(
                    (pd.read_parquet(f, columns=["REGID", "PKTNR", "JAHR", "FINAL_MARKTPREIS"]) for f in reg_files),
                    ignore_index=True
                ).astype({
                    "REGID": "int32",
                    "PKTNR": "int32",
                    "JAHR": "int32",
                    "FINAL_MARKTPREIS": "float32"
                })
                all_reg_dfs.append(reg_df)
                print(f"📥 REG {year}: {len(reg_df):,} Zeilen geladen")
        else:
            print(f"⚠️ REG-Verzeichnis für {year} nicht gefunden.")

        # --- KW ---
        if os.path.exists(kw_dir):
            kw_files = [os.path.join(kw_dir, f) for f in os.listdir(kw_dir) if f.endswith(".parquet")]
            if kw_files:
                kw_df = pd.concat(
                    (pd.read_parquet(f, columns=["KWID", "PKTNR", "JAHR", "PINSTALL", "EINSATZ", "VARKOSTEN"]) for f in kw_files),
                    ignore_index=True
                ).astype({
                    "KWID": "int32",
                    "PKTNR": "int32",
                    "JAHR": "int32",
                    "PINSTALL": "float32",   # besser float für Berechnungen
                    "EINSATZ": "float32",
                    "VARKOSTEN": "float32"
                })
                all_kw_dfs.append(kw_df)
                print(f"⚡ KW {year}: {len(kw_df):,} Zeilen geladen")
        else:
            print(f"⚠️ KW-Verzeichnis für {year} nicht gefunden.")

    # Gesamtdaten zusammenführen
    reg_df = pd.concat(all_reg_dfs, ignore_index=True) if all_reg_dfs else pd.DataFrame()
    kw_df = pd.concat(all_kw_dfs, ignore_index=True) if all_kw_dfs else pd.DataFrame()

    # 📎 Mapping laden
    mapping = pd.read_excel(r"C:\Users\ahmed\Desktop\Data_pfad\2023\helping_files\kwid_reg_mapping.xlsx")

    print(f"✅ Gesamt REG: {len(reg_df):,} Zeilen")
    print(f"✅ Gesamt KW:  {len(kw_df):,} Zeilen")

    # 🔸 KWID-Differenzen analysieren
    mapping_kwids = set(mapping['KWID'].unique())
    kw_kwids = set(kw_df['KWID'].unique())

    only_in_mapping = mapping_kwids - kw_kwids
    only_in_kw = kw_kwids - mapping_kwids

    print(f"✅ KWIDs nur in mapping (nicht in kw_df): {len(only_in_mapping)}")
    print(sorted(only_in_mapping))
    print(f"✅ KWIDs nur in kw_df (nicht in mapping): {len(only_in_kw)}")
    print(sorted(only_in_kw))

    # 📊 Zeilenanzahl pro KWID (Bericht)
    kwid_row_count_df = (
        kw_df
        .groupby('KWID')
        .size()
        .reset_index(name='Anzahl_Zeilen')
        .sort_values(by='Anzahl_Zeilen', ascending=False)
    )

    # 🧭 KWID → REGID hinzufügen
    kw_df = pd.merge(kw_df, mapping[['KWID', 'REGID']], on='KWID')

    # 🧮 Merge KW & REG
    merged = pd.merge(kw_df, reg_df, on=["REGID", "PKTNR", "JAHR"])
    ger_df = merged[(merged['PKTNR'] == 1) & (merged['JAHR'] == 2023) & (merged['REGID'] == 1) & (merged['KWID'] == 4748)]
    # 💰 Profitabilität berechnen
    merged['Deckungsbeitrag_hr'] = (merged['FINAL_MARKTPREIS'] + merged['VARKOSTEN']) * merged['EINSATZ']

    result_list = []
    for (year, kwid), group in merged.groupby(['JAHR', 'KWID']):
        pinstall_mean = group['PINSTALL'].mean()
        if pinstall_mean > 0:
            denominator = pinstall_mean * 1000
            if pd.notna(denominator) and denominator != 0:
                average_profit = round(group['Deckungsbeitrag_hr'].sum() / denominator,4)
            else:
                average_profit = 0
        else:
            average_profit = 'PINSTALL = 0'  # Markiere KWIDs mit 0 installierter Leistung
        result_list.append({
            'JAHR': year,
            'KWID': kwid,
            'Annual_Profit/installed_kw': average_profit
        })

    profit_df = pd.DataFrame(result_list)
    ger_df_2 = profit_df[
        (profit_df['PKTNR'] == 1) & (profit_df['JAHR'] == 2023) & (profit_df['REGID'] == 1) & (profit_df['KWID'] == 4748)]
    print("📊 Profitabilitätsübersicht:")
    print(profit_df)

    return reg_df, kw_df, profit_df


# -----------------------------------------
# 🧪 Anwendung:
results_path = r"C:\Users\ahmed\Desktop\Data_pfad\2023\ltmp_rech\results"
years = [1987]

reg_df, kw_df, profit_df = load_existing_parquets(results_path, years)
