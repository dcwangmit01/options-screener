from pandas_datareader.data import Options
import requests_cache
import datetime

#####################################################################
# Settings

# tickers to fetch data for
tickers = [
    'SPY', 'QQQ', 'TWTR', 'GRPN', 'SHLD', 'AAPL', 'GOOG', 'AMZN', 'MSFT', 'FB'
]

# output file name
outfile = 'long_puts.csv'

# cache settings
days_to_cache = 1

# CSV columns to export
csv_cols = [
    'xBreakEvenDrop%',
    'xPremium',
    'xDaysUntilExpiration',
    'xBreakEvenDrop',
    'xBreakEvenPrice',
    'Root',
    'Underlying_Price',
    'Strike',
    'Type',
    'Expiry',
    'Symbol',
    'Bid',
    'Ask',
    'Last',
    'Vol',
    'Open_Int',
    'IV',
    'xBankrupcyReturn%',
]

# CSV columns to sort by
sort_cols = ['xDaysUntilExpiration', 'xBreakEvenDrop%']

#####################################################################
# Functions


def long_puts_csv_out(filename, df):
    # calls
    # not expired
    # out of the money
    # greater than 2 weeks from expiration
    # volume greater than 1
    # open interest greater than 10
    filtered = df.loc[(df['Type'] == 'puts') & (df['xExpired'] is not True) & (
        df['Strike'] < df['Underlying_Price']) & (df[
            'xDaysUntilExpiration'] >= 14) & (df['Vol'] > 1) & (df[
                'Open_Int'] > 10) & (df['xDaysUntilExpiration'] > 90)]

    ret = filtered.sort_values(
        by=sort_cols, ascending=True).to_csv(
            filename, columns=csv_cols, index=False, float_format='%.2f')
    return ret


def long_puts_process_dataframe(df):
    # reset_index()
    #   copies multi-index values into columns
    #   sets index to single ordinal integer
    df.reset_index(inplace=True)

    # calculate other values
    #  The ask price is a conservative estimate of the current option price
    df['xDaysUntilExpiration'] = df.apply(
        lambda row: (row['Expiry'].to_pydatetime() - today).days, axis=1)
    df['xExpired'] = df.apply(
        lambda row: row['xDaysUntilExpiration'] <= 0, axis=1)
    df['xDividend'] = df.apply(  # placeholder for dividend
        lambda row: 0, axis=1)
    df['xPremium'] = df.apply(
        lambda row: row['Ask'] if row['Ask'] > 0 else row['Last'], axis=1)
    df['xBreakEvenPrice'] = df.apply(
        lambda row: row['Strike'] - row['Ask'], axis=1)
    df['xBreakEvenDrop'] = df.apply(
        lambda row: row['Underlying_Price'] - row['xBreakEvenPrice'], axis=1)
    df['xBreakEvenDrop%'] = df.apply(
        lambda row: 100.0 * row['xBreakEvenDrop'] / row['Underlying_Price'],
        axis=1)
    df['xBankrupcyReturn%'] = df.apply(
        lambda row: 0 if row['xPremium'] == 0 else 100.0 * (row['Strike'] - row['xPremium']) / row['xPremium'],
        axis=1)

    return df


#####################################################################
# Main

# use cache to reduce web traffic
session = requests_cache.CachedSession(
    cache_name='cache',
    backend='sqlite',
    expire_after=datetime.timedelta(days=days_to_cache))

today = datetime.datetime.today()

# all data will also be combined into one CSV
all_df = None

for ticker in tickers:
    option = Options(ticker, 'yahoo', session=session)

    # fetch all data
    df = option.get_all_data()

    # long_puts_csv_out
    df = long_puts_process_dataframe(df)

    # ensure the all_df (contains all data from all tickers)
    if all_df is None:
        all_df = df.copy(deep=True)
    else:
        all_df = all_df.append(df)

# output the all_df, which contains all of the tickers
long_puts_csv_out(outfile, all_df)
