import sys
from typing import NoReturn

from .generate import generate_argparser


def command(maybe_fn=None, /, **opts):
    def _decorator(fn):
        parser = generate_argparser(fn)
        # TODO: modify defaults for function arguments to hide `Arg`s
        return Command(fn, parser)

    if maybe_fn is None:
        return _decorator
    else:
        return _decorator(maybe_fn)


class Command:
    def __init__(self, func, parser):
        self._func = func
        self.parser = parser

    def __call__(self, *args, **kwargs):
        return self._func(*args, **kwargs)

    def main(self) -> NoReturn:
        args = self.parser.parse_args()
        ret = self._func(**vars(args))
        if ret is None:
            sys.exit(0)
        elif isinstance(ret, int):
            sys.exit(ret)
        else:
            sys.exit(int(not ret))  # Truthy -> 0, Falsy -> 1

    def run(self, *args: str):
        try:
            args = self.parser.parse_args(args)
        except SystemExit as err:
            raise TypeError(str(err))
        return self._func(**vars(args))
