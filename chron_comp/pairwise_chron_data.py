from chron_comp.config import TEMP_DIR, OVERWRITE
from openiti_utils.openitiTexts import openitiTextMs
import json
import pandas as pd
import re
from tqdm import tqdm
from openiti.helper.funcs import text_cleaner
from openiti.helper.ara import tokenize

import os

class pairwiseChronData():
    """Class for populating year-wise alignments between two texts as a data object
    further fields can be added to the class through update, based on processing of years"""
    def __init__(self, b1_path=None, b2_path=None, chron_data=None, passim_tsv=None):
        """b1_path, b2_path - paths to openITI mARkdown files to be used for populating data
                            if None, check temp for json to be used as data
        chron_data: a directory that contains the same json files as a temp folder and can be loaded instead"""
        
        # Init values
        if passim_tsv is not None:
            self.passim_key = "passim_offsets"
        else:
            self.passim_key = None

        # If a path to a chron_json is given - initialise object directly from that
        if chron_data is not None:
            self.data_dir = chron_data
        else:
            self.data_dir = TEMP_DIR


        # Create the temp paths
        self.chron_json = "chron_data.json"
        self.book_json = "book_data.json"
        self.undated_json = "undated_data.json"

        # Check if data has been populated already - and if we're allowed to overwrite it
        process_data = self.check_temp(b1_path, b2_path)

        # If we find we need to run the processes run them
        if process_data:
            self.create_chron_data(b1_path, b2_path, passim_tsv)
        
        # Else load the data from the temp
        else:
            self.load_from_temp()
    
    
    # Main processing funcs
    def create_chron_data(self, b1_path, b2_path, passim_tsv=None):
        self.chron_data = {}
        self.undated_data = {}

        b1_id, b2_id = self._create_bids(b1_path, b2_path)
        self.write_books_data(b1_path, b2_path)
        data_store = {}
        for path, bid in [[b1_path, b1_id], [b2_path, b2_id]]:

            data_store[bid] = self.process_book(path, bid)

        if passim_tsv is not None:
            # if we have passim data - use full tables to get date-wise passim links - adding that data to each row
            data_store = self.link_passim_data(data_store, passim_tsv, b1_path, b2_path)

        # Then parse the resulting data
        for bid in [b1_id, b2_id]:
            self.parse_book_data(data_store[bid], bid)

        # Once parsing is complete - write the temp files
        self.write_books_data(b1_path, b2_path)
        self.write_to_temp()
    
    def process_book(self, path, bid, passim_data=None):
        openiti_ms_obj = openitiTextMs(path, pre_process_ms=False)
        section_offsets = openiti_ms_obj.fetch_section_offsets_full(return_content=True)
        
        # Add dates and return full data
        section_offsets = self.fetch_dates(section_offsets)
        return section_offsets

    def fetch_dates(self, section_offsets, date_regex = r"@YY(\d{3})"):
        """Extract @YY-tagged years from each section's heading and content.
        Dates are normalised to int (rather than left as the raw regex match strings) so that
        they can be used consistently as chron_data keys and compared/sorted without
        further conversion downstream."""
        new_offsets = []
        for offset in section_offsets:
            heading_dates = [int(d) for d in re.findall(date_regex, offset["heading"])]
            # Use first case - pass remainder to 'dates'
            # If there is no date available we populate with 0
            if len(heading_dates) == 0:
                heading_dates = [0]
            offset["date"] = heading_dates[0]
            dates = [int(d) for d in re.findall(date_regex, offset["content"])]
            dates.extend(heading_dates)
            dates = list(set(dates))
            offset["dates"] = dates
            new_offsets.append(offset)
        return new_offsets


    
        

    def parse_book_data(self, offsets, book):
        """Use section offsets data for a book to populate the date-wise data
        returns: offset_data_lookup - a df used to transform passim offsets into pairwise
        comparison of dates"""

        for offset in tqdm(offsets):
            data = {"offset": offset["offset"], "offset_end": offset["offset_end"], "heading": offset["heading"], "content": offset["content"], "dates": offset["dates"]}
            if self.passim_key in offset.keys():
                data[self.passim_key] = offset[self.passim_key]

            # Sections with no resolvable @YY date go to undated_data - kept separate so
            # year-wise comparisons never have to special-case a fake "year 0" bucket
            if offset["date"] == 0:
                self.add_update_undated_data(book, data)
            else:
                self.add_update_chron_data(offset["date"], book, data)

    def _create_dir_cols(self, cols, data_dir):
        """Helper function that appends a number directly to the input columns e.g. cols = ['offset'] data_dir = 1, returns ['offset1']"""
        new_cols = []
        for col in cols:
            new_col = f"{col}{data_dir}"
            new_cols.append(new_col)
        return new_cols

    def _fetch_overlapping_offsets(self, df, start_col, end_col, start, end):
        """Find rows of df whose [start_col, end_col] range overlaps the given [start, end] range.
        True interval overlap (not a one-sided point-in-range check) so it's correct regardless
        of which range - the row's or the given one - happens to be the larger/containing one.
        df: incoming data with start_col/end_col to check for overlap
        start_col, end_col: column names holding each row's own range
        start, end: the range to check for overlap against
        returns: df filtered to rows whose range overlaps [start, end]"""
        mask = (df[start_col] <= end) & (df[end_col] >= start)
        return df[mask]

    def _map_date_to_offset(self, offset_df, dated_sections, data_dir):
        """Map the dates for section offsets to passim offsets. 
        offset_df : df of passim offsets
        dated_sections : sections of an openiti text with date data about them
        data_dir: the side of the passim offset data that the dated_sections corresponds to - 1 == start_offset1, 2 == start_offset2
        returns: offset_df with the corresponding dates added as a column, dates{data_dir} """

        # Convert offsets to list of dict to loop through
        data_dicts = offset_df.to_dict("records")

        # Create empty list for putting data back
        new_data_dicts = []

        # Transform dated_sections into df to facilitate lookups
        dated_sections = pd.DataFrame(dated_sections)

        for row in tqdm(data_dicts):
            corresponding_dates = self._fetch_overlapping_offsets(dated_sections, "offset", "offset_end", row[f"start_offset{data_dir}"], row[f"end_offset{data_dir}"])
            row[f"dates{data_dir}"] = corresponding_dates["date"].to_list()
            new_data_dicts.append(row)
        
        return pd.DataFrame(new_data_dicts)

    def _map_passim_to_data(self, data_dicts, passim_df, data_dir):
        
        
        # data cols - the columns to use for the passim data - if selection cols is 1 then data cols 2
        if data_dir == 1:
            data_col_dir = 2
        else:
            data_col_dir = 1
        base_cols = ["start_offset", "end_offset", "dates", "series_b"]
        data_cols = self._create_dir_cols(base_cols, data_col_dir)
        # Drop the numeral once selected - within a given entry's passim_offsets, "the other
        # book's data" is unambiguous from context, so the suffix would only add friction to querying
        rename_map = dict(zip(data_cols, base_cols))

        # Also keep this side's own matched sub-range - the section's top-level offset/offset_end
        # covers the whole section, not the specific slice this passim alignment actually covers.
        # "local" (this book) vs the unprefixed start_offset/end_offset above (the other, "remote" book)
        local_cols = [f"start_offset{data_dir}", f"end_offset{data_dir}"]
        local_rename = {f"start_offset{data_dir}": "local_start_offset", f"end_offset{data_dir}": "local_end_offset"}
        select_cols = data_cols + local_cols
        full_rename = {**rename_map, **local_rename}

        # Go row by row and fetch corresponding data
        new_data_dict = []
        for row in tqdm(data_dicts):
            filtered_df = self._fetch_overlapping_offsets(passim_df, f"start_offset{data_dir}", f"end_offset{data_dir}", row["offset"], row["offset_end"])
            passim_data = filtered_df[select_cols].rename(columns=full_rename).to_dict("records")
            row[self.passim_key] = passim_data
            new_data_dict.append(row)
        
        return new_data_dict


    def link_passim_data(self, data_store, passim_tsv, b1_path, b2_path):
        """Function to take book-wise offsets in a data_store and use them to create passim offsets with corresponding
        dates within the paired book"""

        # Load tsv
        df = pd.read_csv(passim_tsv, sep="\t")
        
        # Fetch corresponding b1 and b2 texts - a little fragile as it assumes text paths contain ids
        b1 = df["series_b1"].iloc[0]
        b2 = df["series_b2"].iloc[0]
        b1_text = None
        b2_text = None
        for path in [b1_path, b2_path]:
            if b1 in path:
                b1_text = path
            if b2 in path:
                b2_text = path
        
        # Check we've set both, if not throw an error
        if b1_text is None or b2_text is None:
            print("No corresponding text found for passim data in given paths. Do the paths contain an ID? Is the passim file correct?")
            print(f"passim b1: {b1}, passim b2: {b2}")
            print(f"path b1: {b1_path}, path b2: {b2_path}")
            exit()

        # Convert b1 to raw offsets
        # Prepare data
        df = df.rename(columns={"seq1": "ms", "b1": "start_offset", "e1": "end_offset"})
        dict_data = df.to_dict("records")

        # Load b1 OpenITI file and run full offsets - pass through all additional data in the df
        dict_data = openitiTextMs(b1_text, pre_process_ms=False).build_full_ms_offsets(dict_data)

        # Relabel data ( --> b2)
        df = pd.DataFrame(dict_data)
        df = df.rename(columns={"start_offset": "start_offset1", "end_offset": "end_offset1"})
        df = df.rename(columns={"seq2": "ms", "b2": "start_offset", "e2": "end_offset"})
        dict_data = df.to_dict("records")

        # Convert b2 data to raw offsets
        dict_data = openitiTextMs(b2_text, pre_process_ms=False).build_full_ms_offsets(dict_data)

        # Relabel b1 data
        df = pd.DataFrame(dict_data)
        df = df.rename(columns={"start_offset": "start_offset2", "end_offset": "end_offset2"})

        # map dates to the offsets using the data store
        for bid in data_store.keys():
            data_dir = self._resolve_data_dir(bid, b1_text, b2_text)
            df = self._map_date_to_offset(df, data_store[bid], data_dir=data_dir)


        # write out data to datastore
        for bid in data_store.keys():
            data_dir = self._resolve_data_dir(bid, b1_text, b2_text)
            data_store[bid] = self._map_passim_to_data(data_store[bid], df, data_dir)

        return data_store

    def _resolve_data_dir(self, bid, b1_path, b2_path):
        data_dir = None
        if bid in b1_path:
            data_dir = 1
        if bid in b2_path:
            data_dir = 2
        if data_dir is not None:
            return data_dir
        else:
            print(f"No corresponding path found for bid {bid} to determine direction")
            print(f"Paths: {b1_path}, {b2_path}")
            exit()

    
    def _next_instance_id(self, entries, book):
        """Shared instance-numbering/addressing logic used by both chron_data (year-keyed)
        and undated_data (book-keyed): given the dict of existing entries at this level and
        a book id, return the next (instance_number, entry_id) pair, e.g. (2, "IbnMuyassar.2")"""
        books = [key.split(".")[0] for key in entries.keys()]
        instance = books.count(book) + 1
        return instance, f"{book}.{instance}"

    def add_update_chron_data(self, date, book, data, instance=None):
        """Add a new row of data to self.chron_data
        date: year to which data belongs
        book: book from which data is derived
        data: a dictionary containing data to be added or updated
        instance: if None - see if entry for book exists and add a new instance if it does if set add given
                    data to instance"""

        # If instance is set - we perform an update on the data - throw an error if data mismatches
        if instance is not None:
            data_id = f"{book}.{instance}"
            if date in self.chron_data.keys():
                if data_id in self.chron_data[date].keys():
                    self.chron_data[date][data_id].update(data)
                else:
                    self._update_error(date, book, instance)
            else:
                self._update_error(date, book, instance)

        else:
            # If date is not there it's our first populated instance
            if not date in self.chron_data.keys():
                self.chron_data[date] = {}

            instance, data_id = self._next_instance_id(self.chron_data[date], book)
            data["instance"] = instance
            self.chron_data[date][data_id] = data

    def add_update_undated_data(self, book, data, instance=None):
        """Add a new row of data to self.undated_data - same book.N addressing as
        add_update_chron_data, but flat (no year level) since these sections have no
        resolvable @YY date to key on.
        book: book from which data is derived
        data: a dictionary containing data to be added or updated
        instance: if None - see if entry for book exists and add a new instance if it does if set add given
                    data to instance"""

        if instance is not None:
            data_id = f"{book}.{instance}"
            if data_id in self.undated_data.keys():
                self.undated_data[data_id].update(data)
            else:
                self._update_error("undated", book, instance)

        else:
            instance, data_id = self._next_instance_id(self.undated_data, book)
            data["instance"] = instance
            self.undated_data[data_id] = data

    def _update_error(self, date, book, instance):
        print(f"Could not identify corresponding data in object for date: {date}, instance_id: {book}.{instance}")
        print("Continue processing without update? Y/N")
        response = input()
        if response.upper() != "Y":
            exit()

    # Temp checking at init

    def check_temp(self, b1_path, b2_path):
        overwrite = OVERWRITE
        temp_files = os.listdir(self.data_dir)
        # If there are no temp files - return True - we need to run the init process
        # Note: create_chron_data always writes undated_json (even if empty), so a missing
        # file here means an incomplete/stale run rather than "no undated sections found"
        if self.chron_json not in temp_files or self.book_json not in temp_files or self.undated_json not in temp_files:
            overwrite = True
        if b1_path is None or b2_path is None:
            if self.chron_json not in temp_files:
                print("No available temp files: b1 and b2 paths must be specified")
                exit()
        elif not overwrite:
            # Only need to check whether the existing temp data matches these books if we
            # haven't already determined we need to reprocess (e.g. on a first-ever run,
            # book_data.json won't exist yet, so there's nothing to compare against)
            b1, b2 = self._create_bids(b1_path, b2_path)
            books_data = self.load_books_data()["books"]
            if b1 not in books_data or b2 not in books_data:
                overwrite = True
        return overwrite
    
    # Functions for querying the data object (in modular design, avoid querying the data dict directly in separate functions, prefer functions based here)
    
    def fetch_book_id(self, book_instance):
        """Convert a book_instance string into a book_id for use accross reference functions"""
        return ".".join(book_instance.split(".")[:-1])
    
    def fetch_year(self, year, book=None):
        """return all data for a given year
        year: int for requested date
        returns: dict containing all data in object - following same structure as in input data
                if year data does not exist - returns empty dict"""
        if year not in self.chron_data.keys():
            year_data = {}
        else:
            year_data = self.chron_data[year]
            if book is not None:
                filtered_year_data = {}
                for book_instance, book_data in year_data.items():
                    if book in book_instance:
                        filtered_year_data[book_instance] = book_data

                year_data = filtered_year_data
        
        return year_data
    
    # def _fetch_books(self, year_dict, book):
    #     """Helper func that takes a dict containing data for one year with book_instances
    #     as keys returns a list of books"""

    def fetch_book_years(self):
        """Return a dict recording unique years for each book_id
        returns: dict of key value pair where key is the book_id and value a list of unique dates
                {"book_id": []}
        """
        year_dict = {}
        for year, data in self.chron_data.items():
            books = list(data.keys())
            books = [self.fetch_book_id(book) for book in books]
            for book in books:
                year_dict.setdefault(book, []).append(year)
        
        return year_dict
    
    def fetch_year_list(self, book_id = None):
        """Return unique list of years present in the object
        book_id: if None return all years, otherwise only years present in the book_id
        returns: list of ints (years)"""
        if book_id is not None:
            book_years = self.fetch_book_years
            years = book_years[book_id]
        else:
            years = list(self.chron_data.keys())
        return years
                

    
    def fetch_year_text(self, year, clean=False, return_tokens=False):
        """return a list of book instances and their corresponding strings for a year
        year: int  for requested date
        clean: clean the text using an OpenITI cleaner
        tokenize: return a list of tokens as a result for text, rather than a string
        returns: list of dict records (convertable to a df with pandas)
                [{"book", "", "instance": int, "text": "" or []}]
                if year does not exist - returns empty list"""
        year_data = self.fetch_year(year)
        out = []
        for book_instance, data in year_data.items():
            # Book name is the book_instance key without the final part
            book = self.fetch_book_id(book_instance)
            instance = data["instance"]
            text = data["content"]

            # Handle cleaning and tokenization
            if clean:
                text = text_cleaner(text)
            if return_tokens:
                text = tokenize(text)[0]

            out.append({"book": book, "instance": instance, "text": text})
        
        return out

    def fetch_year_passim(self, year, book_instance):
        """return all passim data for a year and book instance as a dict
        year: int for requested date
        returns: list of passim data - if no data found for year and book instance, returns empty list"""
        all_data = self.fetch_year(year)
        data = []
        if book_instance in all_data.keys and self.passim_key is not None:
            data = all_data[book_instance][self.passim_key]
        return data
    
    # Passim offset handlers - use raw full text offsets to fetch text of a passim alignment or text in a gap between alignments
    def fetch_full_offset_text(self, year, book_instance, start, end, as_tokens=False):
        """Use a pair of full offsets to identify text within the section and return text
        Returned text will always be cleaned
        year: year in which the section to be offsetted belongs
        book_instance: the book_instance of the section
        start: start of the offset into the full text
        end: end of the offset into the full text
        as_tokens : boolean  - return offset text as list of tokens (e.g. for running token counts)
        returns: text of offset (str), before_chars (int number of chars in offset before section, default 0), after_chars (int number of char in offset after section, default 0)"""

        # Set defaults for before_chars after_chars
        before_chars = 0
        after_chars = 0

        # Get the relevant text and offsets and clean the text
        year_data = self.fetch_year(year)
        section_start, section_end = self.get_year_section_offsets(year_data, book_instance)
        section_text = self._fetch_field_for_instance(year_data, book_instance, "content")
        section_text = text_cleaner(section_text)

        # Adjust offsets based on section start and end
        local_start = start - section_start
        # Check local_start isn't before section end - if it is set outside chars to that variable
        if local_start < 0:
            before_chars = -1*local_start
            local_start = 0
        # Check if the end offset is greater than the section end - if it is set the after_chars and local_end is end of text
        if end > section_end:
            local_end = -1
            after_chars = end - section_end
        # If not calculate the offset on the basis of difference
        else:        
            offset_len = end - start
            local_end = local_start + offset_len

        # Make the cut
        cut_text = section_text[local_start:local_end]

        if as_tokens:
            cut_text = tokenize(cut_text)[0]
        
        return cut_text, before_chars, after_chars
    
    def _append_offset_record(self, offset_list, start_offset, end_offset):
        """Helper to create a dict record for start and end offsets and update the offset list
        returns: offset_list with new record added"""
        offset_record =  {"start_offset": start_offset,
                "end_offset": end_offset}
        offset_list.append(offset_record)
        return offset_list

    def create_mirror_passim_offsets(self, year, book_instance):
        """For all the passim offsets for a year, book_instance, create offsets for the gaps
        between the passim alignments (including gaps between the section start and section end)
        returns: gap_offsets - list of dictionaries (of format that can be converted to records df)
                ["start_offset": int, "end_offset": int] where offsets are full text offsets
        """
        # Fetch the section data
        year_data = self.fetch_year(year)
        section_start, section_end = self.get_year_section_offsets(year_data, book_instance)

        # Fetch the passim data sort them by start
        passim_data = self.fetch_year_passim(year, book_instance)
        passim_data = pd.DataFrame(passim_data).sort_values(by=["start_offset"]).to_dict("records")

        # Write the offsets for the gaps
        gap_offsets = []
        # Check if first entry is after the start
        first_offset = passim_data[0]["start_offset"]
        if first_offset > section_start:
            gap_end = first_offset - section_start
            gap_offsets = self._append_offset_record(gap_offsets, section_start, gap_end)
        
        # Loop through offsets, except final one
        for idx, row in enumerate(passim_data[:-1]):
            gap_start = row["end_offset"]
            gap_end = passim_data[idx+1]["start_offset"]
            gap_offsets = self_append_offset_record(gap_offsets, gap_start, gap_end)
        
        # Check if final entry goes beyond end of section
        final_offset = passim_data[-1]["end_offset"]
        if not final_offset > section_end:
            gap_offsets = self._append_offset_record(gap_offsets, final_offset, section_end)
        
        return gap_offsets




    # Possibly add funcs for retrieving multiple dates - but probably should leave that to requesting func

    # Funcs for handling data formatted according to object data model - takes data formatted according to object as input and returns reformatted
    def _fetch_field_for_instance(self, year_data, book_instance, data_field):
        """Utility function for fetching given data fields for a book instance - and doing safety checks"""
        if not book_instance in year_data.keys():
            print(f"Invalid book instance for given year_data {book_instance}")
            exit()
        return year_data[book_instance][field]

    def get_year_section_offsets(self, year_data, book_instance):
        """For year_data, get a specific book_instance and return its offsets
        returns: offset_start, offset_end, error if invalid book_instance"""
        offset_start = self._fetch_field_for_instance(year_data, book_instance, "offset")
        offset_end = self._fetch_field_for_instance(year_data, book_instance, "end_offset")
        
        return offset_start, offset_end
    
    def get_year_section_dates(self, year_data, book_instance):
        """For year_data, get specific book_instance and return the dates it contains
        returns: list of dates as ints"""
        return self._fetch_field_for_instance(year_data, book_instance, "dates")
    


    
    # Utility funcs for handling data
    def fetch_bids(self):
        return self.books[0], self.books[1]

    def _create_bids(self, b1_path, b2_path):
        """Logic for creating an ID from a book that can be used to create temp data and check temp data"""
        b1_id = b1_path.split("/")[-1]
        b2_id = b2_path.split("/")[-1]
        return b1_id, b2_id

    def _build_json_path(self, file_name):
        """Build the path for the temp data"""
        return os.path.join(self.data_dir, file_name)

    def load_books_data(self):
        """Load the temp file containing the books data"""
        return self._load_json(self._build_json_path(self.book_json))
    
    def write_books_data(self, b1_path, b2_path):
        b1, b2 = self._create_bids(b1_path, b2_path)
        self.books = [b1, b2]
        data = {"books": self.books}
        self.write_json_data(self._build_json_path(self.book_json), data)

    def load_from_temp(self):
        """Load data from temp directory"""
        self.load_json_data(self._build_json_path(self.chron_json))
        self.load_undated_data(self._build_json_path(self.undated_json))
        self.books = self.load_books_data()["books"]

    def write_to_temp(self):
        """Write data to temp directory"""
        self.write_json_data(self._build_json_path(self.chron_json), self.chron_data)
        self.write_json_data(self._build_json_path(self.undated_json), self.undated_data)

    def load_json_data(self, path):
        """Load the data from a json file"""
        dict_data = self._load_json(path)
        # JSON object keys are always strings - cast years back to int so chron_data
        # stays consistent with how fetch_dates/add_update_chron_data populate it
        self.chron_data = {int(year): entries for year, entries in dict_data.items()}

    def load_undated_data(self, path):
        """Load undated_data from a json file - keys are already strings (book.N ids), no cast needed"""
        self.undated_data = self._load_json(path)

    def write_json_data(self, path, data):
        """Write the data to a json file"""

        json_data = json.dumps(data, indent=2, ensure_ascii=False)

        with open(path, "w", encoding='utf-8') as f:
            f.write(json_data)
    
    def _load_json(self, path):
        """Load a json file"""
        with open(path, "r", encoding='utf-8') as f:
            data = json.load(f)
        return data
    
