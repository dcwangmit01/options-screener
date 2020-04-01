from app import datareader

dr = datareader.Datareader()


class TestDatareader():
    def dtest_yahoo_dataframe(self):
        df = dr.yahoo_options_dataframe('AAPL')
        print(df)
