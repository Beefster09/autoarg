import argparse
from enum import Enum

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

    try:
        parser.parse_args(['tomato'])
    except SystemExit:
        pass
    else:
        assert False

    try:
        parser.parse_args(['peach', '-s', 'potato'])
    except SystemExit:
        pass
    else:
        assert False

    args = parser.parse_args(['apple', '--side', 'peach', '-a', 'quickly'])
    assert args.fruit is Fruit.Apple
    assert args.side is Fruit.Peach
    assert args.adverb == 'quickly'
