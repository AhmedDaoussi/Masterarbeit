import os
import pandas as pd
import matplotlib.pyplot as plt
region_mapping = {
    1: "Germany",
    2: "Baltics",
    3: "Turkey",
    4: "Balkans",
    5: "France",
    6: "Belgium",
    7: "Austria",
    8: "Switzerland",
    9: "Netherlands",
    10: "Poland",
    11: "Czech Republic",
    12: "DenmarkWest",
    13: "DenmarkEast",
    14: "SloCro",
    15: "SWE1and2",
    16: "IT_CN",
    17: "England",
    18: "IT_N",
    19: "Spain",
    20: "Romania",
    21: "Slovakia",
    22: "Hungary",
    23: "Bulgaria",
    24: "Greece",
    25: "Portugal",
    26: "Norway",
    27: "Finland",
    28: "IT_CS",
    29: "SWE3",
    30: "SWE4",
    31: "IT_S",
    32: "IT_SI",
    33: "IT_SA",
    34: "IT_CA"
}

def concatenate_and_process_yearly_data(folder_path, start_year, end_year):
    # Liste für DataFrames
    all_dataframes = []

    # Über die Jahre im angegebenen Bereich iterieren
    for year in range(start_year, end_year + 1):
        # Über alle Dateien im Ordner iterieren
        for file_name in os.listdir(folder_path):
            # Prüfen, ob die Datei dem Muster entspricht
            if f"RegResults_{year}_" in file_name and file_name.endswith('.dat'):
                file_path = os.path.join(folder_path, file_name)

                # Datei lesen
                df = pd.read_csv(file_path, delimiter=',', header=None)

                # Bearbeitung der Datei
                df1 = df.iloc[10:].reset_index(drop=True)
                column_names = ['VARID', 'REGID', 'SIMID', 'JAHR', 'ZENR', 'MARKTPREIS']
                df1 = pd.DataFrame([x.split(';') for x in df1[0]])

                # Sicherstellen, dass die Spaltenanzahl passt
                df2 = df1.iloc[:, :6].copy()
                df2.columns = column_names[:df2.shape[1]]

                # Daten zur Liste hinzufügen
                all_dataframes.append(df2)

    # Alle DataFrames zusammenfügen
    if all_dataframes:
        combined_df = pd.concat(all_dataframes, ignore_index=True)

        # Datentypen umwandeln
        combined_df['VARID'] = pd.to_numeric(combined_df['VARID'], errors='coerce')
        combined_df['JAHR'] = pd.to_numeric(combined_df['JAHR'], errors='coerce')
        combined_df['REGID'] = pd.to_numeric(combined_df['REGID'], errors='coerce')
        combined_df['ZENR'] = pd.to_numeric(combined_df['ZENR'], errors='coerce')
        combined_df['MARKTPREIS'] = pd.to_numeric(combined_df['MARKTPREIS'], errors='coerce')

        # Sortieren der Daten
        sorted_df = combined_df.sort_values(by=['JAHR', 'REGID', 'ZENR'], ascending=[True, True, True]).reset_index(drop=True)
        return sorted_df
    else:
        print(f"Keine Dateien für die Jahre {start_year} bis {end_year} gefunden.")
        return pd.DataFrame()  # Leerer DataFrame, falls keine Dateien gefunden werden


# Beispielaufruf
folder_path = 'C:/Users/ahmed/Desktop/ltmp_rech/1982/daoussi_Wetterjahr_ab/SQLLoader/regresults/'
start_year = 2023
end_year = 2026

result_df = concatenate_and_process_yearly_data(folder_path, start_year, end_year)
result_df['REGION_NAME'] = result_df['REGID'].map(region_mapping)

# Ergebnis anzeigen oder speichern
if not result_df.empty:
    print("Verarbeiteter kombinierter DataFrame:")
    print(result_df.head())  # Nur die ersten Zeilen anzeigen
else:
    print("Keine Daten zusammengefügt.")


import matplotlib.pyplot as plt



def analyze_and_plot(result_df, folder_path):
    # Sicherstellen, dass der Ordner existiert
    os.makedirs(folder_path, exist_ok=True)

    # Sicherstellen, dass JAHR und ZENR gültige Werte haben
    result_df = result_df[(result_df['JAHR'] > 1900) & (result_df['JAHR'] < 2100)]  # Filter für gültige Jahre
    result_df = result_df[result_df['ZENR'].between(1, 8760)]  # Stundenzahl im gültigen Bereich

    # Berechnung der DATETIME
    result_df['DATETIME'] = pd.to_datetime(
        result_df['JAHR'].astype(str) + '-01-01',  # 1. Januar des Jahres
        format='%Y-%m-%d'
    ) + pd.to_timedelta(result_df['ZENR'] - 1, unit='h')  # Stunden hinzufügen

    # Iteriere über alle REGIDs und Jahre
    for region in result_df['REGION_NAME'].unique():
        for jahr in result_df[result_df['REGION_NAME'] == region]['JAHR'].unique():
            # Filtere Daten für die aktuelle Region und das Jahr
            filtered_df = result_df[(result_df['REGION_NAME'] == region) & (result_df['JAHR'] == jahr)]

            # Überspringe, wenn keine Daten vorhanden
            if filtered_df.empty:
                continue

            region_name = f"Region_{region}"  # Optional, hier könnte ein Mapping für Region_Name verwendet werden

            # Aggregiere Daten für tägliche, wöchentliche, monatliche und jährliche Auflösungen
            resolutions = {
                'Daily': filtered_df.groupby(filtered_df['DATETIME'].dt.date)['MARKTPREIS'].mean(),
                'Weekly': filtered_df.groupby(filtered_df['DATETIME'].dt.to_period('W'))['MARKTPREIS'].mean(),
                'Monthly': filtered_df.groupby(filtered_df['DATETIME'].dt.to_period('M'))['MARKTPREIS'].mean()

            }

            # Erstelle Plots für jede Auflösung
            for res_name, data in resolutions.items():
                plt.figure(figsize=(10, 6))

                # Konvertiere PeriodIndex in Strings für Matplotlib-Kompatibilität
                if isinstance(data.index, pd.PeriodIndex):
                    data.index = data.index.astype(str)

                # Für wöchentliche Plots: Beschriftung mit "Woche N"
                if res_name == 'Weekly':
                    data.index = [f"{i + 1}" for i in range(len(data))]

                plt.plot(data.index, data.values,  label=f'MARKET_PRICES ({res_name})')
                plt.title(f'{res_name} MARKTPREIS ({region_name}, {jahr})')
                plt.xlabel(res_name)
                plt.ylabel('MARKET_PRICES')
                plt.grid(True)
                plt.legend()
                plt.xticks(rotation=90)
                plt.tight_layout()

                # Speichert den Plot im Ordner
                file_path = os.path.join(folder_path+ '/Auswertung', f'{region_name}_{jahr}_{res_name}MARKET_PRICES.png')
                plt.savefig(file_path)
                plt.close()
                plt.show()


            # Erstelle einen absteigenden Plot (Descending Plot)
            sorted_df = filtered_df.sort_values(by='FINAL_MARKTPREIS', ascending=False).reset_index()
            plt.figure(figsize=(10, 6))
            plt.plot(range(1, len(sorted_df) + 1), sorted_df['MARKTPREIS'], label='Descending MARKET_PRICES')
            plt.title(f'Descending MARKET_PRICES ({region_name}, {jahr})')
            plt.xlabel('Stundenzahl (1-8760)')
            plt.ylabel('MARKET_PRICES')
            plt.grid(True)
            plt.legend()
            plt.tight_layout()

            # Speichert den Plot im Ordner
            file_path = os.path.join(folder_path + '/Auswertung', f'{region_name}_{jahr}_Descending_MARKTE_PREICES.png')
            plt.savefig(file_path)
            plt.close()
            plt.show()


            # Erstelle eine Excel-Tabelle mit wichtigen Statistiken
    summary_stats = result_df.groupby('REGION_NAME').agg({
        'MARKTPREIS': ['mean', 'var', 'median', 'max', 'min']
    }).reset_index()

    # Region_Name und Jahr hinzufügen

    summary_stats['Jahr'] = year

    # Speichert die Statistiken in einer Excel-Datei
    excel_path = os.path.join(folder_path + '/Auswertung', f'_{year}_Summary_Statistics.xlsx')
    summary_stats.to_excel(excel_path )
    print(f"Excel-Tabelle für {year} wurde erstellt.")


# Beispielaufruf
analyze_and_plot(result_df, folder_path)


print(1)