# from jesse.enums import exchanges, timeframes
# from jesse.research import get_candles
# from datetime import datetime
# import jesse.helpers as jh
# from jesse.research import backtest
# import jesse.indicators as ta
# from icecream import ic
# import pytz
#
# symbols = [
#     'BTC-USDT',
#     'ETH-USDT',
#     'SOL-USDT',
#     'DOGE-USDT',
#     'LTC-USDT',
#     'FET-USDT',
#     'PEPE-USDT',
#     'SHIB-USDT',
#     'BONK-USDT',
# ]
# symbol = symbols[7]
# symbol = 'BTC-USDT'
# chart_size = (23, 9)
# exchange_name = exchanges.BINANCE_SPOT
# time_frame = timeframes.MINUTE_1
# config = {
#     'starting_balance': 1_000,
#     'fee': 0.001,
#     # accepted values are 'spot' and 'futures'
#     'type': 'spot',
#     # only used if type is 'futures'
#     'futures_leverage': 2,
#     # only used if type is 'futures'
#     'futures_leverage_mode': 'cross',
#     'exchange': exchange_name,
#     'warm_up_candles': 200
# }
#
# #import_candles(exchanges.BINANCE_SPOT, symbols[7], '2023-01-01', show_progressbar=True)
#
# candles = get_candles(exchange_name, symbol, time_frame, '2024-02-01', '2024-04-02', warmup_candles=200*30)
#
# first_one = candles[0]
# ic(datetime.fromtimestamp(first_one[0] / 1000, tz=pytz.utc))
#
# btc_sma_50 = ta.sma(candles, 50, sequential=True)
# super_trend = ta.supertrend(candles, period=14, factor=3, sequential=True)
#
# btc_close = candles[:, 2]
#
# # convect timestamps into a format that is supported for plotting
# times = [datetime.fromtimestamp(c[0] / 1000) for c in candles]
# changed = [x if x else None for x in super_trend.changed]
# trend = [t if t != 0 else None for t in super_trend.trend]
#
# from strategies.Rente2 import Rente2
#
# time_frame = timeframes.MINUTE_30
# routes = [
#     {'exchange': exchange_name, 'strategy': Rente2, 'symbol': symbol, 'timeframe': time_frame}
# ]
# extra_routes = []
# test_candles = {
#     jh.key(exchange_name, symbol): {
#         'exchange': exchange_name,
#         'symbol': symbol,
#         'candles': candles,
#     },
# }
#
# # execute backtest
# # # # # # # # # # # # # # # #
# result = backtest(
#     config,
#     routes,
#     extra_routes,
#     test_candles,
#     generate_charts=True
# )
# # to access the metrics dict:
# ic(result['metrics'])
# # to access the charts string (path of the generated file):
# ic(result['charts'])
# # to access the logs list:
# ic(result['logs'])
