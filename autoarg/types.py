from typing import (
    IO, Any, BinaryIO, Callable, Generic, List, Literal, NewType, Optional,
    TextIO, Tuple, TypeVar, Union
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
]


T = TypeVar('T')


class Arg(Generic[T]):
    """Container for holding argparse metadata alongside a default value

    short:
        * ... -> automatically assign short option if possible
            (based on first letter of name, earlier arguments prioritized)
        * 'a' -> reserves that short opt even if another argument would
            have been automatically assigned that opt otherwise.
        * None -> do not create short option
    long: provide list of long options to use instead of parameter name
    negate_prefix:
        if `long` was not specified and the default value is True, a
        prefix to the name of the long argument
    factory: overrides `type` argument that would have been generated
        from the annotated type
    help: the help string
    metavar: the metavar in the generated help
    """

    def __init__(
        self,
        value: T = ...,
        /, *,
        short: Optional[str] = ...,
        long: Optional[List[str]] = None,
        negate_prefix: str = 'no-',
        factory: Optional[Callable[[str], T]] = None,
        help: Optional[str] = None,
        metavar: Optional[str] = None,
    ):
        self.default = value
        if isinstance(short, str):
            if short[0] == '-':
                short = short[1:]
            if len(short) != 1:
                raise TypeError(f"invalid short option: {short}")
        self.short = short
        self.long = long
        self.negate_prefix = negate_prefix
        self.factory = factory
        self.help = help
        self.metavar = metavar

    def _apply_to(self, kw):
        pass

    def argparse_kwargs(self, is_opt=False):
        ...

    @property
    def is_flag(self):
        return isinstance(self.default, bool)

    @property
    def is_required(self):
        return self.default is ...


# Special annotation-only types


class OneOrMore(Generic[T]):
    pass


class Append(List[T]):
    pass


Count = NewType("Count", int)
Remainder = NewType("Remainder", List[str])
InFile = NewType("InFile", TextIO)
OutFile = NewType("OutFile", TextIO)
InFileBin = NewType("InFileBin", BinaryIO)
OutFileBin = NewType("OutFileBin", BinaryIO)
JSON = NewType("JSON", Any)
