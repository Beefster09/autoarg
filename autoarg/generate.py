import argparse
import json
from enum import Enum
from inspect import Parameter, signature
from typing import Any, Callable, Dict, List, MutableSet, Optional, Tuple, Union, IO

from typing_extensions import Annotated, Literal, Text, Type, TypeGuard, get_args, get_origin

from .types import _AnnotatedValue, Count, Level, Remainder


def generate_argparser(
    func: Callable,
    *,
    add_help=True,
    **parser_kw
):
    arg_groups, short_opts = _inspect_fn(func, add_help=add_help)

    parser = argparse.ArgumentParser(func.__name__, add_help=add_help, **parser_kw)
    group_parser = parser
    postprocessors: List[Callable[[argparse.Namespace], None]] = []

    for group, args in arg_groups:
        if group is not None:
            group_parser = group.create_group(parser)
        for arg in args:
            if hasattr(arg, 'auto_assign_short_opts'):
                arg.auto_assign_short_opts(short_opts)
            arg.add_to_parser(group_parser)
            if arg.has_postprocessing:
                postprocessors.append(arg.postprocess_namespace)

    return _ArgumentParserWrapper(parser, postprocessors)


def _inspect_fn(func: Callable, /, *, add_help=True):
    groups = []
    group: Optional[_ArgGroup] = None
    args: List[_CommandArg] = []
    short_opts = {'h'} if add_help else set()

    sig = signature(func)
    for name, param in sig.parameters.items():
        if name.startswith('_') and name.endswith('_'):
            groups.append((group, args))
            group = _ArgGroup(name, param.default)
            args = []
        elif param.kind == Parameter.POSITIONAL_OR_KEYWORD:
            args.append(_Positional(param))
        elif param.kind == Parameter.VAR_POSITIONAL:
            args.append(_VarPositional(param))
        elif param.kind == Parameter.KEYWORD_ONLY:
            opt = _inspect_opt(param)
            opt.reserve_short_opts(short_opts)
            args.append(opt)
        else:
            raise TypeError(f"Unsupported parameter: {name}")

    groups.append((group, args))

    return groups, short_opts


class _CommandArg:
    def __init__(self, param: Parameter, **kwargs):
        self.fn_param = param

        if isinstance(param.default, _AnnotatedValue):
            self.arg = param.default
        elif param.default is Parameter.empty:
            self.arg = _AnnotatedValue()
        else:
            self.arg = _AnnotatedValue(param.default)

        if 'type' in kwargs:
            self.type = kwargs['type']
        elif param.annotation is not Parameter.empty:
            self.type = param.annotation
        elif self.arg.value is not ...:
            self.type = type(self.arg.value)
        else:
            self.type = str

        if issubclass(type(self.arg.value), Enum):
            self.default = self.arg.value._value_
        else:
            self.default = self.arg.value

        if 'help' in self.arg:
            self.help = self.arg['help']
        # TODO: get help from parsed docstring
        else:
            self.help = None

        self.nargs = None

        if 'factory' in kwargs:
            self.factory = kwargs['factory']
        else:
            self.factory = self._infer_factory()

        if 'postprocessor' in kwargs:
            self.postprocessor = kwargs['postprocessor']
        else:
            self.postprocessor = self._infer_postprocessor()

    @property
    def dest(self):
        return self.fn_param.name

    def _infer_factory(self) -> Optional[Callable[[Text], Any]]:
        if 'factory' in self.arg:
            return self.arg['factory']

        if self.type in [str, Remainder]:
            return None

        if get_origin(self.type) is Annotated:
            T, *annotations = get_args(self.type)
            if T is IO:
                return argparse.FileType(*annotations)
            if T is Any and 'json' in annotations:
                return json.loads
            if is_simple_factory(T):
                if 'level' in annotations or 'count' in annotations:
                    return None
                return T

        if is_enum_class(self.type):
            first_base = self.type.__mro__[1]
            if not issubclass(first_base, (str, Enum)):
                return first_base
            else:
                return None

        if get_origin(self.type) is tuple:
            targs = get_args(self.type)
            for T in targs:
                if not is_simple_factory(T):
                    raise TypeError(
                        f"parameter {self.dest}: Tuple type {T} (in {self.type})"
                        + " is not a valid factory"
                    )
            self.nargs = len(targs)
            return None  # should be parsed by postprocessor

        if is_simple_factory(self.type):
            return self.type

        raise TypeError(
            f"parameter {self.dest}: could not determine suitable factory for {self.type}"
        )

    def _infer_postprocessor(self) -> Optional[Callable[[Any], Any]]:
        if 'factory' in self.arg:
            return None

        if is_enum_class(self.type):
            return self.type

        if get_origin(self.type) is tuple:
            return lambda values, types=get_args(self.type): tuple(
                T(x) for x, T in zip(values, types)
            )

        return None

    @property
    def choices(self) -> Optional[List[str]]:
        if is_enum_class(self.type):
            return [str(choice._value_) for choice in self.type]
        return None

    def postprocess_namespace(self, namespace):
        assert self.postprocessor
        setattr(namespace, self.dest, self.postprocessor(getattr(namespace, self.dest)))

    @property
    def has_postprocessing(self) -> bool:
        return self.postprocessor is not None


class _Positional(_CommandArg):
    def add_to_parser(self, parser: argparse.ArgumentParser):
        kw = {
            'choices': self.choices,
            'type': self.factory,
            'metavar': self.arg.get('metavar'),
            'help': self.help,
        }

        if self.default is not ...:
            kw['default'] = self.default

        if self.nargs is not None:
            kw['nargs'] = self.nargs

        parser.add_argument(self.dest, **kw)


class _VarPositional(_Positional):
    def add_to_parser(self, parser: argparse.ArgumentParser):
        kw = {
            'nargs': '*',
            'choices': self.choices,
            'type': self.factory,
            'metavar': self.arg.get('metavar'),
            'help': self.help,
        }

        if self.default is not ...:
            kw['default'] = self.default

        parser.add_argument(self.dest, **kw)


class _Option(_CommandArg):
    def __init__(self, param: Parameter, **kwargs):
        super().__init__(param, **kwargs)
        self.short_opt = None

    @property
    def long_names(self):
        if 'long' in self.arg:
            return self.arg['long']
        return ['--' + self.dest.replace('_', '-')]

    @property
    def all_names(self):
        if self.short_opt:
            return [self.short_opt, *self.long_names]
        else:
            return self.long_names

    def add_to_parser(self, parser: argparse.ArgumentParser):
        kw = {
            'dest': self.dest,
            'choices': self.choices,
            'type': self.factory,
            'metavar': self.arg.get('metavar'),
            'help': self.help,
        }

        if self.default is ...:
            kw['required'] = True
        else:
            kw['default'] = self.default

        if self.nargs is not None:
            kw['nargs'] = self.nargs

        parser.add_argument(*self.all_names, **kw)

    def reserve_short_opts(self, reservations: MutableSet[str]):
        # reserve explicitly defined short options
        if short := self.arg.get('short'):
            short = normalize_shortopt(short)
            if short in reservations:
                raise TypeError(f"Cannot reserve -{short}")
            reservations.add(short)
            self.short_opt = '-' + short

    def auto_assign_short_opts(self, reservations: MutableSet[str]):
        if self.short_opt is not None:
            return
        proposed = self.proposed_short_opt()
        if proposed not in reservations:
            reservations.add(proposed)
            self.short_opt = '-' + proposed

    def proposed_short_opt(self):
        return self.dest[0]


class _AppendOption(_Option):
    def add_to_parser(self, parser: argparse.ArgumentParser):
        kw = {
            'dest': self.dest,
            'action': 'append',
            'choices': self.choices,
            'type': self.factory,
            'metavar': self.arg.get('metavar'),
            'help': self.help,
        }

        if self.default is not ...:
            kw['default'] = self.default

        parser.add_argument(*self.all_names, **kw)


class _Flag(_Option):
    def __init__(self, param: Parameter):
        super().__init__(param, type=bool, factory=None, postprocessor=None)
        if self.default is ... or self.default is None:
            self.default = False
        elif not isinstance(self.default, bool):
            raise TypeError(self.default)

    def add_to_parser(self, parser: argparse.ArgumentParser):
        kw = {
            'dest': self.dest,
            'action': f'store_{not self.default}'.lower(),
            'help': self.help,
        }
        parser.add_argument(*self.all_names, **kw)

    @property
    def long_names(self):
        if 'long' in self.arg:
            return self.arg['long']

        if self.default:
            return [f"--{self.arg.get('negate_prefix', 'no-')}{self.dest.replace('_', '-')}"]
        else:
            return ['--' + self.dest.replace('_', '-')]

    def proposed_short_opt(self):
        proposed = self.dest[0]
        if self.default:
            proposed = proposed.upper()
        return proposed


class _CountFlag(_Option):
    def add_to_parser(self, parser: argparse.ArgumentParser):
        kw = {
            'dest': self.dest,
            'action': 'count',
            'help': self.help,
        }
        parser.add_argument(*self.all_names, **kw)


class _LevelFlag(_CommandArg):
    def __init__(self, param: Parameter, *, is_verbosity: bool):
        super().__init__(param, type=int, factory=None, postprocessor=None)
        self.dest_up = f"_{self.dest}__up_"
        self.dest_down = f"_{self.dest}__down_"

    def add_to_parser(self, parser: argparse.ArgumentParser):
        ...

    def reserve_short_opts(self, reservations: MutableSet[str]):
        ...

    def auto_assign_short_opts(self, reservations: MutableSet[str]):
        ...

    def postprocess_namespace(self, namespace):
        up = getattr(namespace, self.dest_up)
        down = getattr(namespace, self.dest_down)
        setattr(namespace, self.dest, self.default + up - down)
        delattr(namespace, self.dest_up)
        delattr(namespace, self.dest_down)

    @property
    def has_postprocessing(self) -> bool:
        return True


class _FlagGroup(_CommandArg):
    _ACTION = 'store_const'

    def __init__(self, param: Parameter, flag_values: Tuple[str]):
        for val in flag_values:
            if not isinstance(val, str):
                raise TypeError(f"Literal flag values must be strings, got {val}")
        super().__init__(param, type=str)
        self.flag_values = flag_values
        self.short_opts = self.arg['shorts'] if 'shorts' in self.arg else {}
        self.long_opts = self.arg['longs'] if 'longs' in self.arg else {}

    def add_to_parser(self, parser: argparse.ArgumentParser):
        mutex_group = parser.add_mutually_exclusive_group(
            required=self._ACTION == 'store_const' and self.default is ...
        )
        for flag in self.flag_values:
            kw = {
                'dest': self.dest,
                'action': self._ACTION,
                'const': flag,
                'help': self.help,
            }
            if flag in self.long_opts:
                flags = self.long_opts[flag]
            else:
                flags = [f"--{flag.replace('_', '-')}"]
            if short := self.short_opts.get(flag):
                flags.insert(0, '-' + short)
            mutex_group.add_argument(*flags, **kw)

        if self.default is not ...:
            parser.set_defaults(**{self.dest: self.default})

    def reserve_short_opts(self, reservations: MutableSet[str]):
        for flag in self.flag_values:
            if not self.short_opts.get(flag):
                continue  # short opt is either:
                # unset: will be auto-assigned later
                # None or '': is explicitly unreserved
            short = self.short_opts[flag] = normalize_shortopt(self.short_opts[flag])
            if short in reservations:
                raise TypeError(f"Cannot reserve -{short}")
            reservations.add(short)

    def auto_assign_short_opts(self, reservations: MutableSet[str]):
        for flag in self.flag_values:
            if flag in self.short_opts:
                continue  # was explicitly set or unreserved
            proposed = flag[0]
            if proposed not in reservations:
                reservations.add(proposed)
                self.short_opts[flag] = proposed


class _AppendFlagGroup(_FlagGroup):
    _ACTION = 'append_const'


def _inspect_opt(param: Parameter):
    if get_origin(param.annotation) is Annotated:
        T, *annotations = get_args(param.annotation)
        if 'count' in annotations:
            return _CountFlag(param)
        if 'level' in annotations:
            return _LevelFlag(param, is_verbosity='verbosity' in annotations)
        if 'append' in annotations:
            return _AppendOption(param)

    if get_origin(param.annotation) is Literal:
        return _FlagGroup(param, get_args(param.annotation))

    if param.annotation is bool or isinstance(param.default, bool):
        return _Flag(param)

    return _Option(param)


class _ArgGroup:
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


class _ArgumentParserWrapper:
    def __init__(self, parser, postprocessors: List[Callable[[argparse.Namespace], None]]):
        self._parser = parser
        self._postprocessors = postprocessors

    def _postprocess(self, namespace):
        try:
            for post in self._postprocessors:
                post(namespace)
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


def is_enum_class(val) -> TypeGuard[Type[Enum]]:
    return isinstance(val, type) and issubclass(val, Enum)


def is_simple_factory(val) -> TypeGuard[Callable[[str], Any]]:
    return callable(val) and isinstance(val, type)
    # this logic is flawed, but it *does* correctly reject generic annotations
    # TODO: check the signature of the type


def normalize_shortopt(short: str) -> str:
    if short[0] == '-':
        short = short[1:]
    if len(short) > 1:
        raise TypeError(f"invalid short option: {short}")
    return short
