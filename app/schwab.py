import os
import time
import sys
import re
import json

from utils import JsonUtils

from selenium import webdriver
import selenium.webdriver.chrome.service as service
from selenium.webdriver.support.ui import Select

# Time in seconds to sleep in betwen requests
SLEEP_TIME = 5

# Find tHe SCHWAB_USER and SCHWAB_PASSWORD through environment variable
if 'SCHWAB_USER' not in os.environ:
    print("SCHWAB_USER must be defined in environment")
    sys.exit(1)
if 'SCHWAB_PASSWORD' not in os.environ:
    print("SCHWAB_PASSWORD must be defined in environment")
    sys.exit(1)
SCHWAB_USER = os.environ['SCHWAB_USER']
SCHWAB_PASSWORD = os.environ['SCHWAB_PASSWORD']


def striphtml(data):
    p = re.compile(r'<.*?>')
    return p.sub('', data)


#######################################
# Connect to Schwab and login

service = service.Service('chromedriver')
service.start()
capabilities = {
    'chrome.binary':
    '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome'
}

br = webdriver.Remote(service.service_url, capabilities)  # br is browser
br.get('https://client.schwab.com/Login/SignOn/CustomerCenterLogin.aspx')

user = br.find_element_by_id(
    "ctl00_WebPartManager1_CenterLogin_LoginUserControlId_txtLoginID")
user.send_keys(SCHWAB_USER)

pass_ = br.find_element_by_name("txtPassword")
pass_.send_keys(SCHWAB_PASSWORD)

select = Select(
    br.find_element_by_id(
        'ctl00_WebPartManager1_CenterLogin_LoginUserControlId_drpStartPage'))
select.select_by_visible_text('Research')

submit = br.find_element_by_name("btnLogin")
submit.click()

time.sleep(SLEEP_TIME)

#######################################
# Process the data

ticker = 'GOOG'

#br.get('https://www.schwab.wallst.com/research/Client/Stocks/Summary/QuoteDetailsModule?symbol=' + ticker)
#quote_source = br.page_source

time.sleep(SLEEP_TIME)

options_source = br.get(
    'https://client.schwab.com/trade/options/optionChainsJson.ashx?autopage=true&symbol='
    + ticker)
options_source = br.page_source

import ipdb
ipdb.set_trace()
options_dict = json.loads(striphtml(options_source))

for root in options_dict['Roots']:
    if root['Root'] != ticker:  # skip over non main roots
        next
    for expiration in root['Expirations']:
        for strike in expiration['Strikes']:
            print(strike['Price'])

import ipdb
ipdb.set_trace()

service.stop()
