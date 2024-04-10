from datetime import datetime

from jesse.strategies import Strategy, cached
import jesse.indicators as ta
from jesse import utils
from icecream import ic
from custom_indicators import cae, ott, st
import JesseTradingViewLightReport
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


class Rente2(Strategy):
    """
    Dieses Mal probieren wir Optimized Trend Tracker, Simple Trender und Chop and Explode
    """

    @property
    def date(self):
        return datetime.fromtimestamp(self.current_candle[0] / 1000, tz=pytz.utc).isoformat()

    def should_long(self) -> bool:
        chop = cae(self.candles)

        trender = st(self.candles, sequential=True)

        val = chop_value(chop)
        if val in ["up", "tight-up"]:
            # ic(self.date)
            # ic(val)
            if trender.buy_signal[-1]:
                # ic(trender.buy_signal[-1])
                if self.price > trender.long_ema[-1]:
                    # ic(self.price, trender.long_ema[-1])
                    # ic(self.open, self.high, self.low, self.close)
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
        val = chop_value(chop)
        trender = st(self.candles)
        if val == "down" or self.price < trender.short_ema or not trender.buy_signal:
            # ic(self.date, val)
            # ic(self.position.pnl_percentage)
            # breakpoint()
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
        JesseTradingViewLightReport.generateReport(
            customData={
                "cae": {"data": cae(self.candles, sequential=True), "options": {"pane": 2}},
            }
        )
