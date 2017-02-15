import mock

from app import utils
from app import datareader

dr = datareader.Datareader()


class TestDatareader():
    def dtest_yahoo_dataframe(self):
        df = dr.yahoo_options_dataframe('AAPL')

    @mock.patch(
        'app.datareader.SchwabBrowser.page_source',
        return_value=utils.FileUtils.read_string_from_file(
            'tests/fixtures/schwab_options_aapl.json'))
    @mock.patch('app.datareader.SchwabBrowser.get')
    @mock.patch('app.datareader.SchwabBrowser.login')
    @mock.patch('app.datareader.SchwabBrowser.start')
    def dtest_schwab_dataframe(self, mocked_start, mocked_login, mocked_get,
                               mocked_page_source):
        df = dr.schwab_options_dataframe('AAPL')

    def dtest_google_stock_info(self):
        d = dr.google_stock_info('AAPL')
        print(d)
        import pytest
        pytest.set_trace()

    def test_yahoo_stock_info(self):
        d = dr.yahoo_stock_info('AAPL')
        print(d)
        import pytest
        pytest.set_trace()
