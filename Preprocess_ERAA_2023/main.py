from preprocess import Preprocess

def main():
    pre = Preprocess("config.yaml")
    pre.filter_relevant_files()
    pre.process_unavailability_files()
    pre.calculate_special_region_files()
    pre.generate_shape_b_files()
    pre.generate_weather_year_files()

if __name__ == "__main__":
    main()


