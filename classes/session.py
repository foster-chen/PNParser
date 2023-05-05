from .hand import Entry, Hand
from .player import Player
from typing import Union
from .utils import hand_segmentor, EntryList, raw_attributes, player_attributes, player_attribute_titles
import pandas as pd
import json
import seaborn as sns
import matplotlib.pyplot as plt
from matplotlib.transforms import blended_transform_factory
sns.set_theme()

class Session:

    hand_attributes = raw_attributes()
    _actions = ["Call", "Donk", "Bet", "Raise", "Check-Raise", "PFR", "3-Bet", "4-Bet", "5-Bet", "5-Bet+", "C-Bet", "2-Barrel", "3-Barrel"]
    
    def __init__(self, own_id=None) -> None:
        self.hands = []
        self.entries = []
        self.players = dict(_average_=Player("_average_"))
        self.admin_entries = EntryList([])
        self.name_map = dict()
        self.own_id = own_id
        self._session_id = None
        self._id_to_hand = dict()
        
    def load_entries(self, *entries: list[Union[list[Entry], list[str]]], reset=False):
        if reset:
            self.hands, self.entries = [], []
        for ent in entries:
            if isinstance(ent[0], str):
                ent = [Entry(entry) for entry in ent]
            hands, admin_entries = hand_segmentor(ent, return_admin=True)
            for i, hand in enumerate(hands):
                try:
                    hand = Hand(hand)
                    self.hands.append(hand)
                    self._id_to_hand[hand.id] = len(self.hands) - 1
                except KeyError:
                    print(f"\nSkipped errored hand below:")
                    for entry in hand:
                        print(entry)
            self.admin_entries.extend(admin_entries)
            self.init_players()

    def __getitem__(self, index: Union[str, int]):
        if isinstance(index, int):
            return self.hands[index]
        elif isinstance(index, str):
            return self.hands[self._id_to_hand[index]]
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
                        try:
                            self.players[self.name_map[entry.name[0][0]]]
                        except KeyError:
                            self.players[self.name_map[entry.name[0][0]]] = Player(self.name_map[entry.name[0][0]])
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
    
    def log_session_stats(self, reset=True):
        assert self.hands, "No hand history to update"
        if reset:
            for name in self.players:
                self.players[name].reset()
        
        for hand in self.hands:
            self.log_hand_stats(hand)

    def log_hand_stats(self, hand: Hand):
        # record own player ID
        if not self.own_id:
            while True:
                id = input("Own ID not stored. Input own user ID: ")
                if id in self.players:
                    break
                else:
                    print("ID not found in logs")
            self.own_id = id
        self._own_alt_ids = [key for key in self.name_map if self.name_map[key] == self.own_id]
        assert len(self._own_alt_ids) >= 1
        
        # pass own player ID into each hand
        for name in hand.players:
            if name in self._own_alt_ids:
                hand.own_player_id = name

        # log raw stats into players in this session
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

        # record all revealed hands
        if hand.revealed_holdings:
            for name, holdings in hand.revealed_holdings.items():
                position = [0 for _ in hand.players]
                position[hand.players.index(name)] = 1
                self.players[self.name_map[name]].hands[hand.id] = {"hand": holdings, "position": position, "actions": [history["descriptor"]["action"] for history in hand.bet_history.values() if history["stage"] != "end" and history["descriptor"]["name"] == name]}
        
        # record own hand
        if hand.own_hand:
            position = [0 for _ in hand.players]
            for i, name in enumerate(hand.players):
                if name in self._own_alt_ids:
                    position[i] = 1
            self.players[self.own_id].hands[hand.id] = {"hand": hand.own_hand, "position": position, "actions": [history["descriptor"]["action"] for history in hand.bet_history.values() if history["stage"] != "end" and history["descriptor"]["name"] in self._own_alt_ids]}

        # update _average_ dummy player
        for name in hand.players:
            self.players[self.name_map[name]].n_hands_tracked += 1
            self.players["_average_"].n_hands_tracked += 1

        # track player balance
        player_update_track = {name: False for name in self.players if name != "_average_"}
        for name in hand.players:
            player_update_track[self.name_map[name]] = True
            self.players[self.name_map[name]].balance_history.append(hand.stack_changes[name])
        for name in player_update_track:
            if not player_update_track[name]:
                self.players[name].balance_history.append(0)
    
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
            if name != "_average_":
                index.append(f"({profile.n_hands_tracked}) {name}")
            else:
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
        hm = sns.heatmap(proportional_deviation, annot=self.players_profile, center=1, fmt='.3f', cmap="vlag", annot_kws={'fontsize':7}, vmin=-0.1, vmax=2, cbar=False)
        hm.set_xticklabels(hm.get_xticklabels(), rotation=45, ha='right', fontsize=9)
        tf = blended_transform_factory(plt.gca().transAxes, plt.gca().transAxes)
        plt.text(0.85, -0.25, f"{self.__len__()} hands", fontsize=10, color='gray', transform=tf)

    def plot_winnings(self, include=None, exclude=None):
        assert not (include and exclude), "Both inclusion and exclusion set"
        if include:
            assert isinstance(include, list) or isinstance(include, str)
            include = include if isinstance(include, list) else [include]
            players = []
            for name in include:
                assert name in [name for name in self.players if name != "_average_"], f"ID {name} not found in session. Session players: {[player for player in self.players if player != '_average_'] }"
                players.append(name)
        else:
            players = [name for name in self.players if name != "_average_"]
        if exclude:
            assert isinstance(exclude, list) or isinstance(exclude, str)
            exclude = exclude if isinstance(exclude, list) else [exclude]
            for name in exclude:
                assert name in players, f"ID {name} not found in session. Session players: {[player for player in self.players if player != '_average_'] }"
                players.remove(name)  
        winnings = {player: self.players[player].accumulated_winnings for player in players}
        winnings_df = pd.DataFrame(winnings, index=list(range(len(self))))
        fig, ax = plt.subplots(figsize=(13, 10))
        sns.lineplot(data=winnings_df, palette="tab10", ax=ax, linewidth=2.5, dashes=False)
        ax.axhline(y=0, color='black', linestyle='--', alpha=0.5)
        ax.set_ylabel("Net Stack Change")
        ax.set_xlabel("Hands")
    
    def find_hands(self, *descriptor):
        result = list()
        for d in descriptor:
            _result = list()
            hand_list = result if result else self.hands
            if "|" in d:
                ors = d.replace(" ", "").split("|")
                for _d in ors:
                    if _d.startswith("!"):
                        assert _d[1:] in self._actions, f"Supported search keyword:\n{self._actions}"
                    else:
                        assert _d in self._actions, f"Supported search keyword:\n{self._actions}"
                    for ele in hand_list:
                        if isinstance(ele, Hand) and _d.startswith("!") \
                        and _d[1:] not in [history["descriptor"]["action"] for history in ele.bet_history.values() if history["stage"] != "end"]:
                            _result.append(ele.id)
                        elif isinstance(ele, Hand) and not _d.startswith("!") \
                        and _d in [history["descriptor"]["action"] for history in ele.bet_history.values() if history["stage"] != "end"]:
                            _result.append(ele.id)
                        elif isinstance(ele, str) and _d.startswith("!") \
                        and _d[1:] not in [history["descriptor"]["action"] for history in self[ele].bet_history.values() if history["stage"] != "end"]:
                            _result.append(ele)
                        elif isinstance(ele, str) and not _d.startswith("!") \
                        and _d in [history["descriptor"]["action"] for history in self[ele].bet_history.values() if history["stage"] != "end"]:
                            _result.append(ele)
                _result = list(set(_result))
            else:
                if d.startswith("!"):
                    assert d[1:] in self._actions, f"Supported search keyword:\n{self._actions}"
                else:
                    assert d in self._actions, f"Supported search keyword:\n{self._actions}"
                for ele in hand_list:
                    if isinstance(ele, Hand) and d.startswith("!") \
                    and d[1:] not in [history["descriptor"]["action"] for history in ele.bet_history.values() if history["stage"] != "end"]:
                        _result.append(ele.id)
                    elif isinstance(ele, Hand) and not d.startswith("!") \
                    and d in [history["descriptor"]["action"] for history in ele.bet_history.values() if history["stage"] != "end"]:
                        _result.append(ele.id)
                    elif isinstance(ele, str) and d.startswith("!") \
                    and d[1:] not in [history["descriptor"]["action"] for history in self[ele].bet_history.values() if history["stage"] != "end"]:
                        _result.append(ele)
                    elif isinstance(ele, str) and not d.startswith("!") \
                    and d in [history["descriptor"]["action"] for history in self[ele].bet_history.values() if history["stage"] != "end"]:
                        _result.append(ele)
            result = _result
        return result
