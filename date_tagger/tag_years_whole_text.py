# -*- coding: utf-8 -*-
"""
Created on Wed Jun 16 10:17:05 2021

@author: mathe
"""

import pandas as pd
import re
import os
from tqdm import tqdm


dates_df = "./dates-df.csv"

dates_df = pd.read_csv(dates_df, dtype=str)


def string_to_date(line_split, n_tok, dates_df = dates_df):
    
    # Load in the conversion csv
   
    
    dates_1 = dates_df[["1s", "1_no"]].dropna().values.tolist()
    dates_10 = dates_df[["10s", "10s_no"]].dropna().values.tolist()
    dates_100 = dates_df[["100s", "100s_no"]].dropna().values.tolist()
    dates_100_sep = dates_df[["100_1","100_1_no"]].dropna().values.tolist()
    start_terms = dates_df[["year", "meaning"]].dropna().values.tolist()
    exc_100 = "مائة"
    exc_100_2 = "مئة"
    # Setting digits and other values
    d1 = "0"
    d2 = "0"
    d3 = "0"
    y_type = "@YY"
    
    pos_1 = 0
    pos_2 = 1
    pos_3 = 2
    pos_4 = 3
    pos_5 = 4
    
    if n_tok >= 3:
            
            
            for digit_1 in dates_1:
                if digit_1[0] == line_split[pos_1]:
                    d1 = digit_1[1]
                    break
            for digit_2 in dates_10:
                if digit_2[0] == line_split[pos_2] or digit_2[0] == line_split[pos_1]:
                    d2 = digit_2[1]
                    break
            for digit_3 in dates_100:
                                    
                if digit_3[0] == line_split[pos_3] or digit_3[0] == line_split[pos_2] or digit_3[0] == line_split[pos_1]:
                    d3 = digit_3[1]
                    break
                                        
            if line_split[pos_2] == exc_100 or line_split[pos_2] == exc_100_2:
                for digit_1 in dates_100_sep:
                    if digit_1[0] == line_split[pos_1]:                                            
                        d3 = digit_1[1]
                        d2 = '0'
                        d1 = '0'
                        break
                                
            # Finding cases of 'ba'd miyya'
            if line_split[pos_3] == "بعد":                                
                                                        
                try:
                    if line_split[pos_5] == exc_100 or line_split[pos_5] == exc_100_2:
                        for digit_1 in dates_100_sep:
                            if digit_1[0] == line_split[pos_4]:
                                d3 = digit_1[1]
                                break
                except IndexError:
                    pass                                                        
                try:
                    for digit_3 in dates_100:
                        if digit_3[0] == line_split[pos_4]:
                            d3 = digit_3[1]
                            break
                except IndexError:
                    pass
                                
                # Exceptions - split 100s and non-chronicle year types
                try:
                    if line_split[pos_2] == "مولده" or line_split[pos_3] == "مولده" or line_split[pos_4] == "مولده" or line_split[pos_5] == "مولده":
                        y_type = '@YF'
                except IndexError:
                    pass
            if line_split[pos_2] == "من" :
                    if line_split[pos_3] == "ولاية" or line_split[pos_3] == "سلطنة":
                        y_type = "@YR"
                    if line_split[pos_3] == "مولده" or line_split[pos_3] == "الفيل":
                        y_type = "@YF"
                                    
                    if line_split[pos_3] == "النبوة" or line_split[pos_3] == "البعثة":
                        y_type = "@YP"
                    if line_split[pos_3] == "النبوة" or line_split[pos_3] == "البعثة":
                        y_type = "@YP"
            if line_split[pos_2] == "ولاية" :
                        y_type = "@YR"
            elif line_split[pos_3] == exc_100 or line_split[pos_3] == exc_100_2:
                                   
                        for digit_1 in dates_100_sep:
                            if digit_1[0] == line_split[pos_2]:
                                d3 = digit_1[1]
            elif line_split[pos_3] == "من" :
                        try:    
                            if line_split[pos_4] == "ولاية" or line_split[pos_4] == "سلطنة":
                                y_type = "@YR"
                            if line_split[pos_4] == "مولده" or line_split[pos_4] == "الفيل":
                                y_type = "@YF"
                                        
                            if line_split[pos_4] == "النبوة" or line_split[pos_4] == "البعثة":
                                y_type = "@YP"
                        except IndexError:
                            pass
            try:
                                    
                if line_split[pos_4] == exc_100 or line_split[pos_4] == exc_100_2:
                                            
                    for digit_1 in dates_100_sep:
                        if digit_1[0] == line_split[pos_3]:
                            d3 = digit_1[1]
                    # Dropping cases where the year is regnal
                elif line_split[pos_4] == "من" :
                                if line_split[pos_5] == "ولاية" or line_split[pos_5] == "سلطنة":
                                    y_type = "@YR"
                                if line_split[pos_5] == "مولده" or line_split[pos_5] == "الفيل":
                                    y_type = "@YF"
                                    
            except IndexError:
                pass
            if line_split[pos_3] == "ولاية" :
                y_type = "@YR"
                                    
                                
                            

    elif n_tok == 2:
            for digit_1 in dates_1:
                if digit_1[0] == line_split[pos_1]:
                    d1 = digit_1[1]
                    break
            for digit_2 in dates_10:
                if digit_2[0] == line_split[pos_2] or digit_2[0] == line_split[pos_1]:
                    d2 = digit_2[1]
                    break
            for digit_3 in dates_100:
                if digit_3[0] == line_split[pos_2] or digit_3[0] == line_split[pos_1]:
                    d3 = digit_3[1]
                    break
                if line_split[pos_2] == exc_100 or line_split[pos_2] == exc_100_2:
                    for digit_1 in dates_100_sep:
                        if digit_1[0] == line_split[pos_1]:
                            d3 = digit_1[1]
                            d2 = '0'
                            d1 = '0'
                            break
                            
                            

    elif n_tok == 1:
            for digit_1 in dates_1:
                if digit_1[0] == line_split[pos_1]:
                    d1 = digit_1[1]
                    break
            for digit_2 in dates_10:
                if digit_2[0] == line_split[pos_1]:
                    d2 = digit_2[1]
                    break
            for digit_3 in dates_100:
                if digit_3[0] == line_split[pos_1]:
                    d3 = digit_3[1]
                    break
 
    
    year = y_type + d3 + d2 + d1
    return year
    

def string_y_tag (string):    
    
    # Clean the line and get the token count (for efficiency)
    line_clean = re.sub(r"ms\d+|\]|\[|\d+|[,./؟\?!()«»،:~]|###|\|", "", string)    
    
   
    if len(re.findall("سنة", line_clean)) > 0:
        
        date_strings = line_clean.split("سنة")
        tag = ""
        for date_string in date_strings:
            line_split = date_string.split()
            n_tok = len(line_split)
            tag = tag + " " + string_to_date(line_split, n_tok) 
    else: 
        line_split = line_clean.split()
        n_tok = len(line_split)
        tag = string_to_date(line_split, n_tok)
    return tag
    
    
    
    
    


def date_sub(m):
    
    date_string = m.group(0)
    date_tag = string_y_tag(date_string)        
    return " " + date_tag + date_string
        




def tag_whole_text_dir(in_dir, out_dir, path_list = False):
    if not path_list:
        path_list = []         
        for root, dirs, files in os.walk(in_dir, topdown=False):
            for name in tqdm(files):            
                text_path = os.path.abspath(os.path.join(root, name))
                path_list.append(text_path)
    else:
        path_list = in_dir
    for text_path in path_list:        
        with open(text_path, encoding = "utf-8") as f:
            text = f.read()
            f.close()

        sana = "سنة"
        text = re.sub(r"(?<=%s)(\s\S*){6}" % (sana), date_sub, text)
        
        name = text_path.split("/")[-1]
        out_name = name + ".dates_tagged"
        print(out_dir)
        print(out_name)
        text_out_path = os.path.join(out_dir, out_name)
        print(text_out_path)
        
        with open(text_out_path, "w", encoding = "utf-8") as f:
            f.write(text)
            f.close()
    