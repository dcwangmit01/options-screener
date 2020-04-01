import datetime
import click
import logging

from app import app
from app import cli as app_cli

from app.tdameritrade import TDAmeritrade

log = logging.getLogger(__name__)

app = app.App()
today = datetime.datetime.today()

#####################################################################
# Settings

# cache settings
seconds_to_cache = 60 * 30  # 30 minutes

# use s_askPrice instead of s_lastPrice to be more conservative in all subsequent calculations
stock_price = 's_askPrice'

#####################################################################
# Click Code


@click.group()
def cli():
    """Subcommand for covered calls"""

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

    # get the client
    tda = TDAmeritrade()
    tdc = tda.getClient()

    # all data will also be combined into one CSV
    all_df = None

    for ticker in c['config']['options']['covered_calls']:

        # fetch all data
        stock = tdc.quoteDF(ticker)
        option = tdc.optionsDF(ticker)

        # process the data
        df = covered_calls_process_dataframe(stock, option)

        # ensure the all_df (contains all data from all tickers)
        if all_df is None:
            all_df = df.copy(deep=True)
        else:
            all_df = all_df.append(df)

    # output the all_df, which contains all of the tickers
    covered_calls_csv_out(output_csv, all_df)


#####################################################################
# Functions


def covered_calls_csv_out(filename, df):

    # CSV columns to sort by
    sort_cols = ['xo_staticRetAnn%', 'xo_staticRet%', 'xo_assignedRetAnn%']

    # CSV columns to export first.  All fields will be included afterwards
    first_cols = [
        # 'xo_premium',
        # 'xo_assignedRet%',
        'xo_staticRetAnn%',
        'xo_staticRet%',
        'xo_assignedRetAnn%',
        'xo_inTheMoney%',
        'xo_staticRet$',
        'o_daysToExpiration',
        's_symbol',
        's_askPrice',
        'o_strikePrice',
        'o_putCall',
        'o_expirationDate',
        'o_symbol',
        'o_bid',
        'o_ask',
        'o_last',
        'o_totalVolume',
        'o_openInterest',
        'o_volatility',
    ]

    # reorder the cols so that first_cols are first
    csv_cols = df.columns.to_list().copy()
    tmp_cols = []
    for c in first_cols:
        if c not in csv_cols:
            print(f"{c} is not in csv_cols")
        csv_cols.remove(c)
        tmp_cols.append(c)
    csv_cols = tmp_cols + csv_cols

    # calls
    # out of the money
    # greater than 2 weeks from expiration
    # volume greater than 1
    # open interest greater than 10
    filtered = df.loc[True
                      & (df['o_putCall'] == 'CALL')
                      & (df['o_daysToExpiration'] >= 7)
                      & (df['o_strikePrice'] > df['s_askPrice'])  # Uncomment to only show out of the money
                      & (df['o_totalVolume'] > 1)
                      & (df['o_openInterest'] > 20)
                      & (df['o_bid'] > 0.25)]

    ret = filtered.sort_values(by=sort_cols, ascending=False).to_csv(filename,
                                                                     columns=csv_cols,
                                                                     index=False,
                                                                     float_format='%.2f')
    return ret


def covered_calls_process_dataframe(stock_df, options_df):
    # reset_index()
    #   copies multi-index values into columns
    #   sets index to single ordinal integer

    stock_df = stock_df.add_prefix("s_")
    options_df = options_df.add_prefix("o_")

    # copy every value in stock_df to every item in options_df
    df = options_df.copy(deep=True)
    for c in stock_df.columns.to_list():
        df[c] = stock_df.iloc[0][c]
    """
      ['s_52WkHigh', 's_52WkLow', 's_askId', 's_askPrice', 's_askSize',
       's_assetMainType', 's_assetSubType', 's_assetType', 's_bidId',
       's_bidPrice', 's_bidSize', 's_bidTick', 's_closePrice', 's_cusip',
       's_delayed', 's_description', 's_digits', 's_divAmount', 's_divDate',
       's_divYield', 's_exchange', 's_exchangeName', 's_highPrice', 's_lastId',
       's_lastPrice', 's_lastSize', 's_lowPrice', 's_marginable', 's_mark',
       's_markChangeInDouble', 's_markPercentChangeInDouble', 's_nAV',
       's_netChange', 's_netPercentChangeInDouble', 's_openPrice', 's_peRatio',
       's_quoteTimeInLong', 's_regularMarketLastPrice',
       's_regularMarketLastSize', 's_regularMarketNetChange',
       's_regularMarketPercentChangeInDouble',
       's_regularMarketTradeTimeInLong', 's_securityStatus', 's_shortable',
       's_symbol', 's_totalVolume', 's_tradeTimeInLong', 's_volatility',
       'o_putCall', 'o_symbol', 'o_description', 'o_exchangeName', 'o_bid',
       'o_ask', 'o_last', 'o_mark', 'o_bidSize', 'o_askSize', 'o_bidAskSize',
       'o_lastSize', 'o_highPrice', 'o_lowPrice', 'o_openPrice',
       'o_closePrice', 'o_totalVolume', 'o_tradeDate', 'o_tradeTimeInLong',
       'o_quoteTimeInLong', 'o_netChange', 'o_volatility', 'o_delta',
       'o_gamma', 'o_theta', 'o_vega', 'o_rho', 'o_openInterest',
       'o_timeValue', 'o_theoreticalOptionValue', 'o_theoreticalVolatility',
       'o_optionDeliverablesList', 'o_strikePrice', 'o_expirationDate',
       'o_daysToExpiration', 'o_expirationType', 'o_lastTradingDay',
       'o_multiplier', 'o_settlementType', 'o_deliverableNote',
       'o_isIndexOption', 'o_percentChange', 'o_markChange',
       'o_markPercentChange', 'o_mini', 'o_inTheMoney', 'o_nonStandard']
    """

    # calculate other values
    #  The bid price is a conservative estimate of the current option price
    df['xo_premium'] = df.apply(lambda row: row['o_bid'] if row['o_bid'] > 0 else row['o_last'], axis=1)
    df['xo_inTheMoney%'] = df.apply(lambda row: 0 if row['o_inTheMoney'] == 'True' else
                                    (100.0 * (row[stock_price] - row['o_strikePrice']) / row[stock_price]),
                                    axis=1)

    def static_return_dollars(row):
        if row[stock_price] <= row['o_strikePrice']:
            # out of the money or at the money
            return row['xo_premium']
        else:
            # in the money
            return row['xo_premium'] + row['o_strikePrice'] - row[stock_price]

    df['xo_staticRet$'] = df.apply(static_return_dollars, axis=1)
    df['xo_staticRet%'] = df.apply(lambda row: 100.0 * row['xo_staticRet$'] / row[stock_price], axis=1)
    df['xo_staticRetAnn%'] = df.apply(lambda row: 0 if row['o_daysToExpiration'] <= 0 else
                                      (row['xo_staticRet%'] * 365.0 / row['o_daysToExpiration']),
                                      axis=1)
    df['xo_assignedRet%'] = df.apply(lambda row: 100.0 *
                                     (row['xo_premium'] + row['o_strikePrice'] - row[stock_price]) / row[stock_price],
                                     axis=1)
    df['xo_assignedRetAnn%'] = df.apply(
        lambda row: 0 if row['o_daysToExpiration'] <= 0 else row['xo_assignedRet%'] * 365.0 / row['o_daysToExpiration'],
        axis=1)

    return df
