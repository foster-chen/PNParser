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
from .segmentor import hand_segmentor

def load_entries_from_csv(path: str, return_as_entry=True) -> list[Hand]:
    log_df = pd.read_csv(path)
    entry_lists = [log_df.iloc[:, 0].tolist()[::-1]][0]  # list of log entries in chronological order
    if return_as_entry:
        return [Entry(entry) for entry in entry_lists]
    else:
        return entry_lists