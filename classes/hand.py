from .entry import Entry
from copy import deepcopy

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
        for i, entry in enumerate(self.entries):
            if entry.descriptor in ["flop", "turn", "river"]:
                _stage = entry.descriptor
                setattr(self, entry.descriptor, entry.meta)
            self[i].stage = _stage

            if entry.descriptor == "rabbit":
                setattr(self, entry.descriptor, entry.meta)
            elif entry.descriptor == "stack count":
                self.starting_stack = entry.meta
                self.num_players = len(entry.name)
            elif entry.descriptor == "collect":
                self.pot = entry.meta
                self.winner = entry.name

            if entry.descriptor in ["SB", "BB", "fold", "call", "bet", "raise"]:
                if len(self.players) < self.num_players:
                    self.players.append(entry.name)

            if entry.descriptor in ["ANTE", "SB", "BB"]:
                setattr(self, entry.descriptor.lower(), entry.meta)
                if entry.descriptor in ["SB", "BB"]:
                    self.bet_history[0]["bet"][entry.name[0][0]] = getattr(self, entry.descriptor.lower()) + self.ante
                else:
                    self.bet_history[0]["bet"][entry.name[0][0]] = self.ante
            elif entry.descriptor in ["call", "bet", "raise"]:
                self.bet_history[bet_history_index] = deepcopy(self.bet_history[bet_history_index - 1])
                self.bet_history[bet_history_index]["stage"] = _stage
                if self.bet_history[bet_history_index]["stage"] == "preflop":
                    self.bet_history[bet_history_index]["bet"][entry.name[0][0]] = entry.meta + self.ante
                else:
                    self.bet_history[bet_history_index]["bet"][entry.name[0][0]] += entry.meta
   
                bet_history_index += 1
        self._parse_bet_history()
                
                # print(entry.raw)

    def _init_attributes(self):
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
        self.f_three_bet = None
        self.fold_to_c = None
        self.fold_to_double = None
        self.fold_to_tripple = None
        self.c_bet = None
        self.double_barrel = None
        self.tripple_barrel = None
        self.pfr = None
        self.check_raise = None
        self.bet_history = {0: dict(stage="preflop", bet=dict())}
        self.player_af = dict()
        self.revealed_holdings = dict()
        self.players = []
        self.vpip = []
        self.wtsd = []

    def _parse_bet_history(self):
        preflop = dict()
        flop = dict()
        turn = dict()
        river = dict()
        for i, bet_stage in self.bet_history.items():
            if bet_stage["stage"] == "preflop":
                preflop[i] = self.bet_history[i]
            elif bet_stage["stage"] == "flop":
                flop[i] = self.bet_history[i]
            elif bet_stage["stage"] == "turn":
                turn[i] = self.bet_history[i]
            elif bet_stage["stage"] == "river":
                river[i] = self.bet_history[i]

        # preflop analysis
        preflop_bet_to_reach = self.bb + self.ante
        # preflop_bet_to_reach = sum(list(preflop[0]["bet"].items()))
        preflop_lead = None
        self._describe_bet_stage(0, None, "start")
        preflop_callers = []
        for i, stage in preflop.items():
            if i == 0:
                continue
            stage_lead = max(stage["bet"], key=lambda k: stage["bet"][k])

            if stage["bet"][stage_lead] > preflop_bet_to_reach:
                if self.three_bet is not None:
                    self.four_bet = stage_lead
                    self._describe_bet_stage(i, stage_lead, "four_bet")
                elif self.pfr is not None:
                    self.three_bet = stage_lead
                    self._describe_bet_stage(i, stage_lead, "three_bet")
                else:
                    self.pfr = stage_lead
                    self._describe_bet_stage(i, stage_lead, "pfr")

                preflop_lead = stage_lead
                preflop_bet_to_reach = stage["bet"][stage_lead]
            else:
                self._describe_bet_stage(i, self._identify_change(preflop[i]["bet"], preflop[i - 1]["bet"]), "call")

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
    
    @staticmethod
    def _identify_folds(history: dict):
        # for key, stage in history.items():
        pass

    
    def __getitem__(self, index):
        return self.entries[index]

    def __str__(self):
        return f"Hand {self.id}, won by {self.winner[0][0]}\n{self.bet_history}"
