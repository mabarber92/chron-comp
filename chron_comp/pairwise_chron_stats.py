from chron_comp.pairwise_chron_data import pairwiseChronData
import pandas as pd

class pairwiseChronStats():
    def __init__ (self, b1_path=None, b2_path=None, chron_data=None, passim_tsv=None, chron_sort=True):
        """On initialisation if default parameters are used then the pairwiseChronData will try to load from temp
        chron_data: can be used to direct the function to a specfic chron data folder (instead of the temp)
        chron_sort: if true, set b1 to earlier book and b2 to the later of the two books (sorted by id - assuming id is a URI)"""
        self.chron_data = pairwiseChronData(b1_path, b2_path, chron_data, passim_tsv)
        
        # Init base values used for comparison
        self.init_b1_b2(chron_sort=chron_sort)
        self.len_diff_data = None
        if passim_tsv is not None:
            self.passim_dataset = True
        else:
            self.passim_dataset = False
        

    def init_b1_b2(self, chron_sort=True):
        """set b1 and b2 - allowing for control of order of texts at comparison"""
        books = self.chron_data.books
        if chron_sort:
            books.sort()
        self.b1 = books[0]
        self.b2 = books[1]

        # initiate ids for passim data - crude - assumes id in the name
        self.b1_id = self._create_vers_id(self.b1)
        self.b2_id = self._create_vers_id(self.b2)

    def report_pipeline(self, out_dir, pipeline_stages = ["len_comp", "passim_comp", "tfidf_sim", "semantic_sim"]):
        """Run a full reporting pipeline - if data for specified pipeline stages not in the data object - then it will
        not run the pipeline stage"""

    def _create_vers_id(self, book_id):
        """split out the third part of a book_id - as the passim id (assumes a standard URI)"""
        return book_id.split(".")[3]

    def unique_years(self):
        """For the two texts return years that are found in one book but not the other
        NOTE: Written to be pairwise agnostic - could handle clusters later
        returns: dict where key is the book_id and value is a list of years
                {"book_id" : [] }"""
        book_years = self.chron_data.fetch_book_years()
        year_data = {}
        for book, years in book_years.items():
            for book2, years2 in book_years.items():
                if book2 == book:
                    continue
                else:
                    for year in years:
                        if year not in years2:
                            year_data.setdefault(book, []).append(year)
        
        return year_data

    def _select_and_measure(self, text_data, book_name):
        """Helper func to select the relevant rows of the df for the book and produce summary data
        text_data: list of dicts containing section data (instance and text in section)
        book_name: b1 or b2 id used to select the data
        returns: 
        total_len - total length of sections in filtered data
        sect_count - total number of sections for the book_name"""
        total_len = 0
        instance_list = []
        for row in text_data:
            if row["book"] == book_name:
                total_len += len(row["text"])
                instance_list.append(row["instance"])
        
        if len(instance_list) == 0:
            instance_list = [0]
            
        return total_len, max(instance_list)

    # Length-related comparison tools

    def compare_year_length(self, clean=True, count_tokens=True, years=[]):
        """compare the lengths of the sections of the chronicles yearwise. If multiple sections belong to 
        the same year concatenate the lengths. b1_sect and b2_sect in output record count of sections where the year is found
        clean: apply openiti text cleaner prior to measuring
        count_tokens: split the text into tokens, using openiti func, if false count chars
        years: specify the years for comparison - returns a list relating to on those years
        char/token diff calculated as b2 - b1 (assuming b1 is the earlier text)
        stores result as an internal object self.len_comp - to avoid recalculation if used for later analysis
        returns: list of dict records (convertable to a df for export)
                [{"year": int, "b1": "", "b2": "", "b1_len": int, "b2_len": int, "b1_sect": int, "b2_sect": int, "len_diff": int}]"""
        
        if len(years) == 0:
            years = self.chron_data.fetch_year_list()
        years.sort()

        diff_data = []

        for year in years:
            text_data = self.chron_data.fetch_year_text(year, clean=clean, return_tokens=count_tokens)
            if len(text_data) > 0:
                b1_len, b1_sect = self._select_and_measure(text_data, self.b1)
                b2_len, b2_sect = self._select_and_measure(text_data, self.b2)
                diff = b2_len - b1_len
            else:
                b1_len = 0
                b2_len = 0
                b1_sect = 0
                b2_sect = 0
                diff = 0

            out_dict = {
                "year": year,
                "b1": self.b1,
                "b2": self.b2,
                "b1_len": b1_len,
                "b2_len": b2_len,
                "b1_sect": b1_sect,
                "b2_sect": b2_sect,
                "len_diff": diff
            }
            diff_data.append(out_dict)
        
        self.len_diff_data = diff_data
        return diff_data
        
    # def id_similar_year_lens(self, )

    # Passim comparison tools

    # How much is each year aligned - split according to alignment with same year or not



