
from chron_comp.pairwise_chron_stats import pairwiseChronStats

if __name__ == "__main__":
    date_pairs = pairwiseChronStats()
    
    print(date_pairs.compare_year_length(years = [455, 600]))
    similar = date_pairs.id_similar_year_lens()
    diff = date_pairs.id_similar_year_lens(return_diff_years=True)
    print(similar)
    print(diff)
