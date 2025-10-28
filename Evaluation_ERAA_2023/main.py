from Evaluation3 import Evaluation

def main():

    eval = Evaluation("config.yaml")
    eval.generate_parquet_files()  # Nur Parquet erstellen
    eval.calculate_profitability()  # Nur Profitabilität berechnen


if __name__ == "__main__":
    main()
