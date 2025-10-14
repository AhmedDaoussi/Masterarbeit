import pandas as pd

# 📥 Dateien laden
old1 = pd.read_csv(r"D:\Masterarbeit\Weather_Year_Files\1982\WeatherYear_1982.csv")
old2 = pd.read_csv(r"D:\Masterarbeit\Weather_Year_Files\1982\WeatherYear_1982_beta.csv")
new = pd.read_csv(r"C:\Users\ahmed\Desktop\Data_pfad\2023\Weather_Year_Files\1982\WeatherYear_1982.csv")

# 🔹 Alte Dateien zusammenführen & Duplikate entfernen
old = pd.concat([old1, old2], ignore_index=True).drop_duplicates()
new = new.drop_duplicates()

# 📌 Dein Dictionary
kw_dict = {4832: 'pv_2033_DE00', 4866: 'pv_2033_BT', 4852: 'pv_2033_TR00', 4857: 'pv_2033_BA', 4823: 'pv_2033_FR00', 4802: 'pv_2033_BE00', 4819: 'pv_2033_AT00', 4806: 'pv_2033_CH00', 4855: 'pv_2033_NL00', 4878: 'pv_2033_PL00', 4817: 'pv_2033_CZ00', 4824: 'pv_2033_DKW1', 4827: 'pv_2033_DKE1', 4848: 'pv_2033_SC', 4845: 'pv_2033_SE01', 3678: 'pv_2033_ITCN', 4861: 'pv_2033_UK00', 4865: 'pv_2033_ITN1', 4805: 'csp_2033_ES00', 4803: 'pv_2033_ES00', 4809: 'pv_2033_RO00', 4833: 'pv_2033_SK00', 4872: 'pv_2033_HU00', 4797: 'pv_2033_BG00', 4838: 'pv_2033_GR00', 4812: 'pv_2033_PT00', 4869: 'pv_2033_NO', 4875: 'pv_2033_FI00', 3295: 'pv_2033_ITCS', 4839: 'pv_2033_SE03', 4843: 'pv_2033_SE04', 3675: 'pv_2033_ITS1', 4863: 'pv_2033_ITSI', 2923: 'pv_2033_ITSA', 663: 'pv_2033_ITCA', 4748: 'wind_on_2033_DE00_shape_a', 4782: 'wind_on_2033_BT_shape_a', 4767: 'wind_on_2033_TR00_shape_a', 4773: 'wind_on_2033_BA_shape_a', 4739: 'wind_on_2033_FR00_shape_a', 4716: 'wind_on_2033_BE00_shape_a', 4734: 'wind_on_2033_AT00_shape_a', 4722: 'wind_on_2033_CH00_shape_a', 4770: 'wind_on_2033_NL00_shape_a', 4796: 'wind_on_2033_PL00_shape_a', 4731: 'wind_on_2033_CZ00_shape_a', 4740: 'wind_on_2033_DKW1_shape_a', 4743: 'wind_on_2033_DKE1_shape_a', 4764: 'wind_on_2033_SC_shape_a', 4761: 'wind_on_2033_SE01_shape_a', 4715: 'wind_on_2033_ITCN_shape_a', 4776: 'wind_on_2033_UK00_shape_a', 4781: 'wind_on_2033_ITN1_shape_a', 4721: 'wind_on_2033_ES00_shape_a', 4725: 'wind_on_2033_RO00_shape_a', 4749: 'wind_on_2033_SK00_shape_a', 4788: 'wind_on_2033_HU00_shape_a', 4713: 'wind_on_2033_BG00_shape_a', 4752: 'wind_on_2033_GR00_shape_a', 4730: 'wind_on_2033_PT00_shape_a', 4785: 'wind_on_2033_NO_shape_a', 4791: 'wind_on_2033_FI00_shape_a', 4719: 'wind_on_2033_ITCS_shape_a', 4755: 'wind_on_2033_SE03_shape_a', 4758: 'wind_on_2033_SE04_shape_a', 4726: 'wind_on_2033_ITSI_shape_a', 4723: 'wind_on_2033_ITS1_shape_a', 4728: 'wind_on_2033_ITSA_shape_a', 679: 'wind_on_2033_ITCA_shape_a', 4718: 'wind_on_2033_ITCN_shape_b', 4714: 'wind_on_2033_ITN1_shape_b', 4720: 'wind_on_2033_ITCS_shape_b', 4724: 'wind_on_2033_ITS1_shape_b', 4727: 'wind_on_2033_ITSI_shape_b', 4729: 'wind_on_2033_ITSA_shape_b', 1289: 'wind_on_2033_ITCA_shape_b', 4732: 'wind_on_2033_DE00_shape_b', 4733: 'wind_on_2033_BT_shape_b', 4735: 'wind_on_2033_TR00_shape_b', 4736: 'wind_on_2033_BA_shape_b', 4737: 'wind_on_2033_FR00_shape_b', 4742: 'wind_on_2033_BE00_shape_b', 4745: 'wind_on_2033_AT00_shape_b', 4747: 'wind_on_2033_CH00_shape_b', 4750: 'wind_on_2033_NL00_shape_b', 4751: 'wind_on_2033_PL00_shape_b', 4753: 'wind_on_2033_CZ00_shape_b', 4754: 'wind_on_2033_DKW1_shape_b', 4756: 'wind_on_2033_DKE1_shape_b', 4760: 'wind_on_2033_SC_shape_b', 4762: 'wind_on_2033_SE01_shape_b', 4763: 'wind_on_2033_UK00_shape_b', 4765: 'wind_on_2033_ES00_shape_b', 4766: 'wind_on_2033_RO00_shape_b', 4768: 'wind_on_2033_SK00_shape_b', 4769: 'wind_on_2033_HU00_shape_b', 4772: 'wind_on_2033_BG00_shape_b', 4774: 'wind_on_2033_GR00_shape_b', 4775: 'wind_on_2033_PT00_shape_b', 4778: 'wind_on_2033_NO_shape_b', 4779: 'wind_on_2033_FI00_shape_b', 4780: 'wind_on_2033_SE03_shape_b', 4783: 'wind_on_2033_SE04_shape_b', 4746: 'wind_off_2033_DE00_shape_a', 4738: 'wind_off_2033_FR00_shape_a', 4717: 'wind_off_2033_BE00_shape_a', 4771: 'wind_off_2033_NL00_shape_a', 4741: 'wind_off_2033_DKW1_shape_a', 4744: 'wind_off_2033_DKE1_shape_a', 4777: 'wind_off_2033_UK00_shape_a', 4759: 'wind_off_2033_SE04_shape_a', 4757: 'wind_off_2033_SE03_shape_a', 4794: 'wind_off_2033_PL00_shape_a', 4784: 'wind_off_2033_DE00_shape_b', 4786: 'wind_off_2033_UK00_shape_b', 64: 'wind_off_2033_FI00_shape_a', 275: 'wind_off_2033_BT_shape_a', 1639: 'wind_off_2033_NO_shape_a', 955: 'wind_off_2033_ES00_shape_a', 1830: 'wind_off_2033_PT00_shape_a', 1646: 'wind_off_2033_ITS1_shape_a', 1642: 'wind_off_2033_ITSI_shape_a'}

# 🧭 Shape-B → Shape-A Paare finden (robust)
swap_map = {}
normalized_dict = {v.strip().lower(): k for k, v in kw_dict.items()}

for k_id, name in kw_dict.items():
    norm = name.strip().lower()
    if "_shape_a" in norm:
        b_norm = norm.replace("_shape_a", "_shape_b")
        b_id = normalized_dict.get(b_norm)
        if b_id is not None:
            swap_map[k_id] = b_id
            swap_map[b_id] = k_id

print(f"🔄 Anzahl Shape-A/B Paare für Swap: {len(swap_map) // 2}")

# 🧮 Vergleichsfunktion
def compare_dfs(df_old, df_new):
    matching, different = [], []
    only_in_old = set(df_old["KWID"].unique()) - set(df_new["KWID"].unique())
    only_in_new = set(df_new["KWID"].unique()) - set(df_old["KWID"].unique())
    common = set(df_old["KWID"].unique()) & set(df_new["KWID"].unique())

    for kwid in common:
        o = df_old[df_old["KWID"] == kwid].sort_index().reset_index(drop=True)
        n = df_new[df_new["KWID"] == kwid].sort_index().reset_index(drop=True)
        if o.equals(n):
            matching.append(kwid)
        else:
            different.append(kwid)
    return matching, different, only_in_old, only_in_new

# 🧪 1. Vergleich: Original
match_orig, diff_orig, only_old_orig, only_new_orig = compare_dfs(old, new)

# 🧭 2. ECHTER Swap für Shape-A/B IDs
swapped_old = old.copy()
swapped_old["KWID"] = swapped_old["KWID"].apply(lambda x: swap_map.get(x, x))

# 🧪 2. Vergleich: Nach A↔B Swap
match_swap, diff_swap, only_old_swap, only_new_swap = compare_dfs(swapped_old, new)

# 📝 KWID-Namen Funktion
def kwid_name(kwid):
    return kw_dict.get(int(kwid), f"KWID_{kwid}_unbekannt")

# 👉 Hilfsfunktion zur Ausgabe
def print_results(title, matching, different, only_old, only_new):
    matching_names = [(k, kwid_name(k)) for k in matching]
    different_names = [(k, kwid_name(k)) for k in different]
    only_old_names = [(k, kwid_name(k)) for k in only_old]
    only_new_names = [(k, kwid_name(k)) for k in only_new]

    print(f"\n📊 --- {title} ---")
    print(f"✅ KWIDs mit identischen Zeilen: {len(matching)}")
    print(f"❌ KWIDs mit Unterschieden: {len(different)}")
    print(f"📉 KWIDs nur in OLD: {len(only_old)}")
    print(f"📈 KWIDs nur in NEW: {len(only_new)}")

    print("\n✅ Matching KWIDs (ID, Name):", matching_names[:])
    print("\n❌ Different KWIDs (ID, Name):", different_names[:])
    print("\n📉 Only in OLD (ID, Name):", only_old_names[:])
    print("\n📈 Only in NEW (ID, Name):", only_new_names[:])

# 🖨 Ausgabe: Vor Swap
print_results("Vergleich VOR A↔B Swap", match_orig, diff_orig, only_old_orig, only_new_orig)

# 🖨 Ausgabe: Nach Swap
print_results("Vergleich NACH A↔B Swap", match_swap, diff_swap, only_old_swap, only_new_swap)

pd.set_option("display.max_columns", None)
pd.set_option("display.width", 200)

# Alle beteiligten KWIDs sammeln
all_kwids = (
    set(match_orig) | set(diff_orig) | set(only_old_orig) | set(only_new_orig) |
    set(match_swap) | set(diff_swap) | set(only_old_swap) | set(only_new_swap)
)

def get_category(kwid, match, diff, only_old, only_new):
    if kwid in match: return "Match"
    if kwid in diff: return "Different"
    if kwid in only_old: return "Only in OLD"
    if kwid in only_new: return "Only in NEW"
    return "-"

# Reportzeilen bauen
rows = []
for kwid in sorted(all_kwids):
    name_before = kwid_name(kwid)
    cat_before  = get_category(kwid, match_orig, diff_orig, only_old_orig, only_new_orig)

    kwid_after  = swap_map.get(kwid, kwid)
    name_after  = kwid_name(kwid_after)
    cat_after   = get_category(kwid_after, match_swap, diff_swap, only_old_swap, only_new_swap)

    rows.append({
        "KWID_before": kwid,
        "Name_before": name_before,
        "Category_before": cat_before,
        "KWID_after": kwid_after,
        "Name_after": name_after,
        "Category_after": cat_after,
    })

report_df = pd.DataFrame(rows)

# sinnvolle Sortierung
cat_order = pd.CategoricalDtype(["Match", "Different", "Only in OLD", "Only in NEW", "-"], ordered=True)
report_df["Category_before"] = report_df["Category_before"].astype(cat_order)
report_df["Category_after"]  = report_df["Category_after"].astype(cat_order)
report_df = report_df.sort_values(by=["Category_before", "KWID_before"]).reset_index(drop=True)

# Konsole: komplette Tabelle anzeigen (erste 100 Zeilen als Vorgeschmack)
print("\n📊 --- Detaillierter Ergebnis-Report ---")
print(report_df.head(100))

# =========================
# 💾 Kompakte, kompatible Exporte
# =========================

out_base = r"D:\Masterarbeit\Weather_Year_Files\1982"

# 1) Hauptreport mit Namen (CSV, UTF-8 mit BOM für Excel-Kompatibilität)
report_path = fr"{out_base}\Vergleich_Report.csv"
report_df.to_csv(report_path, index=False, encoding="utf-8-sig")
print(f"\n✅ Report gespeichert: {report_path}")

# 2) Nur die tatsächlich geswappten Paare (A↔B), dedupliziert
pairs = []
seen = set()
for a_id, b_id in swap_map.items():
    key = tuple(sorted((a_id, b_id)))
    if key in seen:
        continue
    seen.add(key)
    a_name = kwid_name(a_id)
    b_name = kwid_name(b_id)
    pairs.append({"A_KWID": a_id, "A_Name": a_name, "B_KWID": b_id, "B_Name": b_name})

pairs_df = pd.DataFrame(pairs).sort_values(by=["A_KWID", "B_KWID"])
pairs_path = fr"{out_base}\Vergleich_SwappedPairs.csv"
pairs_df.to_csv(pairs_path, index=False, encoding="utf-8-sig")
print(f"✅ Geswappte Paare gespeichert: {pairs_path}")

# 3) Listen für Missing-Fälle (nur IDs, aber mit Namen)
only_old_df = pd.DataFrame(
    sorted([(k, kwid_name(k)) for k in only_old_orig], key=lambda x: x[0]),
    columns=["KWID", "Name"]
)
only_new_df = pd.DataFrame(
    sorted([(k, kwid_name(k)) for k in only_new_orig], key=lambda x: x[0]),
    columns=["KWID", "Name"]
)
only_old_path = fr"{out_base}\Vergleich_OnlyInOld.csv"
only_new_path = fr"{out_base}\Vergleich_OnlyInNew.csv"
only_old_df.to_csv(only_old_path, index=False, encoding="utf-8-sig")
only_new_df.to_csv(only_new_path, index=False, encoding="utf-8-sig")
print(f"✅ Only-in-OLD gespeichert: {only_old_path}")
print(f"✅ Only-in-NEW gespeichert: {only_new_path}")

print('a')
