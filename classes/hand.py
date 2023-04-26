from .entry import Entry
from copy import deepcopy
from collections import OrderedDict
from tabulate import tabulate
from .utils import pretty_cards, COLOR, get_rank, EntryList


class Hand:
    def __init__(self, entries: list[Entry]) -> None:
        self.entries = EntryList(entries)
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
                if getattr(self, entry.descriptor)[0]:
                    getattr(self, entry.descriptor)[1] += entry.meta
                else:
                    getattr(self, entry.descriptor)[0] += entry.meta
                stage_change = True
            self[i].stage = _stage

            if entry.descriptor == "rabbit":
                getattr(self, entry.descriptor)[0] = entry.meta
            elif entry.descriptor == "stack count":
                self.starting_stack = entry.meta
                self.num_players = len(entry.name)
            elif entry.descriptor == "collect":
                self.pot += entry.meta
                self.winner[entry.name[0][0]] = entry.meta
            elif entry.descriptor == "own hand":
                self.own_hand = entry.meta
            elif entry.descriptor == "show":
                self.revealed_holdings[entry.name[0][0]] = entry.meta

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
        self._get_pot_at_stage()
        self.board = self._get_board()
    
    def _get_board(self):
        first = self.flop[0] + self.turn[0] + self.river[0] + self.rabbit[0]
        if self.river[1] and self.turn[1] and self.flop[1]:
            second = self.flop[1] + self.turn[1] + self.river[1]
        elif self.river[1] and self.turn[1]:
            second = self.flop[0] + self.turn[1] + self.river[1]
        elif self.river[1]:
            second = self.flop[0] + self.turn[0] + self.river[1]
        else:
            second = []

        return [first, second]

    def _init_attributes(self):
        self.pot = 0
        self.ante = 0
        self.sb = 0
        self.bb = 0
        self.own_hand = None
        self.flop = [[], []]
        self.turn = [[], []]
        self.river = [[], []]
        self.rabbit = [[]]
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
        self.winner = dict()
        self.vpip = []
        self.wtsd = []
        self.f_three_bet = []
        self.f_four_bet = []
        self.f_pfr = []
        self.fold_to_c = []
        self.fold_to_double = []
        self.fold_to_tripple = []

    def _get_pot_at_stage(self):
        preflop_last_layer = None
        flop_last_layer = None
        turn_last_layer = None 
        for i, history in self.bet_history.items():
            if history["stage"] == "flop" and not preflop_last_layer:
                preflop_last_layer = i - 1
            elif history["stage"] == "turn" and not flop_last_layer:
                if not preflop_last_layer:
                    preflop_last_layer = i - 1
                flop_last_layer = i - 1
            elif history["stage"] == "river" and not turn_last_layer:
                if not flop_last_layer:
                    flop_last_layer = i - 1
                turn_last_layer = i - 1
        print(preflop_last_layer, flop_last_layer, turn_last_layer)
        self._preflop_pot = sum(self.bet_history[preflop_last_layer]["bet"].values()) if preflop_last_layer \
            else sum(self.bet_history[max(self.bet_history)]["bet"].values())
        self._flop_pot = sum(self.bet_history[flop_last_layer]["bet"].values()) + self._preflop_pot if flop_last_layer else self._preflop_pot
        self._turn_pot = sum(self.bet_history[turn_last_layer]["bet"].values()) + self._flop_pot if turn_last_layer else self._flop_pot
        print(self._preflop_pot, self._flop_pot, self._turn_pot)
        


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
                        self._describe_bet_stage(i, stage_lead, "four bet")
                    elif self.pfr:
                        self.three_bet = stage_lead
                        self._describe_bet_stage(i, stage_lead, "three bet")
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
                    elif flop_lead and [player[0] for player in self.players].index(stage_lead) < [player[0] for player in self.players].index(flop_lead) and self.bet_history[i - 1]["bet"][stage_lead] == 0:
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
                    if not turn_start and self.c_bet and stage_lead == self.c_bet:
                        self.double_barrel = stage_lead
                        turn_start = True
                        self._describe_bet_stage(i, stage_lead, "double-barrel")
                    elif turn_lead and [player[0] for player in self.players].index(stage_lead) < [player[0] for player in self.players].index(turn_lead) and self.bet_history[i - 1]["bet"][stage_lead] == 0:
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
                    if not river_start and self.double_barrel and stage_lead == self.double_barrel:
                        self.tripple_barrel = stage_lead
                        river_start = True
                        self._describe_bet_stage(i, stage_lead, "triple-barrel")
                    elif river_lead and [player[0] for player in self.players].index(stage_lead) < [player[0] for player in self.players].index(river_lead) and self.bet_history[i - 1]["bet"][stage_lead] == 0:
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
    
    @property
    def _pretty_history(self):
        out_content = []
        headers = ["Action from", "Description"]
        headers.extend([name[0] for name in self.players])
        out_content.append(tabulate([["Hand", self.id], ["Holdings", pretty_cards(*self.own_hand) if self.own_hand else "Not recorded"]], tablefmt="grid"))
        cards = [[None, None, None], [None, None, None]]
        folds = []

        preflop_table = [[detail for detail in history["descriptor"].values()] for history in self.bet_history.values() if history["stage"] == "preflop"]
        for stage, history in zip(preflop_table, [history for history in self.bet_history.values() if history["stage"] == "preflop"]):
            folds_this_round = [name[0] for name in history["fold"]]
            for name in folds_this_round:
                history["bet"][name] = COLOR.fold + str(history['bet'][name]) + COLOR.reset
            for name in folds:
                history["bet"][name] = COLOR.dormant + str(history['bet'][name]) + COLOR.reset
            folds.extend(folds_this_round)
            folds = list(set(folds))
            try:
                history["bet"][history["descriptor"]["name"]] = COLOR.action_highlight + str(history["bet"][history["descriptor"]["name"]]) + COLOR.reset
            except KeyError:
                pass
            stage.extend([history["bet"][name[0]] for name in self.players])
        out_content.append(tabulate(preflop_table, headers=headers, tablefmt='orgtbl'))

        flop_table = [[detail for detail in history["descriptor"].values()] for history in self.bet_history.values() if history["stage"] == "flop"]
        for stage, history in zip(flop_table, [history for history in self.bet_history.values() if history["stage"] == "flop"]):
            folds_this_round = [name[0] for name in history["fold"]]
            for name in folds_this_round:
                history["bet"][name] = COLOR.fold + str(history['bet'][name]) + COLOR.reset
            for name in folds:
                history["bet"][name] = COLOR.dormant + str(history['bet'][name]) + COLOR.reset
            folds.extend(folds_this_round)
            folds = list(set(folds))
            history["bet"][history["descriptor"]["name"]] = COLOR.action_highlight + str(history["bet"][history["descriptor"]["name"]]) + COLOR.reset
            stage.extend([history["bet"][name[0]] for name in self.players])
        if self.flop[0]:
            for i in range(2):
                if self.flop[i]:
                    cards[i][0] = pretty_cards(*self.flop[i])
            if all(card is None for card in cards[1]):
                out_content.append(tabulate([[self._preflop_pot, cards[0][0]]], headers=["Pot", "Flop"], tablefmt="rst"))
            else:
                card_table = [[runout[0]] for runout in cards]
                card_table[0].insert(0, self._preflop_pot)
                card_table[1].insert(0, None)
                out_content.append(tabulate(card_table, headers=["Pot", "flop"], tablefmt="rst"))
        if flop_table:
            out_content.append(tabulate(flop_table, headers=headers, tablefmt='orgtbl'))
        elif self.flop:
            check_around = [None, None]
            stats = [0 for _ in self.players]
            for name in folds:
                stats[[player[0] for player in self.players].index(name)] = COLOR.dormant + "0" + COLOR.reset
            out_content.append(tabulate([check_around + stats], headers=headers, tablefmt='orgtbl'))

        turn_table = [[detail for detail in history["descriptor"].values()] for history in self.bet_history.values() if history["stage"] == "turn"]
        for stage, history in zip(turn_table, [history for history in self.bet_history.values() if history["stage"] == "turn"]):
            folds_this_round = [name[0] for name in history["fold"]]
            for name in folds_this_round:
                history["bet"][name] = COLOR.fold + str(history['bet'][name]) + COLOR.reset
            for name in folds:
                history["bet"][name] = COLOR.dormant + str(history['bet'][name]) + COLOR.reset
            folds.extend(folds_this_round)
            folds = list(set(folds))
            history["bet"][history["descriptor"]["name"]] = COLOR.action_highlight + str(history["bet"][history["descriptor"]["name"]]) + COLOR.reset
            stage.extend([history["bet"][name[0]] for name in self.players])
        if self.turn[0]:
            for i in range(2):
                if self.turn[i]:
                    cards[i][1] = pretty_cards(*self.turn[i])
            if all(card is None for card in cards[1]):
                out_content.append(tabulate([[self._flop_pot] + cards[0][:2]], headers=["Pot", "Flop", "Turn"], tablefmt="rst"))
            else:
                card_table = [runout[:2] for runout in cards]
                card_table[0].insert(0, self._flop_pot)
                card_table[1].insert(0, None)
                out_content.append(tabulate(card_table, headers=["Pot", "flop", "turn"], tablefmt="rst"))
        if turn_table:
            out_content.append(tabulate(turn_table, headers=headers, tablefmt='orgtbl'))
        elif self.turn[0]:
            check_around = [None, None]
            stats = [0 for _ in self.players]
            for name in folds:
                stats[[player[0] for player in self.players].index(name)] = COLOR.dormant + "0" + COLOR.reset
            out_content.append(tabulate([check_around + stats], headers=headers, tablefmt='orgtbl'))

        river_table = [[detail for detail in history["descriptor"].values()] for history in self.bet_history.values() if history["stage"] == "river"]
        for stage, history in zip(river_table, [history for history in self.bet_history.values() if history["stage"] == "river"]):
            folds_this_round = [name[0] for name in history["fold"]]
            for name in folds_this_round:
                history["bet"][name] = COLOR.fold + str(history['bet'][name]) + COLOR.reset
            for name in folds:
                history["bet"][name] = COLOR.dormant + str(history['bet'][name]) + COLOR.reset
            folds.extend(folds_this_round)
            folds = list(set(folds))
            history["bet"][history["descriptor"]["name"]] = COLOR.action_highlight + str(history["bet"][history["descriptor"]["name"]]) + COLOR.reset
            stage.extend([history["bet"][name[0]] for name in self.players])

        if self.river[0]:
            for i in range(2):
                if self.river[i]:
                    cards[i][2] = pretty_cards(*self.river[i])
            if all(card is None for card in cards[1]):
                out_content.append(tabulate([cards[0]], headers=["Flop", "Turn", "River"], tablefmt="rst"))
            else:    
                out_content.append(tabulate(cards, headers=["flop", "turn", "river"], tablefmt="rst"))
        if river_table:
            out_content.append(tabulate(river_table, headers=headers, tablefmt='orgtbl'))
        elif self.river[0]:
            check_around = [None, None]
            stats = [0 for _ in self.players]
            for name in folds:
                stats[[player[0] for player in self.players].index(name)] = COLOR.dormant + "0" + COLOR.reset
            out_content.append(tabulate([check_around + stats], headers=headers, tablefmt='orgtbl'))
        if self.revealed_holdings:
            out_content.append("\n----- Show Down -----")
            if self.board[1]:
                reveal_table = [[name, pretty_cards(*cards), f"{get_rank(self.board[0] + cards)[1]}({get_rank(self.board[0] + cards)[0]})", \
                                 f"{get_rank(self.board[1] + cards)[1]}({get_rank(self.board[1] + cards)[0]})", self.winner.get(name, 0)] for name, cards in self.revealed_holdings.items()]
                reveal_headers = ["Name", "Holdings", "Board 1", "Board 2", "Winnings"]
            else:
                reveal_table = [[name, pretty_cards(*cards), f"{get_rank(self.board[0] + cards)[1]}({get_rank(self.board[0] + cards)[0]})", self.winner.get(name, 0)] for name, cards in self.revealed_holdings.items()]
                reveal_headers = ["Name", "Holdings", "Board 1", "Winnings"]
            for reveal in reveal_table:
                if reveal[0] in folds:
                    reveal[0] = COLOR.dormant + reveal[0] + COLOR.reset
                elif reveal[0] in self.winner:
                    reveal[0] = COLOR.action_highlight + reveal[0] + COLOR.reset
            out_content.append(tabulate(reveal_table, headers=reveal_headers, tablefmt='grid'))

        out_content.append(tabulate([["Winner", ", ".join([name for name in self.winner])], ["Pot", self.pot]], tablefmt='grid'))
        return "\n".join(out_content)

    def debug(self):
        for key, item in self.bet_history.items():
            print(key, item["stage"], item["descriptor"], item["bet"])

    def __getitem__(self, index):
        return self.entries[index]

    def __str__(self, pretty=True):
        return self._pretty_history if pretty else [entry.raw for entry in self]
