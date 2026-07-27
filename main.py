
from chron_comp.pairwise_chron_stats import pairwiseChronStats

if __name__ == "__main__":
    date_pairs = pairwiseChronStats()
    print(date_pairs.unique_years())
    print(date_pairs.compare_year_length())