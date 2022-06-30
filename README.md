# autoarg
Experimental python module for making command line parsers from function argument annotations


## Vision

my idea for this library is to be able to do something like this:

```python
@autoarg.command
def some_command(a, b, c, ...):
    ...

if __name__ == '__main__':
    some_command.main()
    some_command.run('some', 'arguments', '--go', '--here')
    args = some_command.parser.parse_args()
    some_command(1, 2, 3)  # you can still run it as a function
```

As for type annotations -> parser mapping:

```python
def some_command(
    positional: str,
    opt_posarg: Optional[str],                  # nargs='?', positional
    default_posarg: float = 3.1415,             # same as above, but default value is set instead of being None
    *multiarg: int,                             # nargs='*', positional
    *one_or_more: OneOrMore[float],             # nargs='+', positional
    verbose: Count,                             # action=count

    _Group_Title_ = "The group's description",  # create group containing all following arguments
    enum_arg: SomeEnum,                         # choices=list(SomeEnum)
    mutex_arg: Literal['one', 'two', 'three'],  # create mutually exclusive group with store_const action
    list_arg: List[str],                        # nargs='+'
    multiple_arg: Tuple[str, int, str],         # nargs=3 (converting to str, int, str)
    append_arg: Append[int],                    # append (can contain a Literal to get append_const)
    set_arg: Set[int],                          # like append, but result is converted to a set
    in_file: InFile,                            # type=argparse.FileType('r')
    out_file: OutFile,                          # type=argparse.FileType('w')

    _Another_Group_ = None,                     # Create group with no description
    enable_flag = False,                        # action=store_true
    disable_flag = True,                        # action=store_false, name prefixed with 'no-'
    inferred_string = 'abc',                    # type is inferred from default
    inferred_int = 123,
    remainder: Remainder                        # nargs=argparse.REMAINDER
):
    """description of what the command does

    help for each argument can be parsed from the docstring somehow
    """
```

less important edge cases:
* `nargs='?'` on options
