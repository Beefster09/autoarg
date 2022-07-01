from autoarg import *


@command
def grep(
    pattern: str,
    *files: File['r'],
    verbose: Count = Arg(short='v', long=[], help="increase output verbosity (can be specified multiple times)"),
    quiet: Count = Arg(short='q', long=[], help="decrease output verbosity (can be specified multiple times)"),

    _Controlling_Output_='The following arguments control the output surrounding a match',
    before: int = Arg(0, short='B', metavar='N', help="show N lines before the match"),
    after: int = Arg(0, short='A', metavar='N', help="show N lines after the match"),
):
    print(verbose - quiet)
    print("not implemented")


if __name__ == '__main__':
    grep.main()
