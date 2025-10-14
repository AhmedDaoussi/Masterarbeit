from preprocess import Preprocess

def main():
    pre = Preprocess("config.yaml")
    pre.generate_weather_year_files()

if __name__ == "__main__":
    main()


