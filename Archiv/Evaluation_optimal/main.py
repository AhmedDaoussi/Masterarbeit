from Evaluation import Evaluation

def main():

    eval = Evaluation("config.yaml")
    eval.calculate_profitability()  # Nur Profitabilität berechnen


if __name__ == "__main__":
    main()
