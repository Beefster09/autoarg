import functools
from typing import Any, TypeVar, cast, overload, Optional, Callable, List

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


# overloads for type checkers


T = TypeVar('T')


@overload
def Arg(
    *,
    short: Optional[str] = ...,
    long: Optional[List[str]] = None,
    negate_prefix: str = 'no-',
    factory: Optional[Callable[[str], T]] = None,
    help: Optional[str] = None,
    metavar: Optional[str] = None,
) -> Any:
    ...


@overload
def Arg(
    value: T,
    /, *,
    short: Optional[str] = ...,
    long: Optional[List[str]] = None,
    negate_prefix: str = 'no-',
    factory: Optional[Callable[[str], T]] = None,
    help: Optional[str] = None,
    metavar: Optional[str] = None,
) -> T:
    ...


@functools.wraps(Argument)
def Arg(value=..., **kwargs):
    return cast(Any, Argument(value, **kwargs))
