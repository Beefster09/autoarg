import functools
from typing import Any, Callable, List, Optional, TypeVar, cast, overload

from .decorators import command
from .generate import generate_argparser
from .types import JSON, Append, Argument, Count, File, OneOrMore, Remainder

__all__ = [
    'Append',
    'Arg',
    'Count',
    'File',
    'JSON',
    'OneOrMore',
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
