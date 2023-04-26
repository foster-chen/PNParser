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
from . import Entry
from colorama import Fore, Style

class EntryList(list):
    def __init__(self, lst: list):
        super(EntryList, self).__init__(lst)
        
    def __str__(self):
        return "\n".join([entry.raw for entry in self])

class COLOR:
    action_highlight = Fore.LIGHTYELLOW_EX
    fold = Fore.RED + Style.DIM
    dormant = Fore.LIGHTBLACK_EX + Style.DIM
    reset = Style.RESET_ALL

def pretty_cards(*cards: Union[int, str, Card]):

    cards = [Card(id) for id in list(map(Card.to_id, cards))]
    
    def _get_pretty_card(card: Card):
        suit_unicode_lookup = {
            "s": u"\u2660",
            "h": u"\u2665",
            "d": u"\u2666",
            "c": u"\u2663",}
        RED = "\033[1;31m"
        BLACK = "\033[0;0m"
        prefix = RED if card.describe_suit() in ['h', 'd'] else ''
        postfix = BLACK if card.describe_suit() in ['h', 'd'] else ''
        return prefix + suit_unicode_lookup[card.describe_suit()] + card.describe_rank() + postfix
        

    cards = [Card(id) for id in list(map(Card.to_id, cards))]
    return ", ".join([_get_pretty_card(card) for card in cards])

def load_entries_from_csv(path: str, return_as_entry=True):
    log_df = pd.read_csv(path)
    entry_lists = [log_df.iloc[:, 0].tolist()[::-1]][0]  # list of log entries in chronological order
    if return_as_entry:
        return [Entry(entry) for entry in entry_lists]
    else:
        return entry_lists
    
def hand_segmentor(entries: list[Union[str, Entry]]):
    hands_list = []
    current_hand = []
    
    for entry in entries:
        if isinstance(entry, str):
            entry = Entry(entry)
        if entry.descriptor == "start":
            hands_list.append(current_hand)
            current_hand = [entry]
        elif entry.descriptor not in ['add stack', 'join', 'terminate', 'admin']:
            current_hand.append(entry)
    hands_list.append(current_hand)
    return hands_list[1:]

def get_rank(cards, return_readable_rank=True):
    _evaluator = Evaluator()
    rank = evaluate_cards(*cards)
    if return_readable_rank:
        return (rank, LookupTable.RANK_CLASS_TO_STRING[_evaluator.get_rank_class(rank)])
    else:
        return rank
