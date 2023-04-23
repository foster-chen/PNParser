from .hand import Entry, Hand
from typing import Union
from tools import hand_segmentor

class Session:
    def __init__(self) -> None:
        pass

    def load_entries(self, entries: Union[list[Entry], list[str]]):
        if isinstance(entries[0], str):
            self.entries = [Entry(entry) for entry in entries]
        elif isinstance(entries[0], Entry):
            self.entries = entries
        hands = hand_segmentor(self.entries)
        breakpoint()
        self.hands = [Hand(hand) for hand in hands]

    def __getitem__(self, index):
        return self.hands[index]
