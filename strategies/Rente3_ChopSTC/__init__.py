from datetime import datetime

from jesse.strategies import Strategy
import jesse.indicators as ta
from jesse import utils
from icecream import ic
from custom_indicators import cae
import pytz
import arrow


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


class Rente3_ChopSTC(Strategy):

    def __init__(self):
        super().__init__()
        self.reset_vars()

    class Candle:

        def __init__(self, data):
            self.data = data
            self.names = ['timestamp', 'open', 'close', 'high', 'low', 'volume']

        def __getitem__(self, key):
            if isinstance(key, str):
                index = self.names.index(key)
                return self.data[index]
            else:
                return self.data[key]

        def __getattr__(self, name):
            if name in self.names:
                index = self.names.index(name)
                return self.data[index]
            else:
                raise AttributeError(f"The candle object has no attribute '{name}'")

        @property
        def date(self):
            return arrow.get(self.timestamp / 1000).to('UTC').format('YYYY-MM-DD HH:mm')

        def __repr__(self):
            return self.date

    @property
    def friendly_candles(self):
        return [self.Candle(candle) for candle in self.candles]

    def reset_vars(self):
        ic("resetting vars")
        self.vars['good_candles'] = 0
        self.vars['max_chop_value'] = 0
        self.vars['max_stc'] = 0
        self.vars['max_profit'] = 0
        self.vars['bad_cycle'] = False
        self.vars['trading_cycle'] = False
        self.vars['rebound'] = False
        self.vars['take_profit'] = False

    @property
    def tr(self):
        return abs(self.open - self.close)

    @property
    def up(self):
        return self.close > self.open

    @property
    def down(self):
        return not self.up

    @property
    def date(self):
        return datetime.fromtimestamp(self.current_candle[0] / 1000, tz=pytz.utc).strftime('%Y-%m-%d %H:%M')

    def should_long(self) -> bool:
        chop = cae(self.candles)
        chop_cat = chop_value(chop)
        prev, stc = ta.stc(self.candles, sequential=True)[-2:]

        if stc < 0.5:
            self.reset_vars()
        if self.vars['take_profit']:
            ic('we already had our fun - not trading anymore')
            return False

        # if the stc went down and we traded this cycle before, we should not trade again
        if stc < self.vars['max_stc'] and self.vars['trading_cycle']:
            self.vars['bad_cycle'] = True
            ic(self.date, chop_cat, "bad cycle", stc, self.vars['max_stc'])

        lets_trade = True
        if prev < stc and stc > 5.0:
            if prev < 0.1:
                ic("uptrend starting")

            if stc < self.vars['max_stc']:
                ic("trend got interrupted - not trading")
                lets_trade = False

            if chop_cat == "down":
                ic("chop is down - not trading")
                lets_trade = False

            # atr = ta.atr(self.candles)
            # if self.tr < atr / 2:
            #     ic(f"tr ({self.tr}) too low - ATR is {atr}")
            if chop < 42:
                ic("and also chop is too low < 42 - not trading", chop)
                lets_trade = False

            if chop > 70:
                ic("chop is too high > 70 - not trading")
                lets_trade = False

            atr = ta.atr(self.candles)
            height_ratio = self.tr / atr
            if height_ratio < 0.20:
                ic("too small candle - not trading")
                lets_trade = False

            if self.tr > atr:
                ic(f"current TR {self.tr} is higher than ATR {atr} - its risky")
                self.vars['bad_cycle'] = True

            self.vars['max_chop_value'] = max(self.vars['max_chop_value'], chop)
            self.vars['max_stc'] = max(self.vars['max_stc'], stc)

            ic(self.date, chop_cat, lets_trade)
            # breakpoint()
            return lets_trade

        else:
            if self.vars['max_stc'] > 5.0:
                ic(self.date, chop_cat, "stc is not going up")

                if self.tr > ta.atr(self.candles):
                    ic("tr is greater than atr - something is happening")
                    if self.down:
                        # try to catch the rebound
                        self.vars['rebound'] = True
                        return True

        return False

    def go_long(self):
        # Open long position and use entire balance to buy
        qty = utils.size_to_qty(self.balance, self.price, fee_rate=self.fee_rate)

        self.buy = qty, self.price
        if self.vars['rebound'] or self.vars['bad_cycle']:
            if self. down:
                self.buy = qty, self.price * 1.005

        self.vars['trading_cycle'] = True

    def should_short(self) -> bool:
        # For futures trading only
        return False

    def go_short(self):
        # For futures trading only
        pass

    def should_cancel_entry(self) -> bool:
        return True

    def on_open_position(self, order) -> None:
        ic("open position")
        self.stop_loss = self.position.qty, self.close * 0.95
        ic("starting stop loss", self.open)
        if self.vars['rebound'] or self.vars['bad_cycle']:
            self.stop_loss = self.position.qty, self.close * 0.98
            self.take_profit = self.position.qty, self.price * 1.05
            ic("take profit", self.take_profit[1])

    def update_position(self):
        stop_loss_percentage = 0.95
        if self.vars['rebound'] or self.vars['bad_cycle']:
            stop_loss_percentage = 0.98
        stop = max(self.stop_loss[0][1], self.close * stop_loss_percentage)
        self.stop_loss = self.position.qty, stop
        ic("current stop loss", stop, self.date)

        chop = cae(self.candles)
        chop_cat = chop_value(chop)
        prev, stc = ta.stc(self.candles, sequential=True)[-2:]

        self.vars['max_profit'] = max(self.vars['max_profit'], self.position.pnl_percentage)
        self.vars['max_chop_value'] = max(self.vars['max_chop_value'], chop)
        self.vars['max_stc'] = max(self.vars['max_stc'], stc)

        up = stc > prev

        sell = False
        if self.vars['max_chop_value'] < 70:
            if chop < self.vars['max_chop_value'] - 15:
                ic("sorted out for bad chop value max - 15")
                sell = True
        else:
            if chop < 60:
                ic("sorted out for bad chop value < 60")
                sell = True
        if not up:
            sell = self.down
            if self.down:
                ic("sorted out for stc down trend")
        if not self.vars['good_candles']:
            ic("tighter stop loss because of no good candles")
            self.stop_loss = self.position.qty, self.position.entry_price * 0.98
            self.vars['bad_cycle'] = True

        if sell:
            ic(self.date, chop_cat, stc)
            ic(round(self.position.pnl_percentage, 2))
            # breakpoint()
            self.reset_vars()
            self.liquidate()

        self.vars['good_candles'] += 1

    def on_close_position(self, order) -> None:
        ic(self.date)
        if order.is_take_profit:
            ic("Take-profit closed the position")
            # breakpoint()
            # if order.pnl_percentage > 5:
            #     self.vars['take_profit'] = True
        elif order.is_stop_loss:
            ic("Stop-loss closed the position")
            self.vars['rebound'] = True
            qty = utils.size_to_qty(self.balance, self.price, fee_rate=self.fee_rate)
            self.buy = qty, self.price * 1.005
        ic(self.trades[-1].pnl_percentage)
        self.vars['bad_cycle'] = True

