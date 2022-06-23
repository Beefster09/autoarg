import argparse
from enum import Enum
from inspect import signature, Parameter
from typing import Any, Callable, Dict, List, Literal, Optional, Text, Tuple, Union, MutableSet, get_origin

from .types import Arg


def generate_argparser(
    func: Callable,
    parser_kw: dict = {},
    *,
    add_help=True,
) -> argparse.ArgumentParser:
    arg_groups, short_opts = _inspect_fn(func, add_help=add_help)

    parser = argparse.ArgumentParser(**parser_kw)
    group_parser = parser

    for group, args in arg_groups:
        if group is not None:
            group_parser = group.create_group(parser)
        for arg in args:
            if hasattr(arg, 'auto_assign_short_opts'):
                arg.auto_assign_short_opts(short_opts)
            arg.add_to_parser(group_parser)

    return parser


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
        if isinstance(param.default, Arg):
            self.arg = param.default
        elif param.default is Parameter.empty:
            self.arg = Arg()
        else:
            self.arg = Arg(param.default)

    @property
    def dest(self):
        return self.fn_param.name

    @property
    def factory(self) -> Optional[Callable[[Text], Any]]:
        if self.arg.factory:
            return self.arg.factory
        annotation = self.fn_param.annotation
        if annotation is Parameter.empty or annotation is str:
            return None
        elif callable(annotation):
            # probably should also check that it can be called with a single string argument
            return annotation
        elif get_origin(annotation) is Tuple:
            # TODO
            raise NotImplementedError()
        else:
            raise TypeError(annotation)

    @property
    def choices(self) -> Optional[List[str]]:
        annotation = self.fn_param.annotation
        if issubclass(annotation, Enum):
            return [str(choice) for choice in annotation]


class Positional(CommandArg):
    def add_to_parser(self, parser: argparse.ArgumentParser):
        kw = {
            'choices': self.choices,
            'type': self.factory,
            'metavar': self.arg.metavar,
            'help': self.arg.help,
        }
        if self.arg.default is not ...:
            kw['default'] = self.arg.default
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
        if self.arg.default is not ...:
            kw['default'] = self.arg.default
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
        if self.arg.default is not ...:
            kw['default'] = self.arg.default
        parser.add_argument(*self.all_names, **kw)

    def reserve_short_opts(self, reservations: MutableSet[str]):
        # reserve explicitly defined short options
        if isinstance(self.arg.short, str):
            if self.arg.short in reservations:
                raise TypeError(f"Cannot reserve -{self.arg.short}")
            reservations.add(self.arg.short)
            self.short_opt = '-' + self.arg.short

    def auto_assign_short_opts(self, reservations: MutableSet[str]):
        proposed = self.dest[0]
        if proposed not in reservations:
            reservations.add(proposed)
            self.short_opt = '-' + proposed


class Flag(Option):
    def __init__(self, param: Parameter):
        super().__init__(param)
        if self.arg.default is ... or self.arg.default is None:
            self.arg.default = False
        elif not isinstance(self.arg.default, bool):
            raise TypeError(self.arg.default)

    def add_to_parser(self, parser: argparse.ArgumentParser):
        kw = {
            'action': f'store_{not self.arg.default}'.lower(),
            'help': self.arg.help,
            'dest': self.dest,
        }
        parser.add_argument(*self.all_names, **kw)

    @property
    def long_names(self):
        if self.arg.long is not None:
            return self.arg.long

        if self.arg.default:
            return ['--' + self.dest.replace('_', '-')]
        else:
            return ['--' + self.arg.negate_prefix + self.dest.replace('_', '-')]

    def auto_assign_short_opts(self, reservations: MutableSet[str]):
        proposed = self.dest[0]
        if self.arg.default:
            proposed = proposed.upper()
        if proposed not in reservations:
            reservations.add(proposed)
            self.short_opt = '-' + proposed


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

