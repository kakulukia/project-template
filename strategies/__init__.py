from abc import ABC
from datetime import datetime

from jesse.strategies import Strategy
from jesse import indicators as ta
import pytz


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


class RentenStrategy(Strategy, ABC):
    def __init__(self):
        super().__init__()
        self.reset_vars()

    def reset_vars(self):
        ...

    @property
    def date(self):
        return datetime.fromtimestamp(self.current_candle[0] / 1000, tz=pytz.utc).strftime('%Y-%m-%d %H:%M')

    @property
    def tr(self):
        """
        True Range
        :return:
        """
        return ta.trange(self.candles)

    @property
    def tr_p(self):
        """
        True Range Percentage
        :return:
        """
        return self.tr / self.atr_short * 100

    @property
    def range(self):
        return self.close - self.open

    @property
    def range_p(self):
        return self.range / self.atr_short * 100

    @property
    def atr_short(self):
        """
        Average True Range 7 candles
        :return:
        """
        return ta.atr(self.candles, period=7)

    @property
    def atr(self):
        """
        Average True Range
        :return:
        """
        return ta.atr(self.candles, period=14)  #14 period ATR used for calculating stop loss

    @property
    def up(self):
        return self.close > self.open

    @property
    def down(self):
        return self.close < self.open

    @property
    def strong(self):
        return self.range_p > 25 and ((self.range_p / self.tr_p * 100) > 30)

