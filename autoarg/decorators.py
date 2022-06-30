import functools
import sys
from typing import NoReturn, Callable, Tuple, no_type_check_decorator
from inspect import signature, Parameter

from .generate import generate_argparser
from .types import Argument


def command(maybe_fn=None, /, **opts):
    @no_type_check_decorator
    def _decorator(fn):
        parser = generate_argparser(fn)
        _sanitize_defaults(fn)
        return Command(fn, parser)

    if maybe_fn is None:
        return _decorator
    else:
        return _decorator(maybe_fn)


class Command:
    def __init__(self, func: Callable, parser):
        self._func = func
        self.parser = parser
        functools.update_wrapper(self, func)
        self.__annotations__ = {
            name: value
            for name, value in func.__annotations__.items()
            if not (name.startswith('_') and name.endswith('_'))
        }

    def __call__(self, *args, **kwargs):
        return self._func(*args, **kwargs)

    def main(self) -> NoReturn:
        namespace = self.parser.parse_args()
        args, kwargs = self._namespace_to_args(namespace)
        ret = self._func(*args, **kwargs)
        if ret is None:
            sys.exit(0)
        elif isinstance(ret, int):
            sys.exit(ret)
        else:
            sys.exit(int(not ret))  # Truthy -> 0, Falsy -> 1

    def run(self, *str_args: str):
        try:
            namespace = self.parser.parse_args(str_args)
        except SystemExit as err:
            raise TypeError(str(err))
        args, kwargs = self._namespace_to_args(namespace)
        return self._func(*args, **kwargs)

    def _namespace_to_args(self, namespace) -> Tuple[list, dict]:
        args = []
        kwargs = {}
        for name, param in signature(self._func).parameters.items():
            if hasattr(namespace, name):
                value = getattr(namespace, name)
                if param.kind in (Parameter.POSITIONAL_OR_KEYWORD, Parameter.POSITIONAL_ONLY):
                    args.append(value)
                elif param.kind is Parameter.VAR_POSITIONAL:
                    args.extend(value)
                elif param.kind is Parameter.KEYWORD_ONLY:
                    kwargs[name] = value
        return args, kwargs


def _sanitize_defaults(fn):
    """Strips out `Argument`s and headers from the function's defaults
    """
    # TODO: handle ... properly for obvious default values, e.g. Count, bool
    if fn.__defaults__ is not None:
        fn.__defaults__ = tuple(
            value.default if isinstance(value, Argument) else value
            for value in fn.__defaults__
        )
    if fn.__kwdefaults__ is not None:
        fn.__kwdefaults__ = {
            name: value.default if isinstance(value, Argument) else value
            for name, value in fn.__kwdefaults__.items()
        }
