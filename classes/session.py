from .hand import Entry, Hand
from .player import Player
from typing import Union
from .utils import hand_segmentor, EntryList, raw_attributes, player_attributes, player_attribute_titles
import pandas as pd
import json
import seaborn as sns

class Session:

    hand_attributes = raw_attributes()
    
    def __init__(self) -> None:
        self.hands = []
        self.entries = []
        self.players = dict(_average_=Player("_average_"))
        self.admin_entries = EntryList([])
        self.name_map = dict()
        
    def load_entries(self, entries: Union[list[Entry], list[str]], reset=False):
        if reset:
            self.hands, self.entries = [], []
        if isinstance(entries[0], str):
            entries = [Entry(entry) for entry in entries]
        hands, admin_entries = hand_segmentor(entries, return_admin=True)
        self.hands.extend([Hand(hand) for hand in hands])
        self.admin_entries.extend(admin_entries)
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
                    if entry.name[0][0] in self.name_map:
                        continue
                    elif entry.name[0][0] in self.players:
                        self.name_map[entry.name[0][0]] = entry.name[0][0]
                    else:
                        print(f"Current profiles: {[name for name in self.players]}")
                        in_rename = True
                        while in_rename:
                            rename = input(f"Creating new player profile for \"{entry.name[0][0]}\". Rename? [Y/N]: ")
                            if rename.lower() == "y":
                                name = input(f"Rename \"{entry.name[0][0]}\" to ->: ")
                                self.name_map[entry.name[0][0]] = name
                                try:
                                    self.players[name]
                                except KeyError:
                                    self.players[name] = Player(name)
                                in_rename = False
                            elif rename.lower() == "n":
                                self.name_map[entry.name[0][0]] = entry.name[0][0]
                                try:
                                    self.players[entry.name[0][0]]
                                except KeyError:
                                    self.players[entry.name[0][0]] = Player(entry.name[0][0])
                                in_rename = False
                            else:
                                pass
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
                self._add_to_attribute(self.players[self.name_map[getattr(hand, attribute)]], f"_{attribute}", 1)
                self._add_to_attribute(self.players["_average_"], f"_{attribute}", 1)
            elif isinstance(getattr(hand, attribute), list):
                for name in getattr(hand, attribute):
                    name = self.name_map[name]
                    self._add_to_attribute(self.players[name], f"_{attribute}", 1)
                    self._add_to_attribute(self.players["_average_"], f"_{attribute}", 1)
            elif isinstance(getattr(hand, attribute), dict):
                for name, value in getattr(hand, attribute).items():
                    name = self.name_map[name]
                    if isinstance(value, int):
                        self._add_to_attribute(self.players[name], f"_{attribute}", value)
                        self._add_to_attribute(self.players["_average_"], f"_{attribute}", value)
                    elif isinstance(value, dict):
                        for att, ele in value.items():
                            self._add_to_attribute(self.players[name], f"_{att}", ele)
                            self._add_to_attribute(self.players["_average_"], f"_{att}", ele)

        for name in hand.players:
            self.players[self.name_map[name[0]]].n_hands_tracked += 1
            self.players["_average_"].n_hands_tracked += 1

    
    @staticmethod
    def _add_to_attribute(_class, attribute, value):
        original_stat = getattr(_class, attribute)
        setattr(_class, attribute, original_stat + value)
    
    @property
    def players_profile(self):
        header = player_attribute_titles()
        index = []
        table = []
        for name, profile in self.players.items():
            index.append(name)
            table.append(profile.stat_api()[1:])
        return pd.DataFrame(table, columns=header, index=index).T
    
    @property
    def players_raw_stats(self):
        header = raw_attributes()
        index = []
        table = []
        for name, profile in self.players.items():
            index.append(name)
            table.append(profile.raw_stat_api())
        return pd.DataFrame(table, columns=header, index=index).T

    def load_name_map(self, _map):
        if isinstance(_map, dict):
            self.name_map = _map
        elif isinstance(_map, str):
            with open(_map, "r") as f:
                self.name_map = json.load(f)
    
    def export_name_map(self, path):
        with open(path, "w") as f:
            json.dump(self.name_map, f, indent=2)
        
    def plot_profile(self):
        proportional_deviation = self.players_profile.div(list(self.players_profile["_average_"]), axis=0)
        hm = sns.heatmap(proportional_deviation, annot=self.players_profile, center=1, fmt='.2f', cmap="vlag", annot_kws={'fontsize':7}, vmin=-0.5, vmax=2.5, cbar=False)
        hm.set_xticklabels(hm.get_xticklabels(), rotation=45, ha='right', fontsize=9)
