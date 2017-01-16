from __future__ import absolute_import, division, print_function

from click import testing
import pytest
import six
import sys

from app.cli import app as app_cli


class Result(testing.Result):
    def __init__(self, *args, **kw):
        self.__allow_exceptions = kw.pop('allow_exception_access', False)
        self.__exception = None
        self.__exc_info = None
        super(Result, self).__init__(*args, **kw)

    @property
    def exception(self):
        assert self.__allow_exceptions, \
            ('In order to access exception information,'
             ' you must explicitly set catch_exceptions when calling the cli')
        return self.__exception

    @exception.setter
    def exception(self, value):
        self.__exception = value

    @property
    def exc_info(self):
        assert self.__allow_exceptions, \
            ('In order to access exception information,'
             ' you must explicitly set catch_exceptions when calling the cli')
        return self.__exc_info

    @exc_info.setter
    def exc_info(self, value):
        self.__exc_info = value

    def __repr__(self):
        return '<Result %s>' % (self.__exception and repr(self.__exception) or
                                'okay', )

    @classmethod
    def from_upstream(cls, r, allow_exception_access):
        d = r.__dict__.copy()
        d['allow_exception_access'] = allow_exception_access
        return Result(**d)


@pytest.fixture
def cli(request):
    def invoke(*args, **kw):
        __tracebackhide__ = True

        runner = testing.CliRunner()

        exit_code = kw.pop('exit_code', 0)
        try:
            catch_exceptions = kw.pop('catch_exceptions')
            explicit = True
        except KeyError:
            catch_exceptions = (request.config.getvalue('verbose') <= 0)
            explicit = False

        assert not kw, 'unhandled kw args: %s' % (kw, )

        args = ('--home', './tests/fixtures') + args
        r = runner.invoke(app_cli, args, catch_exceptions=catch_exceptions)

        if isinstance(exit_code, six.string_types) and (
                exit_code.lower() == 'ignore'):
            pass
        else:
            if not r.exit_code == exit_code:
                print('%r\nOutput was:' % r, file=sys.stderr)
                sys.stderr.write(r.output)
                raise AssertionError(
                    'Wanted exit code %s but got %s (see stderr for more)' %
                    (exit_code, r.exit_code))

        return Result.from_upstream(r, allow_exception_access=explicit)

    return invoke
