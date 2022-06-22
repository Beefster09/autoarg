import argparse
from inspect import signature, Parameter
from typing import Optional


__all__ = ['generate_argparser']


class Arg:
    def apply_to(self, kw):
        pass


def generate_argparser(
    func: callable,
    arg_kws: dict = {},
    parser_kw: dict = {},
) -> argparse.ArgumentParser:
    sig = signature(func)

    parser = argparse.ArgumentParser(**parser_kw)
    short_opts = {}

    for name, param in sig.parameters.items():
        if param.kind == Parameter.POSITIONAL_OR_KEYWORD:
            _add_posarg(parser, param, arg_kws.get(name))
        elif param.kind == Parameter.VAR_POSITIONAL:
            _add_vararg(parser, param, arg_kws.get(name))
        elif param.kind == Parameter.KEYWORD_ONLY:
            _add_option(parser, short_opts, param, arg_kws.get(name))
        else:
            raise TypeError(f"Unsupported parameter: {name}")

    return parser


def _add_posarg(
    parser: argparse.ArgumentParser,
    param: Parameter,
    arg_kw: Optional[dict],
):
    kw = {}

    if param.annotation is not Parameter.empty:
        _interpret_annotation(kw, param)

    if isinstance(param.default, Arg):
        if arg_kw:
            raise TypeError(f"argument configuration for {param.name} is overspecified")
        kw['nargs'] = argparse.OPTIONAL
        param.default.apply_to(kw)
    elif param.default is not Parameter.empty:
        kw['nargs'] = argparse.OPTIONAL
        kw['default'] = param.default

    if arg_kw:
        kw.update(arg_kw)
    parser.add_argument(param.name, **kw)


def _add_vararg(
    parser: argparse.ArgumentParser,
    param: Parameter,
    arg_kw: Optional[dict],
):
    kw = {}
    if param.annotation is not Parameter.empty:
        _interpret_annotation(kw, param)

    if isinstance(param.default, Arg):
        if arg_kw:
            raise TypeError(f"argument configuration for {param.name} is overspecified")
        if param.default.value is not ...:
            raise TypeError(f"vararg {param.name} was given a default value")
        param.default.apply_to(kw)
    elif param.default is not Parameter.empty:
        raise TypeError(f"vararg {param.name} was given a default value")

    if arg_kw:
        kw.update(arg_kw)
    parser.add_argument(param.name, nargs=argparse.ZERO_OR_MORE, **kw)


def _add_option(
    parser: argparse.ArgumentParser,
    short_opts: dict,
    param: Parameter,
    arg_kw: Optional[dict],
):
    kw = {}
    is_flag = False
    default = ...
    if param.annotation is bool:
        is_flag = True
        default = False
    elif param.annotation is not Parameter.empty:
        _interpret_annotation(kw, param)

    if isinstance(param.default, Arg):
        if arg_kw:
            raise TypeError(f"argument configuration for {param.name} is overspecified")
        if param.default.value is not ...:
            raise TypeError(f"vararg {param.name} was given a default value")
        if isinstance(param.default.value, bool):
            is_flag = True
            default = param.default.value
        param.default.apply_to(kw)
    elif isinstance(param.default, bool):
        is_flag = True
        default = param.default
    elif param.default is not Parameter.empty:
        default = param.default

    if arg_kw:
        kw.update(arg_kw)

    if is_flag:
        if default:
            kw['action'] = 'store_false'
            kw['dest'] = param.name
            kw.pop('default', None)
            opt_name = '--no-' + param.name.replace('_', '-')
            short_letter = param.name[0].upper()
        else:
            kw['action'] = 'store_true'
            kw['dest'] = param.name
            kw.pop('default', None)
            opt_name = '--' + param.name.replace('_', '-')
            short_letter = param.name[0]
    else:
        if default is not ...:
            kw['default'] = default
        opt_name = '--' + param.name.replace('_', '-')
        short_letter = param.name[0]

    names = [opt_name]
    if short_letter not in short_opts:
        names.insert(0, '-' + short_letter)

    parser.add_argument(*names, **kw)


def _interpret_annotation(kw: dict, param: Parameter):
    if callable(param.annotation):
        kw['type'] = param.annotation


def test(a, *b, c=False, d=True, e, long, something_with_a_default: int = 3):
    pass


if __name__ == '__main__':
    parser = generate_argparser(test)

    args = parser.parse_args()
    print(vars(args))
