import argparse
from enum import Enum
from typing import List, Tuple

from typing_extensions import Literal

import pytest

from autoarg import generate_argparser


def test_toy_example():
    def some_cmd(a, *b, c=False, d=True, e, long, something_with_a_default: int = 3, cat: str = ''):
        pass

    parser = generate_argparser(some_cmd)

    args = parser.parse_args(['abc', 'def', '123', '-c', '-e', 'xyz', '-l', 'abc'])
    assert args.a == 'abc'
    assert args.b == ['def', '123']
    assert args.c
    assert args.e == 'xyz'
    assert args.long == 'abc'
    assert args.something_with_a_default == 3
    assert args.cat == ''


def test_enum():
    class Fruit(Enum):
        Apple = 'apple'
        Banana = 'banana'
        Peach = 'peach'
        Grapes = 'grapes'

    def eat(
        fruit: Fruit,
        *,
        side: Fruit = Fruit.Grapes,
        adverb: str = 'normally'
    ):
        pass

    parser = generate_argparser(eat)

    with pytest.raises(SystemExit):
        parser.parse_args(['tomato'])

    with pytest.raises(SystemExit):
        parser.parse_args(['peach', '-s', 'potato'])

    args = parser.parse_args(['apple', '--side', 'peach', '-a', 'quickly'])
    assert args.fruit is Fruit.Apple
    assert args.side is Fruit.Peach
    assert args.adverb == 'quickly'


def test_literal():
    def something(
        target: str,
        amount: int,
        *,
        mode: Literal['fast', 'slow', 'balanced', 'default'] = 'default',
    ):
        pass

    parser = generate_argparser(something)

    args = parser.parse_args(['tires', '5'])
    assert args.target == 'tires'
    assert args.amount == 5
    assert args.mode == 'default'

    args = parser.parse_args(['clown', '8', '--default'])
    assert args.target == 'clown'
    assert args.amount == 8
    assert args.mode == 'default'

    args = parser.parse_args(['potato', '13', '--fast'])
    assert args.target == 'potato'
    assert args.amount == 13
    assert args.mode == 'fast'

    args = parser.parse_args(['house', '4', '--slow'])
    assert args.target == 'house'
    assert args.amount == 4
    assert args.mode == 'slow'

    args = parser.parse_args(['sword', '0', '--balanced'])
    assert args.target == 'sword'
    assert args.amount == 0
    assert args.mode == 'balanced'

    with pytest.raises(SystemExit):
        parser.parse_args(['beach', '6', '--fast', '--slow'])


def test_tuple():
    def good(a: Tuple[float, int, str]):
        pass

    parser = generate_argparser(good)

    args = parser.parse_args(['3.14', '42', 'best numbers'])
    assert args.a == (3.14, 42, 'best numbers')


def test_tuple_errors():
    def bad(a: Tuple[List[int], int, str]):
        pass

    with pytest.raises(TypeError):
        generate_argparser(bad)
