from datetime import datetime

import jesse.helpers as jh
from icecream import ic
from jesse.enums import exchanges, timeframes
from jesse.research import backtest, get_candles

# configure your test values here
################################################
# from strategies.Rente3_ChopSTC import Rente3_ChopSTC
# strategy_class = Rente3_ChopSTC
from strategies.testerei import Testerei
strategy_class = Testerei

start = jh.date_to_timestamp('2024-04-01')
end = jh.date_to_timestamp('2024-04-24')

symbols = [
    # 'BTC-USDT',
    # 'ETH-USDT',
    # 'SOL-USDT',
    'DOGE-USDT',
    # 'LTC-USDT',
    # 'FET-USDT',
    # 'PEPE-USDT',
    # 'SHIB-USDT',
    # 'BONK-USDT',
    # 'PEPE-USDT',
]

time_frames = [
    # '1m',
    # '3m',
    # '5m',
    '15m',
    '30m',
    '45m',
    '1h',
    '2h',
    '3h',
    '4h',
    '6h',
    '8h',
    '12h',
    '1D',
    # '3D',
    # '1W',
    # '1M',
]

test_metric = 'net_profit_percentage'
################################################

exchange_name = exchanges.BINANCE_SPOT
config = {
    'starting_balance': 1_000,
    'fee': 0.001,
    # accepted values are 'spot' and 'futures'
    'type': 'spot',
    # only used if type is 'futures'
    'futures_leverage': 2,
    # only used if type is 'futures'
    'futures_leverage_mode': 'cross',
    'exchange': exchange_name,
    'warm_up_candles': 700
}

results = {}

for symbol in symbols:

    for time_frame in time_frames:

        # initialize the results list
        if time_frame not in results:
            results[time_frame] = []

        warmup_candles_num = config['warm_up_candles'] * jh.timeframe_to_one_minutes(time_frame)
        warmup_set, test_set = get_candles(
            exchange_name, symbol, '1m',
            start, end, warmup_candles_num=warmup_candles_num, is_for_jesse=True)
        routes = [
            {'exchange': exchange_name, 'strategy': strategy_class, 'symbol': symbol, 'timeframe': time_frame}
        ]
        extra_routes = []
        test_candles = {
            jh.key(exchange_name, symbol): {
                'exchange': exchange_name,
                'symbol': symbol,
                'candles': test_set,
            },
        }
        warmup_candles = {
            jh.key(exchange_name, symbol): {
                'exchange': exchange_name,
                'symbol': symbol,
                'candles': warmup_set,
            },
        }

        # execute backtest
        result = backtest(
            config,
            routes,
            extra_routes,
            candles=test_candles,
            warmup_candles=warmup_candles,
            generate_charts=True,
        )
        print("====================================================")
        print(f"Results for {symbol} on {time_frame}")
        ic(result)
        results[time_frame].append(result['metrics'][test_metric])

# for all the lists in the results dictionary, find the one with the highest average value
averages = {k: sum(v) / len(v) for k, v in results.items()}
# sort the averages dictionary by value
sorted_averages = sorted(averages.items(), key=lambda item: item[1], reverse=True)
ic(sorted_averages)


