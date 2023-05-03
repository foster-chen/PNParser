from .utils import raw_attributes, player_attributes, describe_holdings
from tabulate import tabulate
import numpy as np
import seaborn as sns
from matplotlib import pyplot as plt
from matplotlib.transforms import blended_transform_factory

class Player:

    raw_stats = raw_attributes()
    player_stats = player_attributes()
    _actions = ["Call", "Donk", "Bet", "Raise", "Check-Raise", "PFR", "3-Bet", "4-Bet", "5-Bet", "5-Bet+", "C-Bet", "2-Barrel", "3-Barrel"]

    def __init__(self, name) -> None:
        self.n_hands_tracked = 0
        for attribute in self.raw_stats:
            setattr(self, f"_{attribute}", 0)
        self._attack = 0
        self._defend = 0
        for attribute in self.player_stats:
            setattr(self, attribute, None)
        self.name = name
        self.hands = dict()

    def reset(self):
        self.__init__(self.name)
    
    def update_profile(self):
        self.vpip = self._divide(self._vpip, self.n_hands_tracked)
        self.wtsd = self._divide(self._wtsd, self._join_flop)
        self.pfr = self._divide(self._pfr, self.n_hands_tracked)
        self.af = self._divide(self._attack, self._defend)
        self.three_bet = self._divide(self._three_bet, self._call_pfr + self._fold_to_pfr + self._three_bet)
        self.four_bet = self._divide(self._four_bet, self._call_three_bet + self._fold_to_three_bet + self._four_bet)
        self.five_bet = self._divide(self._five_bet, self._call_four_bet + self._fold_to_four_bet + self._five_bet)
        self.c_bet = self._divide(self._c_bet, self._preflop_lead)
        self.double_barrel = self._divide(self._double_barrel, self._c_bet)
        self.triple_barrel = self._divide(self._triple_barrel, self._double_barrel)
        self.fold_to_pfr = self._divide(self._fold_to_pfr, self._three_bet + self._call_pfr + self._fold_to_pfr)
        self.fold_to_three_bet = self._divide(self._fold_to_three_bet, self._four_bet + self._call_three_bet + self._fold_to_three_bet)
        self.fold_to_four_bet = self._divide(self._fold_to_four_bet, self._five_bet + self._call_four_bet + self._fold_to_four_bet)
        self.fold_to_c = self._divide(self._fold_to_c, self._raise_against_c + self._call_c + self._fold_to_c)
        self.fold_to_double = self._divide(self._fold_to_double, self._raise_against_double + self._call_double + self._fold_to_double)
        self.fold_to_triple = self._divide(self._fold_to_triple, self._raise_against_triple + self._call_triple + self._fold_to_triple)
        self.check_raise = self._divide(self._check_raise, self._call_without_checkraise)

    @staticmethod
    def _divide(num1, num2):
        try:
            return num1 / num2
        except ZeroDivisionError:
            return None
    
    def __str__(self):
        table = [["Name", self.name],
                 ["VPIP", f"{round(self.vpip * 100, 2)}%" if self.vpip else None],
                 ["PFR", f"{round(self.pfr * 100, 2)}%" if self.pfr else None],
                 ["AF", round(self.af, 2) if self.af else None],
                 ["WTSD", round(self.af, 2) if self.af else None], 
                 ["3-Bet", f"{round(self.three_bet * 100, 2)}%" if self.three_bet else None],
                 ["4-Bet", f"{round(self.four_bet * 100, 2)}%" if self.four_bet else None],
                 ["5-Bet", f"{round(self.five_bet * 100, 2)}%" if self.five_bet else None],
                 ["C-Bet", f"{round(self.c_bet * 100, 2)}%" if self.c_bet else None],
                 ["2Ba", f"{round(self.double_barrel * 100, 2)}%" if self.double_barrel else None],
                 ["3Ba", f"{round(self.triple_barrel * 100, 2)}%" if self.triple_barrel else None],
                 ["F-PFR", f"{round(self.fold_to_pfr * 100, 2)}%" if self.fold_to_pfr else None],
                 ["F-3B", f"{round(self.fold_to_three_bet * 100, 2)}%" if self.fold_to_three_bet else None],
                 ["F-4B", f"{round(self.fold_to_four_bet * 100, 2)}%" if self.fold_to_four_bet else None],
                 ["F-CB", f"{round(self.fold_to_c * 100, 2)}%" if self.fold_to_c else None],
                 ["F-2Ba", f"{round(self.fold_to_double * 100, 2)}%" if self.fold_to_double else None],
                 ["F-3Ba", f"{round(self.fold_to_triple * 100, 2)}%" if self.fold_to_triple else None],
                 ["Trap", f"{round(self.check_raise * 100, 2)}%" if self.check_raise else None],
                 ["Hands", f"({self.n_hands_tracked})"]]
        return tabulate(table, tablefmt="grid")
        
    def stat_api(self):
        return [getattr(self, attribute) for attribute in self.player_stats]

    def raw_stat_api(self):
        return [getattr(self, f"_{attribute}") for attribute in self.raw_stats]

    def print_raw(self):
        for attribute in self.raw_stats:
            print(f"{attribute}: {getattr(self, f'_{attribute}')}")
    
    def find_hands(self, *descriptor, position=None):
        result = list()
        for d in descriptor:
            _result = list()
            id_list = result if result else self.hands.keys()
            if "|" in d:
                ors = d.replace(" ", "").split("|")
                for _d in ors:
                    assert _d in self._actions, f"Supported search keyword:\n{self._actions}"
                    for id in id_list:
                        if _d in self.hands[id]["actions"]:
                            if (position and self.hands[id]["position"][position] == 1) or not position:
                                _result.append(id)

                _result = list(set(_result))
            else:
                assert d in self._actions, f"Supported search keyword:\n{self._actions}"
                for id in id_list:
                    if d in self.hands[id]["actions"]:
                        if (position and self.hands[id]["position"][position] == 1) or not position:
                             _result.append(id)
            result = _result
        return result
    
    def hand_chart(self, hand_ids, show_frequency=False):
        hand_to_index = dict()
        ranks = ["A", "K", "Q", "J", "T", "9", "8", "7", "6", "5", "4", "3", "2"]
        annotations = [[0 for _ in range(13)] for _ in range(13)]
        result = np.array(annotations)
        base_count = np.array(annotations)

        for i in range(13):
            for j in range(13):
                if j > i:
                    annotations[i][j] = f"{ranks[i]}{ranks[j]}s"
                    hand_to_index[f"{ranks[i]}{ranks[j]}s"] = (i, j)
                elif i > j:
                    annotations[i][j] = f"{ranks[j]}{ranks[i]}o"
                    hand_to_index[f"{ranks[j]}{ranks[i]}o"] = (i, j)
                elif i == j:
                    annotations[i][j] = f"{ranks[j]}{ranks[i]}"
                    hand_to_index[f"{ranks[i]}{ranks[j]}"] = (i, j)

        for id in hand_ids:
            hand_type = describe_holdings(self.hands[id]["hand"])
            result[hand_to_index[hand_type]] += 1

        for id in self.hands:
            hand_type = describe_holdings(self.hands[id]["hand"])
            base_count[hand_to_index[hand_type]] += 1

        if show_frequency:
            for i in range(13):
                for j in range(13):
                    annotations[i][j] += f" {result[i, j]}/{base_count[i, j]}"

        base_count[result == 0] = 1  # avoid DivideZeroError

        fig, ax = plt.subplots(figsize=(13, 10))
        sns.heatmap(result / base_count, annot=annotations, cmap=sns.cubehelix_palette(as_cmap=True), vmin=0, vmax=1, fmt='', annot_kws={'fontsize': 10 if show_frequency else 13}, ax=ax)
        ax.set(xticks=[], yticks=[])
        tf = blended_transform_factory(plt.gca().transAxes, plt.gca().transAxes)
        plt.text(0.85, -0.05, f"{len(self.hands)} hands", fontsize=15, color='gray', transform=tf)

        

# proportional_deviation = self.players_profile.div(list(self.players_profile["_average_"]), axis=0)
#         hm = sns.heatmap(proportional_deviation, annot=self.players_profile, center=1, fmt='.3f', cmap="vlag", annot_kws={'fontsize':7}, vmin=-0.1, vmax=2, cbar=False)
#         hm.set_xticklabels(hm.get_xticklabels(), rotation=45, ha='right', fontsize=9)
#         tf = blended_transform_factory(plt.gca().transAxes, plt.gca().transAxes)
#         plt.text(0.85, -0.25, f"{self.__len__()} hands", fontsize=10, color='gray', transform=tf)