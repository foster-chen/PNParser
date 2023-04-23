from typing import Union
from classes import Entry

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
    return hands_list[1:]
