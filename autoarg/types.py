from enum import Enum
from typing import (
    IO,
    Any,
    Callable,
    Dict,
    Generic,
    List,
    Optional,
    Tuple,
    Type,
    TypeVar,
    Union,
    cast,
    overload,
)

from typing_extensions import Annotated, Literal, get_args, get_origin

__all__ = [
    'Append',
    'Arg',
    'Count',
    'File',
    'JSON',
    'OneOrMore',
    'Remainder',
]


T = TypeVar('T')
T_Literal = TypeVar('T_Literal', bound=Literal['dummy'])
T_Enum = TypeVar('T_Enum', bound=Enum)


# Annotated types for special cases


class OneOrMore:
    def __class_getitem__(cls, T):
        return Annotated[T, '+']


class Append:
    def __class_getitem__(cls, T):
        return Annotated[List[T], 'append']


class File:
    def __class_getitem__(cls, mode: str):
        return Annotated[IO, mode]


Count = Annotated[int, 'count']
Level = Annotated[int, 'level']  # creates 2 count arguments: one for up, one for down
Verbosity = Annotated[int, 'level', 'verbosity']  # same as level, but with sensible defaults
Remainder = Annotated[List[str], 'remainder']
JSON = Annotated[Any, 'json']


def _sensible_default_value(typ: Type) -> Any:
    if typ is bool:
        return False

    if get_origin(typ) is Annotated:
        T, *annotations = get_args(typ)
        if T is int:
            if 'count' in annotations or 'level' in annotations:
                return 0
        if get_origin(T) is list:
            if 'remainder' in annotations or 'append' in annotations:
                return []

    return ...


class _AnnotatedValue:
    """Internal container for holding data alongside default values
    """
    def __init__(
        self,
        value: Any = ...,
        /,
        **annotations
    ):
        self.value = value
        self._annotations = annotations

    def get(self, key, default=None):
        return self._annotations.get(key, default)

    def __getitem__(self, key):
        return self._annotations[key]

    def __contains__(self, key):
        return key in self._annotations


# A utility public wrapper for _AnnotatedValue
# with some sensible overloads for various special types
# mostly for documentation - it probably won't make sense to type checkers


@overload
def Arg(
    *,
    short: Optional[str] = None,
    long: Optional[List[str]] = None,
    help: Optional[str] = None,
    metavar: Optional[str] = None,
) -> Count:
    ...


@overload
def Arg(
    default: int = 0,
    /, *,
    up_short: Optional[str] = None,
    up_long: Optional[List[str]] = None,
    down_short: Optional[str] = None,
    down_long: Optional[List[str]] = None,
    min: Optional[int] = None,
    max: Optional[int] = None,
    help: Optional[str] = None,
    metavar: Optional[str] = None,
) -> Level:
    ...


@overload
def Arg(
    default: bool = False,
    /, *,
    short: Optional[str] = None,
    long: Optional[List[str]] = None,
    help: Optional[str] = None,
) -> bool:
    ...


@overload
def Arg(
    default: bool = False,
    /, *,
    short: Optional[str] = None,
    negate_prefix: str,
    help: Optional[str] = None,
) -> bool:
    ...


@overload
def Arg(
    default: Optional[T_Literal] = None,
    /, *,
    shorts: Dict[T_Literal, str] = {},
    longs: Dict[T_Literal, List[str]] = {},
    help: Optional[str] = None,
) -> T_Literal:
    ...


@overload
def Arg(
    default: Optional[T_Enum] = None,
    /, *,
    short: Optional[str] = None,
    long: Optional[List[str]] = None,
    help: Optional[str] = None,
    metavar: Optional[str] = None,
) -> T_Enum:
    ...


@overload
def Arg(
    default: Optional[T] = None,
    /, *,
    short: Optional[str] = None,
    long: Optional[List[str]] = None,
    factory: Optional[Callable[[str], T]] = None,
    help: Optional[str] = None,
    metavar: Optional[str] = None,
) -> T:
    ...


def Arg(default: Any = ..., /, **annotations):
    if not annotations:
        raise TypeError("at least one keyword argument must be provided to Arg()")
    return cast(Any, _AnnotatedValue(default, **annotations))
