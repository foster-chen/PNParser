from .entry import Entry
from copy import deepcopy
from tabulate import tabulate
from .utils import pretty_cards, COLOR, get_rank, EntryList, raw_attributes

class Hand:
    def __init__(self, entries: list[Entry]) -> None:
        self.entries = EntryList(entries)
        assert self.entries[0].descriptor == "start"
        self.id = self.entries[0].meta
        self.own_player_id = None
        try:
            self.dealer = self.entries[0].name[0]
        except IndexError:
            self.dealer = None

        self._init_attributes()
        for entry in self.entries:
            if entry.descriptor in ["SB", "BB", "fold", "call", "bet", "raise"]:
                if entry.name[0][0] not in self.players:
                    self.players.append(entry.name[0][0])
                    self.num_players += 1
        self.bet_history = {0: dict(stage="preflop", bet={name: 0 for name in self.players})}

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
            elif entry.descriptor == "collect":
                self.pot += entry.meta
                try:
                    self.winner[entry.name[0][0]] += entry.meta
                except KeyError:
                    self.winner[entry.name[0][0]] = entry.meta
            elif entry.descriptor == "own hand":
                self.own_hand = entry.meta
            elif entry.descriptor == "show":
                self.revealed_holdings[entry.name[0][0]] = entry.meta

            if entry.descriptor in ["ANTE", "SB", "BB"]:
                setattr(self, entry.descriptor.lower(), entry.meta)
                if entry.descriptor in ["SB", "BB"]:
                    self.bet_history[0]["bet"][entry.name[0][0]] = getattr(self, entry.descriptor.lower()) + self.ante
                else:
                    self.bet_history[0]["bet"][entry.name[0][0]] = self.ante
                self.bet_history[0]["fold"] = []
            elif entry.descriptor in ["call", "bet", "raise"]:
                if _stage == "preflop":
                    self.vpip.append(entry.name[0][0])
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
                self.bet_history[bet_history_index - 1]["fold"].append(entry.name[0][0])
        self.bet_history[max(self.bet_history) + 1] = dict(stage="end")

        self.player_aggression_factor = {player:{"attack": 0, "defend": 0} for player in self.players}
        self.check_raise = {player:0 for player in self.players}
        self.call_without_checkraise = {player:0 for player in self.players}
        self._parse_bet_history()
        self._get_pot_at_stage()
        self.board = self._get_board()
        self.vpip = list(set(self.vpip))
    
    def _get_board(self):
        first = self.flop[0] + self.turn[0] + self.river[0]
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
        self.num_players = 0
        self.own_hand = None
        self.flop = [[], []]
        self.turn = [[], []]
        self.river = [[], []]
        self.rabbit = [[]]
        self.three_bet = None
        self.four_bet = None
        self.five_bet = None
        self.c_bet = None
        self.double_barrel = None
        self.triple_barrel = None
        self.pfr = None
        self.raise_against_c = None
        self.raise_against_double = None
        self.raise_against_triple = None
        self.revealed_holdings = dict()
        self.players = []
        self.winner = dict()
        self.vpip = []
        self.join_flop = []
        self.wtsd = []
        self.fold_to_three_bet = []
        self.fold_to_four_bet = []
        self.fold_to_pfr = []
        self.fold_to_c = []
        self.fold_to_double = []
        self.fold_to_triple = []
        self.call_three_bet = []
        self.call_four_bet = []
        self.call_pfr = []
        self.call_c = []
        self.call_double = []
        self.call_triple = []

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
            elif history["stage"] in ["river", "end"] and not turn_last_layer:
                if not flop_last_layer:
                    flop_last_layer = i - 1
                if not preflop_last_layer:
                    preflop_last_layer = i - 1
                turn_last_layer = i - 1
        self._preflop_pot = sum(self.bet_history[preflop_last_layer]["bet"].values()) if preflop_last_layer \
            else sum(self.bet_history[max(self.bet_history) - 1]["bet"].values())
        self._flop_pot = sum(self.bet_history[flop_last_layer]["bet"].values()) + self._preflop_pot if flop_last_layer and flop_last_layer != preflop_last_layer else self._preflop_pot
        self._turn_pot = sum(self.bet_history[turn_last_layer]["bet"].values()) + self._flop_pot if turn_last_layer and turn_last_layer != flop_last_layer else self._flop_pot
        
    def _parse_bet_history(self):
        preflop_bet_to_reach = self.bb + self.ante
        flop_bet_to_reach = 0
        turn_bet_to_reach = 0
        river_bet_to_reach = 0
        self.preflop_lead = None
        self.flop_lead = None
        self.turn_lead = None
        self.river_lead = None
        folds = []

        _preflop_end_layer = None
        _river_end_layer = None
        
        self._describe_bet_stage(0, None, "start")
        flop_start, turn_start, river_start = False, False, False
        for i, stage in self.bet_history.items():
            if stage["stage"] != "preflop" and not _preflop_end_layer \
                        and len([name for name, bet in self.bet_history[i - 1]["bet"].items() if bet == preflop_bet_to_reach]) > 1:
                _preflop_end_layer = i - 1
            if not _river_end_layer and stage["stage"] == "end" and self.bet_history[i - 1]["stage"] == "river" \
                        and len([name for name, bet in self.bet_history[i - 1]["bet"].items() if bet == river_bet_to_reach]) > 1:
                _river_end_layer = i - 1

            if i == 0 or i == max(self.bet_history):
                continue
            folds.extend(stage["fold"])
            stage_lead = max(stage["bet"], key=lambda k: stage["bet"][k])
            # analyze PFR, 3Bet, 4Bet, Fold to PFR, Fold to 3Bet, Fold to 4Bet on preflop
            if stage["stage"] == "preflop":
                if stage["bet"][stage_lead] > preflop_bet_to_reach:
                    if self.five_bet:
                        self._describe_bet_stage(i, stage_lead, "5-Bet+")
                    elif self.four_bet:
                        self.five_bet = stage_lead
                        self._describe_bet_stage(i, stage_lead, "5-Bet")
                    elif self.three_bet:
                        self.four_bet = stage_lead
                        self._describe_bet_stage(i, stage_lead, "4-Bet")
                    elif self.pfr:
                        self.three_bet = stage_lead
                        self._describe_bet_stage(i, stage_lead, "3-Bet")
                    else:
                        self.pfr = stage_lead
                        self._describe_bet_stage(i, stage_lead, "PFR")

                    self.preflop_lead = stage_lead
                    preflop_bet_to_reach = stage["bet"][stage_lead]
                else:
                    caller = self._identify_change(self.bet_history[i]["bet"], self.bet_history[i - 1]["bet"])
                    if self.four_bet:
                        self.call_four_bet.append(caller)
                    elif self.three_bet:
                        self.call_three_bet.append(caller)
                    elif self.pfr:
                        self.call_pfr.append(caller)
                    self._describe_bet_stage(i, caller, "Call")
                
                if stage["fold"]:
                    if self.four_bet:
                        self.fold_to_four_bet.extend(stage["fold"])
                    elif self.three_bet:
                        self.fold_to_three_bet.extend(stage["fold"])
                    elif self.pfr:
                        self.fold_to_pfr.extend(stage["fold"])
            # analyze C-bet, fold to C-bet on flop
            elif stage["stage"] == "flop":
                if stage["bet"][stage_lead] > flop_bet_to_reach:
                    self.player_aggression_factor[stage_lead]["attack"] += 1
                    if not flop_start:
                        if stage_lead == self.preflop_lead:
                            self.c_bet = stage_lead
                            self._describe_bet_stage(i, stage_lead, "C-Bet")
                        elif self.pfr and [player for player in self.players].index(stage_lead) < [player for player in self.players].index(self.pfr):
                            self._describe_bet_stage(i, stage_lead, "Donk")
                        else:
                            self._describe_bet_stage(i, stage_lead, "Bet")
                    elif self.flop_lead and [player for player in self.players].index(stage_lead) < [player for player in self.players].index(self.flop_lead) \
                                                        and self.bet_history[i - 1]["bet"][stage_lead] == 0:
                        if not self.raise_against_c and self.c_bet:
                            self.raise_against_c = stage_lead
                        self.check_raise[stage_lead] += 1
                        self._describe_bet_stage(i, stage_lead, "Check-Raise")
                    elif self.flop_lead:
                        if not self.raise_against_c and self.c_bet:
                            self.raise_against_c = stage_lead
                        self._describe_bet_stage(i, stage_lead, "Raise")
                    else:
                        self._describe_bet_stage(i, stage_lead, "Bet")
                    self.flop_lead = stage_lead
                    flop_bet_to_reach = stage["bet"][stage_lead]
                else:
                    caller = self._identify_change(self.bet_history[i]["bet"], self.bet_history[i - 1]["bet"])
                    self.player_aggression_factor[caller]["defend"] += 1
                    if self.flop_lead and [player for player in self.players].index(caller) < [player for player in self.players].index(self.flop_lead) \
                                                        and self.bet_history[i - 1]["bet"][caller] == 0:
                         self.call_without_checkraise[caller] += 1
                    if self.c_bet:
                        self.call_c.append(caller)
                    self._describe_bet_stage(i, caller, "Call")
                flop_start = True

                if stage["fold"] and self.c_bet:
                    self.fold_to_c.extend(stage["fold"])

            # analyze double-barrel, fold to double barrel on turn
            elif stage["stage"] == "turn":
                if stage["bet"][stage_lead] > turn_bet_to_reach:
                    self.player_aggression_factor[stage_lead]["attack"] += 1
                    if not turn_start and self.c_bet:
                        if stage_lead == self.c_bet:
                            self.double_barrel = stage_lead
                            self._describe_bet_stage(i, stage_lead, "2-Barrel")
                        elif self.c_bet and [player for player in self.players].index(stage_lead) < [player for player in self.players].index(self.c_bet):
                            self._describe_bet_stage(i, stage_lead, "Donk")
                        else:
                            self._describe_bet_stage(i, stage_lead, "Bet")
                    elif self.turn_lead and [player for player in self.players].index(stage_lead) < [player for player in self.players].index(self.turn_lead) \
                                         and self.bet_history[i - 1]["bet"][stage_lead] == 0:
                        if not self.raise_against_double and self.double_barrel:
                            self.raise_against_double = stage_lead
                        self.check_raise[stage_lead] += 1
                        self._describe_bet_stage(i, stage_lead, "Check-Raise")
                    elif self.turn_lead:
                        if not self.raise_against_double and self.double_barrel:
                            self.raise_against_double = stage_lead
                        self._describe_bet_stage(i, stage_lead, "Raise")
                    else:
                        self._describe_bet_stage(i, stage_lead, "Bet")
                    self.turn_lead = stage_lead
                    turn_bet_to_reach = stage["bet"][stage_lead]
                else:
                    caller = self._identify_change(self.bet_history[i]["bet"], self.bet_history[i - 1]["bet"])
                    self.player_aggression_factor[caller]["defend"] += 1
                    if self.turn_lead and [player for player in self.players].index(caller) < [player for player in self.players].index(self.turn_lead) \
                                                        and self.bet_history[i - 1]["bet"][caller] == 0:
                         self.call_without_checkraise[caller] += 1
                    if self.double_barrel:
                        self.call_double.append(caller)
                    self._describe_bet_stage(i, caller, "Call")
                turn_start = True

                if stage["fold"] and self.double_barrel:
                    self.fold_to_double.extend(stage["fold"])

            # analyze triple-barrel, fold to triple-barrel
            elif stage["stage"] == "river":
                if stage["bet"][stage_lead] > river_bet_to_reach:
                    self.player_aggression_factor[stage_lead]["attack"] += 1
                    if not river_start and self.double_barrel:
                        if stage_lead == self.double_barrel:
                            self.triple_barrel = stage_lead
                            self._describe_bet_stage(i, stage_lead, "3-Barrel")
                        elif self.double_barrel and [player for player in self.players].index(stage_lead) < [player for player in self.players].index(self.double_barrel):
                            self._describe_bet_stage(i, stage_lead, "Donk")
                        else:
                            self._describe_bet_stage(i, stage_lead, "Bet")
                    elif self.river_lead and [player for player in self.players].index(stage_lead) < [player for player in self.players].index(self.river_lead) and self.bet_history[i - 1]["bet"][stage_lead] == 0:
                        if not self.raise_against_triple and self.triple_barrel:
                            self.raise_against_triple = stage_lead
                        self.check_raise[stage_lead] += 1
                        self._describe_bet_stage(i, stage_lead, "Check-Raise")
                    elif self.river_lead:
                        if not self.raise_against_triple and self.triple_barrel:
                            self.raise_against_triple = stage_lead
                        self._describe_bet_stage(i, stage_lead, "Raise")
                    else:
                        self._describe_bet_stage(i, stage_lead, "Bet")
                    self.river_lead = stage_lead
                    river_bet_to_reach = stage["bet"][stage_lead]
                else:
                    caller = self._identify_change(self.bet_history[i]["bet"], self.bet_history[i - 1]["bet"])
                    self.player_aggression_factor[caller]["defend"] += 1
                    if self.river_lead and [player for player in self.players].index(caller) < [player for player in self.players].index(self.river_lead) \
                                                        and self.bet_history[i - 1]["bet"][caller] == 0:
                         self.call_without_checkraise[caller] += 1
                    if self.triple_barrel:
                        self.call_triple.append(caller)
                    self._describe_bet_stage(i, caller, "Call")
                river_start = True

                if stage["fold"] and self.triple_barrel:
                    self.fold_to_triple.extend(stage["fold"])

        if _preflop_end_layer:
            self.join_flop.extend([name for name, bet in self.bet_history[_preflop_end_layer]["bet"].items() if bet == preflop_bet_to_reach])
        if _river_end_layer:
            self.wtsd.extend([name for name, bet in self.bet_history[_river_end_layer]["bet"].items() if bet == river_bet_to_reach])

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
        headers.extend([name for name in self.players])
        out_content.append(tabulate([["Hand", self.id], ["SB:BB:ANTE", f"{self.sb}:{self.bb}:{self.ante}"], ["Holdings", pretty_cards(*self.own_hand) if self.own_hand else "Not recorded"]], tablefmt="grid"))
        cards = [[None, None, None], [None, None, None]]
        folds = []

        preflop_table = [[detail for detail in history["descriptor"].values()] for history in self.bet_history.values() if history["stage"] == "preflop"]
        for stage, history in zip(preflop_table, [history for history in self.bet_history.values() if history["stage"] == "preflop"]):
            history = deepcopy(history)
            folds_this_round = [name for name in history["fold"]]
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
            stage.extend([history["bet"][name] for name in self.players])
        out_content.append(tabulate(preflop_table, headers=headers, tablefmt='orgtbl'))

        flop_table = [[detail for detail in history["descriptor"].values()] for history in self.bet_history.values() if history["stage"] == "flop"]
        for stage, history in zip(flop_table, [history for history in self.bet_history.values() if history["stage"] == "flop"]):
            history = deepcopy(history)
            folds_this_round = [name for name in history["fold"]]
            for name in folds_this_round:
                history["bet"][name] = COLOR.fold + str(history['bet'][name]) + COLOR.reset
            for name in folds:
                history["bet"][name] = COLOR.dormant + str(history['bet'][name]) + COLOR.reset
            folds.extend(folds_this_round)
            folds = list(set(folds))
            history["bet"][history["descriptor"]["name"]] = COLOR.action_highlight + str(history["bet"][history["descriptor"]["name"]]) + COLOR.reset
            stage.extend([history["bet"][name] for name in self.players])
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
        elif self.flop[0]:
            check_around = [None, None]
            stats = [0 for _ in self.players]
            for name in folds:
                stats[[player for player in self.players].index(name)] = COLOR.dormant + "0" + COLOR.reset
            out_content.append(tabulate([check_around + stats], headers=headers, tablefmt='orgtbl'))

        turn_table = [[detail for detail in history["descriptor"].values()] for history in self.bet_history.values() if history["stage"] == "turn"]
        for stage, history in zip(turn_table, [history for history in self.bet_history.values() if history["stage"] == "turn"]):
            history = deepcopy(history)
            folds_this_round = [name for name in history["fold"]]
            for name in folds_this_round:
                history["bet"][name] = COLOR.fold + str(history['bet'][name]) + COLOR.reset
            for name in folds:
                history["bet"][name] = COLOR.dormant + str(history['bet'][name]) + COLOR.reset
            folds.extend(folds_this_round)
            folds = list(set(folds))
            history["bet"][history["descriptor"]["name"]] = COLOR.action_highlight + str(history["bet"][history["descriptor"]["name"]]) + COLOR.reset
            stage.extend([history["bet"][name] for name in self.players])
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
                stats[[player for player in self.players].index(name)] = COLOR.dormant + "0" + COLOR.reset
            out_content.append(tabulate([check_around + stats], headers=headers, tablefmt='orgtbl'))

        river_table = [[detail for detail in history["descriptor"].values()] for history in self.bet_history.values() if history["stage"] == "river"]
        for stage, history in zip(river_table, [history for history in self.bet_history.values() if history["stage"] == "river"]):
            history = deepcopy(history)
            folds_this_round = [name for name in history["fold"]]
            for name in folds_this_round:
                history["bet"][name] = COLOR.fold + str(history['bet'][name]) + COLOR.reset
            for name in folds:
                history["bet"][name] = COLOR.dormant + str(history['bet'][name]) + COLOR.reset
            folds.extend(folds_this_round)
            folds = list(set(folds))
            history["bet"][history["descriptor"]["name"]] = COLOR.action_highlight + str(history["bet"][history["descriptor"]["name"]]) + COLOR.reset
            stage.extend([history["bet"][name] for name in self.players])

        if self.river[0]:
            for i in range(2):
                if self.river[i]:
                    cards[i][2] = pretty_cards(*self.river[i])
            if all(card is None for card in cards[1]):
                out_content.append(tabulate([[self._turn_pot] + cards[0]], headers=["Pot", "Flop", "Turn", "River"], tablefmt="rst"))
            else:    
                card_table = cards
                card_table[0].insert(0, self._turn_pot)
                card_table[1].insert(0, None)
                out_content.append(tabulate(card_table, headers=["Pot", "flop", "turn", "river"], tablefmt="rst"))
        if river_table:
            out_content.append(tabulate(river_table, headers=headers, tablefmt='orgtbl'))
        elif self.river[0]:
            check_around = [None, None]
            stats = [0 for _ in self.players]
            for name in folds:
                stats[[player for player in self.players].index(name)] = COLOR.dormant + "0" + COLOR.reset
            out_content.append(tabulate([check_around + stats], headers=headers, tablefmt='orgtbl'))
        if self.revealed_holdings:
            out_content.append("\n----- Show Down -----")
            if self.board[1]:
                reveal_table = [[name, pretty_cards(*cards), f"{get_rank(self.board[0] + cards)[1]}({get_rank(self.board[0] + cards)[0]})", \
                                 f"{get_rank(self.board[1] + cards)[1]}({get_rank(self.board[1] + cards)[0]})", self.winner.get(name, 0)] for name, \
                                 cards in self.revealed_holdings.items()]
                reveal_headers = ["Name", "Holdings", "Board 1", "Board 2", "Winnings"]
            else:
                try:
                    reveal_table = [[name, pretty_cards(*cards), f"{get_rank(self.board[0] + cards)[1]}({get_rank(self.board[0] + cards)[0]})", \
                                    self.winner.get(name, 0)] for name, cards in self.revealed_holdings.items()]
                    reveal_headers = ["Name", "Holdings", "Board 1", "Winnings"]
                except ValueError:
                    reveal_table = [[name, pretty_cards(*cards), self.winner.get(name, 0)] for name, cards in self.revealed_holdings.items()]
                    reveal_headers = ["Name", "Holdings", "Winnings"]
            for reveal in reveal_table:
                if reveal[0] in folds:
                    reveal[0] = COLOR.dormant + reveal[0] + COLOR.reset
                elif reveal[0] in self.winner:
                    reveal[0] = COLOR.action_highlight + reveal[0] + COLOR.reset
            out_content.append(tabulate(reveal_table, headers=reveal_headers, tablefmt='grid'))

        if self.board[1]:
            out_content.append(tabulate([[pretty_cards(*self.board[0])], [pretty_cards(*self.board[1])]], headers=["Board"], tablefmt='rst'))
        elif self.rabbit[0] and self.board[0]:
            rabbit = [[pretty_cards(*self.board[0]), pretty_cards(*self.rabbit[0])]]
            out_content.append(tabulate(rabbit, headers=["Board", "Rabbit"], tablefmt='rst'))
        elif self.rabbit[0]:
            out_content.append(tabulate([[pretty_cards(*self.rabbit[0])]], headers=["Rabbit"], tablefmt='rst'))
        else:
            out_content.append(tabulate([[pretty_cards(*self.board[0])]], headers=["Board"], tablefmt='rst'))
        out_content.append(tabulate([["Winner", ", ".join([name for name in self.winner])], ["Pot", self.pot]], tablefmt='grid'))
        return "\n".join(out_content)

    def __getitem__(self, index):
        return self.entries[index]

    def __str__(self, pretty=True):
        return self._pretty_history if pretty else [entry.raw for entry in self]

    def show_raw_stats(self):
        lst = [getattr(self, attribute) for attribute in raw_attributes()]
        for i, attribute in enumerate(raw_attributes()):
            print(f"{attribute}: {lst[i]}")
