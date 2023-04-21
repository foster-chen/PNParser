import argparse
from treys import Evaluator
from treys.lookup import LookupTable
from phevaluator import evaluate_cards


def parse_args(args):
    parser = argparse.ArgumentParser()
    parser.add_argument("logs", type=str)

    args = parser.parse_args()
    return args
