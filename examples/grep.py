from autoarg import *


@command
def grep(
    pattern: str,
    *files: OneOrMore[InFile],
    verbose: Count = Arg(short='v'),
    before: int = Arg(0, short='B'),
    after: int = Arg(0, short='A'),
):
    print("not implemented")


if __name__ == '__main__':
    grep.main()
