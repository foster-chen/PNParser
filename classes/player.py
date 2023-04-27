from .utils import raw_attributes, player_attributes
from tabulate import tabulate

class Player:

    raw_stats = raw_attributes()
    player_stats = player_attributes()

    def __init__(self, name) -> None:
        self.n_hands_tracked = 0
        for attribute in self.raw_stats:
            setattr(self, f"_{attribute}", 0)
        self._attack = 0
        self._defend = 0
        for attribute in self.player_stats:
            setattr(self, attribute, None)
        self.name = name

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


    
    

        