import re
from phevaluator.card import Card

class Entry:
    def __init__(self, entry: str) -> None:
        self.raw = entry
        self.name = self._get_name(self.raw)
        self.descriptor = self._define_descriptor()
        self.meta = self._get_meta()
        self.stage = None
        self.pot = None
        
    @staticmethod
    def _get_name(entry: str, return_hash=True):
        full_names = re.findall(r'"([^"]*)"', entry)
        return [full_name.split(" @ ") for full_name in full_names] if return_hash else [[full_name.split(" @ ")[0]] for full_name in full_names]
        
    def _define_descriptor(self):
        descriptor_lookup = {
            "checks": "check",#
            "calls": "call",#
            "folds": "fold",#
            "bets": "bet",#
            "raises": "raise",#
            "Uncalled": "uncalled",#
            "Undealt cards": "rabbit",#
            "shows a": "show",#
            "ending hand": "end",#
            "starting hand": "start",#
            "Player stacks": "stack count",#
            "collected": "collect",#
            "Your hand": "own hand",#
            "ante": "ANTE",#
            "posts a small": "SB",#
            "posts a big": "BB",#
            "Flop": "flop",#
            "Turn": "turn",#
            "River": "river",#
            "stack from": "add stack",#
            "adding": "add stack",#
            "approved the player": "join",#
            "enqueued": "terminate",#
        }
        for key, descriptor in descriptor_lookup.items():
            if key in self.raw:
                return descriptor
        return "admin"

    def _get_meta(self):
        if self.descriptor in ['call', 'raise', 'bet', 'uncalled', 'collect', 'ANTE', 'SB', 'BB', 'join']:
            return int(re.search(r"(?<!')\b\d+\b(?!')", self.raw).group())
        elif self.descriptor in ['flop', 'turn', 'river', 'rabbit']:
            cards = re.search(r'\[([^\[\]]+)\]', self.raw).group()[1:-1].replace(" ", "")
            return self._parse_cards(cards)
        elif self.descriptor == "own hand":
            cards = self.raw.split("is ")[1].replace(" ", "")
            return self._parse_cards(cards)
        elif self.descriptor == "show":
            cards = self.raw.split(" a ")[1][:-1].replace(" ", "")
            return self._parse_cards(cards)
        elif self.descriptor == "start":
            return re.search(r'\(id:\s*(\w+)\)', self.raw).group(1)
        elif self.descriptor == "stack count":
            return self._parse_stacks(self.raw)
        elif self.descriptor == "add stack":
            nums = list(map(int, re.findall(r"(?<!')\b\d+\b(?!')", self.raw)))
            return int(nums[1] - nums[0]) if len(nums) == 2 else nums[0]
        else:
            return None
    
    @staticmethod
    def _parse_cards(cards:str) -> list[Card]:
        unicode_suit_lookup = {
            2660: 's',
            2665: 'h',
            2666: 'd',
            2663: 'c',
            }
        
        if " " in cards:
            cards = cards.replace(" ", "")
        if "," in cards:
                cards = cards.split(",")
        else:
            cards = [cards]
        
        parsed_cards = []
        for card in cards:
            suit = card[-1]
            rank = card[:-1]
            rank = rank if len(rank) != 2 else "T"
            parsed_cards.append(Card(f"{rank}{unicode_suit_lookup[int(hex(ord(suit))[2:].zfill(4))]}"))
        return parsed_cards

    @staticmethod
    def _parse_stacks(entry:str) -> dict:
        stacks = {}
        pattern = re.compile(r'"([^"]*)"')  # Matches everything between double quotes

        for player_stat in entry.split(": ")[1].split('|'):
            player_name = pattern.findall(player_stat)[0].split(" @ ")[0]  # Extract player name from the string
            stack = int(re.findall(r'\((\d+)\)', player_stat)[0])  # Extract player stats from the string
            stacks[player_name] = stack
        return stacks
            
    def __str__(self) -> str:
        return self.raw
