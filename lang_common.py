# -*- coding: utf-8 -*-
# библиотека общих функций для lang_main.py и lang_bs_main.py

import sys
import pickle

def get_args():
    return pickle.loads(sys.argv[1])

# to be used in algo_*.py and passed through lang_*main.py
args = get_args()
