from pandas_datareader.data import Options
import requests_cache
import datetime
import click
import logging

from app import app
from app import cli as app_cli

log = logging.getLogger(__name__)

app = app.App()
today = datetime.datetime.today()

#####################################################################
# Settings

# cache settings
seconds_to_cache = 60 # * 30  # 30 minutes

# CSV columns to export
csv_cols = [
    'xBreakEvenRise%PerDayUntilExpiration',
    'xBreakEvenRise%',
    'xPremium',
    'xDaysUntilExpiration',
    'xBreakEvenRise',
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
]

# CSV columns to sort by
sort_cols = ['xBreakEvenRise%PerDayUntilExpiration', 'xDaysUntilExpiration', 'xBreakEvenRise%']

#####################################################################
# Click Code


@click.group()
def cli():
    """Subcommand for long calls"""

    pass


@cli.command()
@click.argument('config_yaml')
@click.argument('output_csv')
@app_cli.pass_context
def run(ctx, config_yaml, output_csv):
    """This command loads config.yaml and the current ENV-ironment,
    creates a single merged dict, and prints to stdout.
    """

    # read the configuration file
    c = app.get_config_dict(ctx, [config_yaml])

    # use cache to reduce web traffic
    session = requests_cache.CachedSession(
        cache_name='cache',
        backend='sqlite',
        expire_after=seconds_to_cache)

    # all data will also be combined into one CSV
    all_df = None

    for ticker in c['config']['options']['long_calls']:
        option = Options(ticker, 'yahoo', session=session)

        # fetch all data
        df = option.get_all_data()

        # process the data
        df = long_calls_process_dataframe(df)

        # ensure the all_df (contains all data from all tickers)
        if all_df is None:
            all_df = df.copy(deep=True)
        else:
            all_df = all_df.append(df)

        # output the all_df, which contains all of the tickers
        long_calls_csv_out(output_csv, all_df)


#####################################################################
# Functions


def long_calls_csv_out(filename, df):
    # calls
    # not expired
    # out of the money
    # greater than 2 weeks from expiration
    # volume greater than 1
    # open interest greater than 10
    filtered = df.loc[(df['Type'] == 'call') & (df['xExpired'] is not True) & (
        df['Strike'] > df['Underlying_Price']) & (df[
            'xDaysUntilExpiration'] >= 14) & (df['Vol'] > 1) & (df[
                'Open_Int'] > 10) & (df['xDaysUntilExpiration'] > 4)]

    ret = filtered.sort_values(
        by=sort_cols, ascending=True).to_csv(
            filename, columns=csv_cols, index=False, float_format='%.2f')
    return ret


def long_calls_process_dataframe(df):
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
        lambda row: row['Strike'] + row['Ask'], axis=1)
    df['xBreakEvenRise'] = df.apply(
        lambda row: 0 - row['Underlying_Price'] + row['xBreakEvenPrice'], axis=1)
    df['xBreakEvenRise%'] = df.apply(
        lambda row: 100.0 * row['xBreakEvenRise'] / row['Underlying_Price'],
        axis=1)
    df['xBreakEvenRise%PerDayUntilExpiration'] = df.apply(
        lambda row: 0 if row['xDaysUntilExpiration'] == 0 else row['xBreakEvenRise%'] / row['xDaysUntilExpiration'],
        axis=1)

    return df
