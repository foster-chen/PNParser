from phevaluator.card import Card
from typing import Union


def pretty_cards(*cards: Union[int, str, Card]):

    cards = [Card(id) for id in list(map(Card.to_id, cards))]
    
    def _get_pretty_card(card: Card):
        suit_unicode_lookup = {
            "s": u"\u2660",
            "h": u"\u2665",
            "d": u"\u2666",
            "c": u"\u2663",}
        RED = "\033[1;31m"
        BLACK = "\033[0;0m"
        prefix = RED if card.describe_suit() in ['h', 'd'] else ''
        postfix = BLACK if card.describe_suit() in ['h', 'd'] else ''
        return prefix + suit_unicode_lookup[card.describe_suit()] + card.describe_rank() + postfix
        

    cards = [Card(id) for id in list(map(Card.to_id, cards))]
    return ", ".join([_get_pretty_card(card) for card in cards])