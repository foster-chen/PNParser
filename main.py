import argparse
from treys import Evaluator
from treys.lookup import LookupTable
from phevaluator import evaluate_cards
from classes import Hand, Entry, Session
from tools import load_entries_from_csv


# def parse_args(args):
#     parser = argparse.ArgumentParser()
#     parser.add_argument("logs", type=str)

#     args = parser.parse_args()
#     return args

session = Session()
entries = load_entries_from_csv("data/poker_now_log_pglfe0T7uQ0xAoikKguywLWDJ.csv")
breakpoint()
session.load_entries(entries)
