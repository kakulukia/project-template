import json
import os
from datetime import datetime

from jesse.strategies import Strategy, cached
import jesse.indicators as ta
import jesse.helpers as jh
from jesse import utils
from icecream import ic
from custom_indicators import cae, ott, st
import JesseTradingViewLightReport
import pytz
from jesse.store import store
from jesse.config import config


def chop_value(value):
    """
    The chop is RSI movement between 40 and 60
    tight chop is RSI movement between 45 and 55. There should be an explosion after RSI breaks through 60 (long) or
    40 (short). Tight chop bars are colored black, a series of black bars is tight consolidation and should explode imminently.
    The longer the chop the longer the explosion will go for. tighter the better.

    Loose chop (whip saw/yellow bars) will range between 40 and 60.
    the move begins with blue bars for long and purple bars for short.
    Couple it with your trading system to help stay out of chop and enter when there is movement. Use with "Simple Trender."

    :param value:
    :return up, chop, down and tight:
    """
    if value > 60:
        return "up"
    if value < 40:
        return "down"
    if 40 <= value <= 45:
        return "tight-down"
    if 55 <= value <= 60:
        return "tight-up"
    return "chop"


class Rente2(Strategy):
    """
    Dieses Mal probieren wir Optimized Trend Tracker, Simple Trender und Chop and Explode
    """

    def __init__(self):
        super().__init__()
        self.reset_vars()

    def reset_vars(self):
        self.vars['starting_downtrend_found'] = False
        self.vars['good_candles'] = 0
        self.vars['max_chop_value'] = 0
        self.vars['max_profit'] = 0

    @property
    def date(self):
        return datetime.fromtimestamp(self.current_candle[0] / 1000, tz=pytz.utc).strftime('%Y-%m-%d %H:%M')

    def should_long(self) -> bool:
        prev_chop, chop = cae(self.candles, sequential=True)[-2:]
        trender = st(self.candles, sequential=True)
        chop_cat = chop_value(chop)
        buy = trender.buy_signal[-1]

        if not buy:
            self.reset_vars()
            if not self.vars['starting_downtrend_found']:
                self.vars['starting_downtrend_found'] = True
            return False

        if buy:
            if not self.vars['starting_downtrend_found']:
                return False
            self.vars['good_candles'] += 1
            self.vars['max_chop_value'] = max(self.vars['max_chop_value'], chop)
            ic(self.date, chop_cat)

            min_chop = 55
            downtrend = trender.long_ema[-2] > trender.long_ema[-1]
            if downtrend:
                min_chop = 60
            ic(downtrend, chop)
            if chop > min_chop:
                if downtrend:
                    if prev_chop > 55 and trender.short_ema[-1] > trender.mvwap[-1]:
                        # breakpoint()
                        return True
                else:
                    # breakpoint()
                    return True
        return False

    def go_long(self):
        # Open long position and use entire balance to buy
        qty = utils.size_to_qty(self.balance, self.price, fee_rate=self.fee_rate)
        # ic(qty, self.price, self.fee_rate)
        self.buy = qty, self.price

    def should_short(self) -> bool:
        # For futures trading only
        return False

    def go_short(self):
        # For futures trading only
        pass

    def should_cancel_entry(self) -> bool:
        return True

    def update_position(self):
        # ic(self.stop_loss)
        # stop = max(self.stop_loss[0][1], self.close * 0.95)
        # ic(stop)
        # self.stop_loss = self.position.qty, stop
        # ic("current stop loss", stop)

        chop = cae(self.candles)
        chop_cat = chop_value(chop)
        trender = st(self.candles, sequential=True)
        downtrend = trender.long_ema[-2] > trender.long_ema[-1]

        self.vars['max_profit'] = max(self.vars['max_profit'], self.position.pnl_percentage)

        buy_signal = trender.buy_signal[-1]
        if buy_signal:
            self.vars['good_candles'] += 1
            self.vars['max_chop_value'] = max(self.vars['max_chop_value'], chop)

        sell = False
        min_chop = 50 if downtrend else 45
        max_chop_loose = 10 if downtrend else 17
        if self.position.pnl_percentage < self.vars['max_profit'] * 0.75:
            ic("sorted out for bad profit")
            sell = True
        if chop < min_chop:
            ic("sorted out for bad chop value < 50")
            sell = True
        if self.price < trender.short_ema[-1]:
            ic("sorted out for price below short ema")
            sell = True
        if not buy_signal:
            ic("sorted out because of sell signal")
            sell = True
        if chop < self.vars['max_chop_value'] - max_chop_loose:
            ic("sorted out because chop value got too low")
            sell = True

        if sell:
            ic(self.date, chop_cat)
            ic(round(self.position.pnl_percentage, 2))
            # breakpoint()
            self.reset_vars()
            self.liquidate()

    # def on_open_position(self, order) -> None:
    #     self.stop_loss = self.position.qty, self.price * 0.97

    def on_close_position(self, order) -> None:
        # ic(self.date)
        # ic(self.trades[-1].pnl_percentage)
        # self.vars['first_good_close'] = None
        # self.vars['first_good_close_date'] = None
        # breakpoint()
        pass

    def terminate(self):
        # self.store_json()
        ...

    def store_json(self):
        start_date = str(datetime.fromtimestamp(store.app.starting_time / 1000))[0:10]
        finish_date = str(datetime.fromtimestamp(store.app.time / 1000))[0:10]
        exchange = 'BF' if self.exchange == 'Binance Perpetual Futures' else self.exchange
        sid = jh.get_session_id()
        file_name = f"{self.name.__name__}_{exchange}_{self.symbol}_{self.timeframe}_{start_date}_{finish_date}_{sid}"
        trades_json = {'trades': [], 'considering_timeframes': config['app']['considering_timeframes']}
        for t in store.completed_trades.trades:
            trades_json['trades'].append(self.to_json(t))

        json_path = f'storage/json/{file_name}.json'
        ic(json_path)

        os.makedirs('./storage/json', exist_ok=True)
        with open(json_path, 'w+') as outfile:
            def set_default(obj):
                if isinstance(obj, set):
                    return list(obj)
                raise TypeError

            json.dump(trades_json, outfile, default=set_default)

    @staticmethod
    def to_json(trade):
        orders = [o.__dict__ for o in trade.orders]
        exchange = 'Binance Futures' if trade.exchange == 'Binance Perpetual Futures' else trade.exchange
        return {
            "id": trade.id,
            "strategy_name": trade.strategy_name.__name__,
            "symbol": trade.symbol,
            "exchange": exchange,
            "type": trade.type,
            "entry_price": trade.entry_price,
            "exit_price": trade.exit_price,
            "qty": trade.qty,
            "fee": trade.fee,
            "size": trade.size,
            "PNL": trade.pnl,
            "PNL_percentage": trade.pnl_percentage,
            "holding_period": trade.holding_period,
            "opened_at": trade.opened_at,
            "closed_at": trade.closed_at,
            "entry_candle_timestamp": trade.opened_at,
            "exit_candle_timestamp": trade.closed_at,
            "orders": orders,
        }
