from .entry import Entry
from copy import deepcopy
from collections import OrderedDict

class Hand:
    def __init__(self, entries: list[Entry]) -> None:
        self.entries = entries
        assert self.entries[0].descriptor == "start"
        self.id = self.entries[0].meta
        try:
            self.dealer = self.entries[0].name[0]
        except IndexError:
            self.dealer = None
        self._init_attributes()

        _stage = "preflop"
        bet_history_index = 1
        stage_change = False
        for i, entry in enumerate(self.entries):
            if entry.descriptor in ["flop", "turn", "river"]:
                _stage = entry.descriptor
                setattr(self, entry.descriptor, entry.meta)
                stage_change = True
            self[i].stage = _stage

            if entry.descriptor == "rabbit":
                setattr(self, entry.descriptor, entry.meta)
            elif entry.descriptor == "stack count":
                self.starting_stack = entry.meta
                self.num_players = len(entry.name)
            elif entry.descriptor == "collect":
                self.pot += entry.meta
                self.winner.append(entry.name[0])

            if entry.descriptor in ["SB", "BB", "fold", "call", "bet", "raise"]:
                if len(self.players) < self.num_players:
                    self.players.append(entry.name[0])

            if entry.descriptor in ["ANTE", "SB", "BB"]:
                setattr(self, entry.descriptor.lower(), entry.meta)
                if entry.descriptor in ["SB", "BB"]:
                    self.bet_history[0]["bet"][entry.name[0][0]] = getattr(self, entry.descriptor.lower()) + self.ante
                else:
                    self.bet_history[0]["bet"][entry.name[0][0]] = self.ante
                self.bet_history[0]["fold"] = []
            elif entry.descriptor in ["call", "bet", "raise"]:
                self.bet_history[bet_history_index] = deepcopy(self.bet_history[bet_history_index - 1])
                self.bet_history[bet_history_index]["fold"] = []
                self.bet_history[bet_history_index]["stage"] = _stage
                if _stage == "preflop":
                    self.bet_history[bet_history_index]["bet"][entry.name[0][0]] = entry.meta + self.ante
                else:
                    if stage_change:
                        for key in self.bet_history[bet_history_index]["bet"]:
                            self.bet_history[bet_history_index]["bet"][key] = 0
                        stage_change = False
                    self.bet_history[bet_history_index]["bet"][entry.name[0][0]] = entry.meta
                bet_history_index += 1
            elif entry.descriptor == "fold":
                self.bet_history[bet_history_index - 1]["fold"].append(entry.name[0])

        self._parse_bet_history()

    def _init_attributes(self):
        self.pot = 0
        self.ante = None
        self.sb = None
        self.bb = None
        self.flop = None
        self.turn = None
        self.river = None
        self.rabbit = None
        self.preflop_aggressor = None
        self.three_bet = None
        self.four_bet = None
        self.c_bet = None
        self.double_barrel = None
        self.tripple_barrel = None
        self.pfr = None
        self.check_raise = None
        self.bet_history = {0: dict(stage="preflop", bet=dict())}
        self.player_af = dict()
        self.revealed_holdings = dict()
        self.players = []
        self.winner = []
        self.vpip = []
        self.wtsd = []
        self.f_three_bet = []
        self.f_four_bet = []
        self.f_pfr = []
        self.fold_to_c = []
        self.fold_to_double = []
        self.fold_to_tripple = []

    def _parse_bet_history(self):
        player_active = {player[0]: True for player in self.players}

        preflop_bet_to_reach = self.bb + self.ante
        flop_bet_to_reach = 0
        turn_bet_to_reach = 0
        river_bet_to_reach = 0
        preflop_lead = None
        flop_lead = None
        turn_lead = None
        river_lead = None
        
        self._describe_bet_stage(0, None, "start")
        flop_start, turn_start, river_start = False, False, False
        for i, stage in self.bet_history.items():
            if i == 0:
                continue
            stage_lead = max(stage["bet"], key=lambda k: stage["bet"][k])
            # analyze PFR, 3Bet, 4Bet, Fold to PFR, Fold to 3Bet, Fold to 4Bet on preflop
            if stage["stage"] == "preflop":
                if stage["bet"][stage_lead] > preflop_bet_to_reach:
                    if self.three_bet:
                        self.four_bet = stage_lead
                        self._describe_bet_stage(i, stage_lead, "four_bet")
                    elif self.pfr:
                        self.three_bet = stage_lead
                        self._describe_bet_stage(i, stage_lead, "three_bet")
                    else:
                        self.pfr = stage_lead
                        self._describe_bet_stage(i, stage_lead, "pfr")

                    preflop_lead = stage_lead
                    preflop_bet_to_reach = stage["bet"][stage_lead]
                else:
                    self._describe_bet_stage(i, self._identify_change(self.bet_history[i]["bet"], self.bet_history[i - 1]["bet"]), "call")
                
                if stage["fold"]:
                    if self.four_bet:
                        self.f_four_bet.extend(stage["fold"])
                    elif self.three_bet:
                        self.f_three_bet.extend(stage["fold"])
                    elif self.pfr:
                        self.f_pfr.extend(stage["fold"])
            # analyze C-bet, fold to C-bet on flop
            elif stage["stage"] == "flop":
                if stage["bet"][stage_lead] > flop_bet_to_reach:
                    if not flop_start and stage_lead == preflop_lead:
                        self.c_bet = stage_lead
                        flop_start = True
                        self._describe_bet_stage(i, stage_lead, "C-bet")
                    elif [player[0] for player in self.players].index(stage_lead) < [player[0] for player in self.players].index(flop_lead) and stage["bet"][stage_lead] == 0:
                        self._describe_bet_stage(i, stage_lead, "check raise")
                    elif flop_lead:
                        self._describe_bet_stage(i, stage_lead, "raise")
                    else:
                        self._describe_bet_stage(i, stage_lead, "bet")
                    flop_lead = stage_lead
                    flop_bet_to_reach = stage["bet"][stage_lead]
                else:
                    self._describe_bet_stage(i, self._identify_change(self.bet_history[i]["bet"], self.bet_history[i - 1]["bet"]), "call")

                if stage["fold"]:
                    if self.c_bet:
                        self.fold_to_c.extend(stage["fold"])
            # analyze double-barrel, fold to double barrel on turn
            elif stage["stage"] == "turn":
                if stage["bet"][stage_lead] > turn_bet_to_reach:
                    if not turn_start and stage_lead == flop_lead:
                        self.double_barrel = stage_lead
                        turn_start = True
                        self._describe_bet_stage(i, stage_lead, "double-barrel")
                    elif [player[0] for player in self.players].index(stage_lead) < [player[0] for player in self.players].index(turn_lead) and stage["bet"][stage_lead] == 0:
                        self._describe_bet_stage(i, stage_lead, "check raise")
                    elif turn_lead:
                        self._describe_bet_stage(i, stage_lead, "raise")
                    else:
                        self._describe_bet_stage(i, stage_lead, "bet")
                    turn_lead = stage_lead
                    turn_bet_to_reach = stage["bet"][stage_lead]
                else:
                    self._describe_bet_stage(i, self._identify_change(self.bet_history[i]["bet"], self.bet_history[i - 1]["bet"]), "call")

                if stage["fold"]:
                    if self.double_barrel:
                        self.fold_to_double.extend(stage["fold"])
            # analyze triple-barrel, fold to triple-barrel
            elif stage["stage"] == "river":
                if stage["bet"][stage_lead] > river_bet_to_reach:
                    if not river_start and stage_lead == turn_lead:
                        self.tripple_barrel = stage_lead
                        river_start = True
                        self._describe_bet_stage(i, stage_lead, "triple-barrel")
                    elif [player[0] for player in self.players].index(stage_lead) < [player[0] for player in self.players].index(river_lead) and stage["bet"][stage_lead] == 0:
                        self._describe_bet_stage(i, stage_lead, "check raise")
                    elif river_lead:
                        self._describe_bet_stage(i, stage_lead, "raise")
                    else:
                        self._describe_bet_stage(i, stage_lead, "bet")
                    river_lead = stage_lead
                    river_bet_to_reach = stage["bet"][stage_lead]
                else:
                    self._describe_bet_stage(i, self._identify_change(self.bet_history[i]["bet"], self.bet_history[i - 1]["bet"]), "call")

                if stage["fold"]:
                    if self.tripple_barrel:
                        self.fold_to_tripple.extend(stage["fold"])


            # if max(list(stage["bet"].items()))
        # print(f"preflop: {preflop}\nflop: {flop}\nturn: {turn}\nriver: {river}")

    def _describe_bet_stage(self, i, name, descriptor):
        self.bet_history[i]["descriptor"] = {"name": name, "action": descriptor}
    
    @staticmethod
    def _identify_change(stage1, stage2):
        for key in stage1:
            if stage1[key] != stage2[key]:
                return key
        return None
    
    def _identify_folds(self):
        def next_player(current_player):
            return 0 if current_player + 1 == self.num_players else current_player + 1
        player_status = {i: {"name": self.players[i][0], "active": True} for i in range(self.num_players)}
        player_to_act = 2
        stage = "preflop"
        
        for key in self.bet_history:
            if key == 0:
                continue
            if self.bet_history[key]["stage"] != stage:
                stage = self.bet_history[key]["stage"]
                player_to_act = 0
            player_of_interest = [name[0] for name in self.players].index( \
                self._identify_change(self.bet_history[key]["bet"], self.bet_history[key - 1]["bet"]))
            # print(key, self.bet_history[key], self._identify_change(self.bet_history[key]["bet"], self.bet_history[key - 1]["bet"]))
            if player_of_interest == player_to_act:
                player_to_act = next_player(player_to_act)
                continue
            else:
                while player_to_act != player_of_interest:
                    if player_status[player_to_act]["active"]:
                        self.bet_history[key]["fold"].append(self.players[player_to_act])
                        player_status[player_to_act]["active"] = False
                        player_to_act = next_player(player_to_act)
                    else:
                        player_to_act = next_player(player_to_act)
    
    def debug(self):
        for key, item in self.bet_history.items():
            print(key, item["stage"], item["descriptor"], item["bet"])

        

    
    def __getitem__(self, index):
        return self.entries[index]

    def __str__(self):
        return f"Hand {self.id}, won by {self.winner}\n{self.bet_history}"
