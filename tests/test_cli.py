import re


def test_app_help(cli):
    r = cli('-h')
    regex = ('Usage: app \[OPTIONS\] COMMAND \[ARGS\]...'
             '.*Options:'
             '.*Commands:')
    assert re.search(regex, r.output, re.DOTALL) is not None, r.output
    assert r.exit_code == 0
