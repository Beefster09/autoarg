from autoarg import generate_argparser


def test_generate_argparser():
    def some_cmd(a, *b, c=False, d=True, e, long, something_with_a_default: int = 3, cat: str = ''):
        pass

    parser = generate_argparser(some_cmd)

    args = parser.parse_args(['abc', 'def', '123', '-c', '-e', 'xyz', '-l', 'abc'])
    assert args.a == 'abc'
    assert args.b == ['def', '123']
    assert args.c
    assert args.e == 'xyz'
    assert args.long == 'abc'
    assert args.something_with_a_default == 3
    assert args.cat == ''
