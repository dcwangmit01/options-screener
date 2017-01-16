import mock

from app import utils
from app import schwab_datareader as schwab


class TestSchwabDatareader():
    def dtest_schwab_options_dict_to_dataframe():
        datasource = schwab.SchwabDatareader()
        s = utils.FileUtils.read_string_from_file(
            'tests/fixtures/schwab_options_goog.json')

        df = datasource.schwab_options_dict_to_dataframe(s)

    def dtest_schwab_stock_info():
        datasource = schwab.SchwabDatareader()
        s = utils.FileUtils.read_string_from_file(
            'tests/fixtures/schwab_summary_goog.json')
        datasource.schwab_stock_info(s)

    def dtest_yahoo_dataframe():
        ds = schwab.SchwabDatareader()
        df = ds.yahoo_dataframe('AAPL')

    @mock.patch(
        'app.schwab_datareader.SchwabBrowser.page_source',
        return_value=utils.FileUtils.read_string_from_file(
            'tests/fixtures/schwab_options_aapl.json'))
    @mock.patch('app.schwab_datareader.SchwabBrowser.get')
    @mock.patch('app.schwab_datareader.SchwabBrowser.login')
    @mock.patch('app.schwab_datareader.SchwabBrowser.start')
    def test_schwab_dataframe(self, mocked_start, mocked_login, mocked_get,
                              mocked_page_source):
        ds = schwab.SchwabDatareader()
        df = ds.schwab_dataframe('AAPL')
