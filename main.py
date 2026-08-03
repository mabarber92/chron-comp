from chron_comp.pairwise_chron_data import pairwiseChronData
from chron_comp.pairwise_chron_stats import pairwiseChronStats

if __name__ == "__main__":

    # text_1 = "data/texts/0677IbnMuyassar.AkhbarMisr.Kraken210528115855-ara1.mARkdown.dates_tagged"
    # text_2 = "data/texts/0845Maqrizi.ItticazHunafa.Shamela0000176-ara1.mARkdown.dates_tagged"
    # passim_tsv = "data/passim_data/Shamela0000176-ara1.mARkdown_Kraken210528115855-ara1.mARkdown.csv"
    # date_obj = pairwiseChronData(text_1, text_2, passim_tsv=passim_tsv)
    
    date_pairs = pairwiseChronStats()

    print(date_pairs.measure_passim_alignment_b2())
    
    # print(date_pairs.compare_year_length(years = [455, 600]))
    # similar = date_pairs.id_similar_year_lens()
    # diff = date_pairs.id_similar_year_lens(return_diff_years=True)
    # print(similar)
    # print(diff)
