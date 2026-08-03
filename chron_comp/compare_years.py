from chron_comp.pairwise_chron_data import pairwiseChronData
import pandas as pd

class yearComparison():
    """Base class used for performing comparison on years. Other classes for specific types of comparison
    operate through this class."""
    def __init__(self, b1_path=None, b2_path=None, chron_data=None, passim_tsv=None, chron_sort=True):
        """On initialisation if default parameters are used then the pairwiseChronData will try to load from temp
        chron_data: can be used to direct the function to a specfic chron data folder (instead of the temp)
        chron_sort: if true, set b1 to earlier book and b2 to the later of the two books (sorted by id - assuming id is a URI)"""
        self.chron_data = pairwiseChronData(b1_path, b2_path, chron_data, passim_tsv)
        
        # Init base values used for comparison
        chron_data.init_b1_b2(chron_sort=chron_sort)
        self.len_diff_data = None