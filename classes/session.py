from .hand import Entry, Hand
from .player import Player
from typing import Union
from .utils import hand_segmentor, EntryList, raw_attributes

class Session:

    hand_attributes = raw_attributes()
    
    def __init__(self) -> None:
        self.hands = None
        self.players = dict()
        self.admin_entries = []

    def load_entries(self, entries: Union[list[Entry], list[str]]):
        if isinstance(entries[0], str):
            self.entries = [Entry(entry) for entry in entries]
        elif isinstance(entries[0], Entry):
            self.entries = entries
        hands, admin_entries = hand_segmentor(self.entries, return_admin=True)
        self.admin_entries = EntryList(admin_entries)
        breakpoint()
        self.hands = [Hand(hand) for hand in hands]
        self.init_players()

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
    
    def __len__(self):
        return len(self.hands)
    
    def init_players(self, players=None):
        if players:
            assert isinstance(players, list)
        if not players:
            assert self.hands, "Pass in the list of players to manually initialize. To initialize automatically from session log, use load_entries() first"
            for entry in self.admin_entries:
                if entry.descriptor == "join":
                    try:
                        self.players[entry.name[0][0]]
                    except KeyError:
                        self.players[entry.name[0][0]] = Player(entry.name[0][0])
        else:
            for name in players:
                try:
                    self.players[name]
                except KeyError:
                    self.players[name] = Player(name)
    
    def update_player_profiles(self):
        for name in self.players:
            self.players[name].update_profile()
    
    def log_session_stats(self, reset_players=True):
        assert self.hands, "No hand history to update"
        if reset_players:
            for name in self.players:
                self.players[name].reset()
        
        for hand in self.hands:
            self.log_hand_stats(hand)

    def log_hand_stats(self, hand: Hand):
        for attribute in self.hand_attributes:
            if not getattr(hand, attribute):
                pass
            elif isinstance(getattr(hand, attribute), str):
                stat = getattr(self.players[getattr(hand, attribute)], f"_{attribute}")
                setattr(self.players[getattr(hand, attribute)], f"_{attribute}", stat + 1)
            elif isinstance(getattr(hand, attribute), list):
                for name in getattr(hand, attribute):
                    stat = getattr(self.players[name], f"_{attribute}")
                    setattr(self.players[name], f"_{attribute}", stat + 1)
            elif isinstance(getattr(hand, attribute), dict):
                for name, value in getattr(hand, attribute).items():
                    if isinstance(value, int):
                        stat = getattr(self.players[name], f"_{attribute}")
                        setattr(self.players[name], f"_{attribute}", stat + value)
                    elif isinstance(value, dict):
                        for att, ele in value.items():
                            stat = getattr(self.players[name], f"_{att}")
                            setattr(self.players[name], f"_{att}", stat + ele)

        for name in hand.players:
            self.players[name[0]].n_hands_tracked += 1

