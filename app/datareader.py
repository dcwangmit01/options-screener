import os
import time
import sys
import re
import json
import pandas as pd

from selenium import webdriver
import selenium.webdriver.chrome.service as service
from selenium.webdriver.support.ui import Select

from pandas_datareader.data import Options
import requests_cache

#####################################################################
# Settings

# cache settings
seconds_to_cache = 180  # seconds

seconds_to_pause = 3  # seconds

yahoo_columns = [
    'Strike', 'Expiry', 'Type', 'Symbol', 'Last', 'Bid', 'Ask', 'Chg', 'PctChg', 'Vol', 'Open_Int', 'IV', 'Root',
    'IsNonstandard', 'Underlying', 'Underlying_Price', 'Quote_Time', 'Last_Trade_Date', 'JSON'
]

common_columns = [
    'strike', 'expiry', 'type', 'symbol', 'lst', 'bid', 'ask', 'chg', 'vol', 'oi', 'root', 'nonstandard', 'underlying',
    'underlyingprice', 'quotetime'
]


class Datareader(object):
    """ This class is unused """
    def __init__(self):
        # Create the requests cache
        self.session = requests_cache.CachedSession(cache_name='cache', backend='sqlite', expire_after=seconds_to_cache)

    def yahoo_options_dataframe(self, ticker):

        # fetch all data
        option = Options(ticker, 'yahoo', session=self.session)
        df = option.get_all_data()

        # reset_index()
        #   copies multi-index values into columns
        #   sets index to single ordinal integer
        df.reset_index(inplace=True)

        # rename a bunch of the columns
        df.rename(index=str,
                  inplace=True,
                  columns={
                      'Strike': 'strike',
                      'Expiry': 'expiry',
                      'Type': 'type',
                      'Symbol': 'symbol',
                      'Last': 'lst',
                      'Bid': 'bid',
                      'Ask': 'ask',
                      'Chg': 'chg',
                      'Vol': 'vol',
                      'Open_Int': 'oi',
                      'Root': 'root',
                      'IsNonstandard': 'nonstandard',
                      'Underlying': 'underlying',
                      'Underlying_Price': 'underlyingprice',
                      'Quote_Time': 'quotetime'
                  })

        # delete unnecessary columns
        df.drop('PctChg', axis=1, inplace=True)
        df.drop('IV', axis=1, inplace=True)
        df.drop('Last_Trade_Date', axis=1, inplace=True)
        df.drop('JSON', axis=1, inplace=True)

        # normalize values for type column
        df['type'] = df.apply(lambda row: 'call' if row['type'] == 'calls' else 'put', axis=1)

        return df

    def schwab_options_dataframe(self, ticker):
        schwab = SchwabBrowser.Singleton()
        schwab.start()
        schwab.login()
        url = ('https://client.schwab.com/trade/options/optionChainsJson.ashx' '?autopage=true&symbol=' + ticker)
        schwab.get(url)

        options_dict = json.loads(self.striphtml(schwab.page_source()))

        df = pd.DataFrame(columns=common_columns)

        i = 0
        for root in options_dict['Roots']:
            _underlying = options_dict['UnderLying']
            _underlying_price = 0  # TODO
            _quotetime = pd.to_datetime(options_dict['TimeStamp'])
            _adjusted = True if root['IsAdjusted'] == 'Y' else False
            _root = root['Root']
            for expiration in root['Expirations']:
                _expiry = pd.to_datetime(expiration['Date'])
                for strike in expiration['Strikes']:
                    _strike = strike['Price']
                    for option in ['Call', 'Put']:
                        _type = option.lower()
                        _lst = strike[option]['Lst']
                        _chg = strike[option]['Chg']
                        _bid = strike[option]['Bid']
                        _ask = strike[option]['Ask']
                        _vol = strike[option]['Vol']
                        _oi = strike[option]['OI']

                        _symbol = ('{0}{1:02d}{2:02d}{3:02d}{4}{5:08d}'.format(_underlying, _expiry.year - 2000,
                                                                               _expiry.month, _expiry.day,
                                                                               "C" if _type == "call" else "P",
                                                                               int(_strike * 1000)))

                        df.loc[i] = [
                            _strike, _expiry, _type, _symbol, _lst, _bid, _ask, _chg, _vol, _oi, _root, _adjusted,
                            _underlying, _underlying_price, _quotetime
                        ]
                        i += 1
        return df

    def striphtml(self, data):
        p = re.compile(r'<.*?>')
        return p.sub('', data)


class SchwabBrowser(object):
    """ This class is unused """

    _Singleton = None

    @staticmethod
    def Singleton():
        if SchwabBrowser._Singleton is None:
            SchwabBrowser._Singleton = SchwabBrowser()
        return SchwabBrowser._Singleton

    def __init__(self):
        # Find the SCHWAB_USER and SCHWAB_PASSWORD through environment variable
        if 'SCHWAB_USER' not in os.environ:
            print("SCHWAB_USER must be defined in environment")
            sys.exit(1)
        if 'SCHWAB_PASSWORD' not in os.environ:
            print("SCHWAB_PASSWORD must be defined in environment")
            sys.exit(1)
        self.SCHWAB_USER = os.environ['SCHWAB_USER']
        self.SCHWAB_PASSWORD = os.environ['SCHWAB_PASSWORD']

        self.service = service.Service('chromedriver')
        self.browser = None
        self.is_started = False
        self.is_logged_in = False

    def start(self):

        if self.is_started is False:
            self.service.start()

            capabilities = {'chrome.binary': '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome'}
            self.browser = (webdriver.Remote(self.service.service_url, capabilities))
            self.is_started = True

        return

    def login(self):

        self.start()
        assert (self.is_started is True)
        assert (self.browser is not None)

        # Don't login twice
        if self.is_logged_in is True:
            return True

        #######################################
        # Connect to Schwab and login

        br = self.browser
        self.get('https://client.schwab.com/Login/SignOn/CustomerCenterLogin.aspx')

        user = br.find_element_by_id("ctl00_WebPartManager1_CenterLogin_LoginUserControlId_txtLoginID")
        user.send_keys(self.SCHWAB_USER)

        pass_ = br.find_element_by_name("txtPassword")
        pass_.send_keys(self.SCHWAB_PASSWORD)

        select = Select(br.find_element_by_id('ctl00_WebPartManager1_CenterLogin_LoginUserControlId_drpStartPage'))
        select.select_by_visible_text('Research')

        submit = br.find_element_by_name("btnLogin")
        submit.click()  # This blocks until page loads but AJAX may continue
        time.sleep(5)  # Wait additional time for the research page to load
        self.is_logged_in = True
        return

    def get(self, url):
        self.browser.get(url)
        time.sleep(seconds_to_pause)
        return self.browser

    def page_source(self):
        return self.browser.page_source

    def stop(self):
        self.service.stop()
