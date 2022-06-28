import argparse
from enum import Enum
from inspect import signature, Parameter
from typing import Any, Callable, Dict, List, Literal, Optional, Text, Tuple, Type, Union, MutableSet, get_origin

from .types import Argument


def generate_argparser(
    func: Callable,
    *,
    add_help=True,
    **parser_kw
):
    arg_groups, short_opts = _inspect_fn(func, add_help=add_help)

    parser = argparse.ArgumentParser(func.__name__, add_help=add_help, **parser_kw)
    group_parser = parser
    postprocessors: Dict[str, Callable[[Any], Any]] = {}

    for group, args in arg_groups:
        if group is not None:
            group_parser = group.create_group(parser)
        for arg in args:
            if hasattr(arg, 'auto_assign_short_opts'):
                arg.auto_assign_short_opts(short_opts)
            arg.add_to_parser(group_parser)
            pf = arg.postprocessor
            if pf is not None:
                postprocessors[arg.dest] = pf

    return ArgumentParserWrapper(parser, postprocessors)


def _inspect_fn(func: Callable, /, *, add_help=True):
    groups = []
    group = None
    args = []
    short_opts = {'h'} if add_help else set()

    sig = signature(func)
    for name, param in sig.parameters.items():
        if name.startswith('_') and name.endswith('_'):
            groups.append((group, args))
            group = ArgGroup(name, param.default)
            args = []
        elif param.kind == Parameter.POSITIONAL_OR_KEYWORD:
            args.append(Positional(param))
        elif param.kind == Parameter.VAR_POSITIONAL:
            args.append(VarPositional(param))
        elif param.kind == Parameter.KEYWORD_ONLY:
            opt = _inspect_opt(param)
            opt.reserve_short_opts(short_opts)
            args.append(opt)
        else:
            raise TypeError(f"Unsupported parameter: {name}")

    groups.append((group, args))

    return groups, short_opts


class CommandArg:
    def __init__(self, param: Parameter):
        self.fn_param = param

        if isinstance(param.default, Argument):
            self.arg = param.default
        elif param.default is Parameter.empty:
            self.arg = Argument()
        else:
            self.arg = Argument(param.default)

        if param.annotation is not Parameter.empty:
            self.type = param.annotation
        elif self.arg.default is not ...:
            self.type = type(self.arg.default)
        else:
            self.type = ...

        if issubclass(type(self.arg.default), Enum):
            self.default = self.arg.default._value_
        else:
            self.default = self.arg.default

        self.factory = self._infer_factory()
        self.postprocessor = self._infer_postprocessor()

    @property
    def dest(self):
        return self.fn_param.name

    def _infer_factory(self) -> Optional[Callable[[Text], Any]]:
        if self.arg.factory:
            return self.arg.factory

        if self.type is ... or self.type is str:
            return None
        elif isinstance(self.type, type) and issubclass(self.type, Enum):
            first_base = self.type.__mro__[1]
            if not issubclass(first_base, (str, Enum)):
                return first_base
            else:
                return None
        elif get_origin(self.type) is tuple:
            # TODO
            raise NotImplementedError()
        elif callable(self.type):
            # probably should also check that it can be called with a single string argument
            return self.type

        raise TypeError(self.type)

    def _infer_postprocessor(self) -> Optional[Callable[[Any], Any]]:
        if self.arg.factory:
            return None

        if isinstance(self.type, type) and issubclass(self.type, Enum):
            return self.type
        else:
            return None

    @property
    def choices(self) -> Optional[List[str]]:
        annotation = self.fn_param.annotation
        if isinstance(self.type, type) and issubclass(annotation, Enum):
            return [str(choice._value_) for choice in annotation]


class Positional(CommandArg):
    def add_to_parser(self, parser: argparse.ArgumentParser):
        kw = {
            'choices': self.choices,
            'type': self.factory,
            'metavar': self.arg.metavar,
            'help': self.arg.help,
        }
        if self.default is not ...:
            kw['default'] = self.default
        parser.add_argument(self.dest, **kw)


class VarPositional(Positional):
    def add_to_parser(self, parser: argparse.ArgumentParser):
        kw = {
            'nargs': '*',
            'choices': self.choices,
            'type': self.factory,
            'metavar': self.arg.metavar,
            'help': self.arg.help,
        }
        if self.default is not ...:
            kw['default'] = self.default
        parser.add_argument(self.dest, **kw)


class Option(CommandArg):
    def __init__(self, param: Parameter):
        super().__init__(param)
        self.short_opt = None

    @property
    def long_names(self):
        if self.arg.long is not None:
            return self.arg.long
        return ['--' + self.dest.replace('_', '-')]

    @property
    def all_names(self):
        if self.short_opt:
            return [self.short_opt, *self.long_names]
        else:
            return self.long_names

    def add_to_parser(self, parser: argparse.ArgumentParser):
        kw = {
            'choices': self.choices,
            'type': self.factory,
            'metavar': self.arg.metavar,
            'help': self.arg.help,
            'dest': self.dest,
        }
        if self.default is ...:
            kw['required'] = True
        else:
            kw['default'] = self.default
        parser.add_argument(*self.all_names, **kw)

    def reserve_short_opts(self, reservations: MutableSet[str]):
        # reserve explicitly defined short options
        if isinstance(self.arg.short, str):
            if self.arg.short in reservations:
                raise TypeError(f"Cannot reserve -{self.arg.short}")
            reservations.add(self.arg.short)
            self.short_opt = '-' + self.arg.short

    def auto_assign_short_opts(self, reservations: MutableSet[str]):
        if self.short_opt is not None:
            return
        proposed = self.proposed_short_opt()
        if proposed not in reservations:
            reservations.add(proposed)
            self.short_opt = '-' + proposed

    def proposed_short_opt(self):
        return self.dest[0]


class Flag(Option):
    def __init__(self, param: Parameter):
        super().__init__(param)
        if self.arg.default is ... or self.arg.default is None:
            self.default = False
        elif not isinstance(self.default, bool):
            raise TypeError(self.default)

    def add_to_parser(self, parser: argparse.ArgumentParser):
        kw = {
            'action': f'store_{not self.default}'.lower(),
            'help': self.arg.help,
            'dest': self.dest,
        }
        parser.add_argument(*self.all_names, **kw)

    @property
    def long_names(self):
        if self.arg.long is not None:
            return self.arg.long

        if self.default:
            return ['--' + self.arg.negate_prefix + self.dest.replace('_', '-')]
        else:
            return ['--' + self.dest.replace('_', '-')]

    def proposed_short_opt(self):
        proposed = self.dest[0]
        if self.default:
            proposed = proposed.upper()
        return proposed


class FlagGroup(CommandArg):
    def __init__(self, param: Parameter):
        ...

    def reserve_short_opts(self, reservations: MutableSet[str]):
        ...

    def auto_assign_short_opts(self, reservations: MutableSet[str]):
        ...


def _inspect_opt(param: Parameter):
    if get_origin(param.annotation) is Literal:
        return FlagGroup(param)
    # TODO: Append/Set[Literal[...]]
    elif param.annotation is bool or isinstance(param.default, bool):
        return Flag(param)
    else:
        return Option(param)


class ArgGroup:
    def __init__(self, arg_name: str, arg_default):
        self.title = arg_name.strip('_').replace('_', ' ')
        if arg_default is Parameter.empty or arg_default is None:
            self.description = None
        elif isinstance(arg_default, str):
            self.description = arg_default
        else:
            raise TypeError(f"invalid argument group description: {arg_default}")

    def create_group(self, parser: argparse.ArgumentParser):
        return parser.add_argument_group(self.title, self.description)


class ArgumentParserWrapper:
    def __init__(self, parser, postprocessors: Dict[str, Callable[[Any], Any]]):
        self._parser = parser
        self._postprocessors = postprocessors

    def _postprocess(self, namespace):
        try:
            for attr, post in self._postprocessors.items():
                setattr(namespace, attr, post(getattr(namespace, attr)))
        except ValueError as err:
            self._parser.error(str(err))

    def parse_args(self, args=None, namespace=None):
        ns = self._parser.parse_args(args, namespace)
        self._postprocess(ns)
        return ns

    def parse_known_args(self, args=None, namespace=None):
        ns, unknown = self._parser.parse_known_args(args, namespace)
        self._postprocess(ns)
        return ns, unknown

    def parse_intermixed_args(self, args=None, namespace=None):
        ns = self._parser.parse_intermixed_args(args, namespace)
        self._postprocess(ns)
        return ns

    def parse_known_intermixed_args(self, args=None, namespace=None):
        ns, unknown = self._parser.parse_known_intermixed_args(args, namespace)
        self._postprocess(ns)
        return ns, unknown

    # proxy remaining methods to _parser, unmodified
    def __getattr__(self, attr):
        return getattr(self._parser, attr)
