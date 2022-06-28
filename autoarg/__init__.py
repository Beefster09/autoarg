import functools
from typing import TypeVar, cast

from .decorators import command
from .generate import generate_argparser
from .types import (
    Append, Argument, Count, InFile, InFileBin, JSON, OneOrMore,
    OutFile, OutFileBin, Remainder,
)

__all__ = [
    'Append',
    'Arg',
    'Count',
    'InFile',
    'InFileBin',
    'JSON',
    'OneOrMore',
    'OutFile',
    'OutFileBin',
    'Remainder',
    'command',
    'generate_argparser'
]


T = TypeVar('T')


@functools.wraps(Argument)
def Arg(value: T = ..., /, **kwargs) -> T:
    return cast(T, Argument(value, **kwargs))
