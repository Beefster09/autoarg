import functools
from typing import Any, Callable, List, Optional, TypeVar, cast, overload

from .decorators import command
from .generate import generate_argparser
from .types import JSON, Append, Arg, Count, File, OneOrMore, Remainder

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
