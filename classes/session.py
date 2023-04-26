from .hand import Entry, Hand
from typing import Union
from .utils import hand_segmentor

class Session:
    def __init__(self) -> None:
        self.hands = None
        self.players = None

    def load_entries(self, entries: Union[list[Entry], list[str]]):
        if isinstance(entries[0], str):
            self.entries = [Entry(entry) for entry in entries]
        elif isinstance(entries[0], Entry):
            self.entries = entries
        hands = hand_segmentor(self.entries)
        breakpoint()
        self.hands = [Hand(hand) for hand in hands]

    def __getitem__(self, index: Union[str, int]):
        if isinstance(index, int):
            return self.hands[index]
        elif isinstance(index, str):
            for hand in self.hands:
                if hand.id == index:
                    return hand
            raise IndexError(f"Hand ID {index} not found in session")
        else:
            raise IndexError("Index with hand number of hand ID")

