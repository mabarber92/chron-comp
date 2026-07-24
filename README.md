# chron-comp 
Tools for comparing OpenITI chronicles

# Introduction
The functions in this repository allow for the comparison of Arabic texts organised by year. They allow one to see at scale ways in which two chronicles rely on one-another, deviate semantically or thematically, and to calculate basic statistics around the similarity/difference between chronicles.

# Testing
The code in this repository has been tested using:
0677IbnMuyassar.AkhbarMisr
0845Maqrizi.ItticazHunafa

# Repository structure and usage
The repository is structured around two-step process. The main functions expect OpenITI texts
with full structural mARkdown and date tags @YY and @YR inserted. For best results, correct the
tags inserted by the date_tagger functions into the mARkdown headings.

Directories:
- date_tagger : function (and supporting data) for adding date tags to OpenITI texts
- chron_comp : functions for making comparisons between chronicles
- openiti_utils: functions for loading OpenITI texts as structural and milestone units (for example, for easy and predictable processing of text reuse offsets). Used by chron_comp functs
- data/texts : OpenITI texts used as input for chron_comp (with date tags inserted)
- data/temp : temporary data produced by running chron_comp - avoids need to reprocess data

# To do:
date_tagger:
- migrate and lightly refactor existing date tagger funcs: to take an input text and add tags
openit_utils:
- migrate existing openiti classes (aim for minimal/no modification of these)
- these classes need to include tokenizers (possibly different tokenization strategies)
chron_comp:
- base pairwise data class:
 - object that stores pairs of years with the full text
 - load pair of texts as pair of dates
 - function to add pairwise text reuse data, populate year-wise offsets
 - need to handle cases where multiple sections in text might have same year label
 - load/save year-wise data as json
- year-wise text comparison class:
 - func to create year fragments (split according to heuristic)
 - TF-IDF representations of chronicle years as documents
 - TF-IDF representations of year fragments as documents
 - sequence embedded representations of years as documents (may cap out token limit)
 - sequence embedded representations of year fragments as documents
 - option to use passim verbatim alignment boundaries as splits for year fragments
 - func to calculate cosine similarity between any document representation (all years in text a to all years in text b)
 - func to rank cosine similarities
 - nice-to-have - year-level named entities comparisons
 - nice-to-have - compare order of narrative units within year (text reuse, cosine sim fragments possibly a way into this)
 - store new document representations and cosine similarities within pairwise data class
 - export data for specific years or whole text pairs related to analysis
- pairwise stats class:
 - inherits pairwise data class (and uses that structure)
 - compare year lengths (words and chars)
 - compare year coverage (first year, last year, missing years for each side of the relationship, and shared data)
 - compare text reuse data year-wise (how much of a year is shared between the two texts, how large are gaps between reuse on each side)
 - compare other semantic similarities year-wise
 - export stats as reports
- graphing class(es):
 - graph results of comparisons - typically with text a or b on the x axis (possibly with dates as labels)
