import pandas as pd
import os
from prettytable import PrettyTable
import argparse
from treys import Evaluator
from treys.lookup import LookupTable
from phevaluator import evaluate_cards
from phevaluator.card import Card
from typing import Union
import re

from classes import Entry, Hand

log_dir = "data/poker_now_log_pglOQ-rWNflPZLm3su2DufFm6.csv"

log_df = pd.read_csv(log_dir)

# log_df.iloc[120:154]
print(log_df.iloc[50][0])

def _get_name(entry: str):
    full_name = re.findall(r'"([^"]*)"', entry)
    name = full_name.split("@")

