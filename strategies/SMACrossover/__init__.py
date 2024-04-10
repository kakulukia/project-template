from datetime import datetime

from jesse.strategies import Strategy, cached
import jesse.indicators as ta
from jesse import utils
from icecream import ic


class ExampleStrategy(Strategy):

    @property
    def tr(self):
        if self.up:
            return self.close - self.open
        else:
            return self.open - self.close

    @property
    def up(self):
        return self.close < self.open

    @property
    def down(self):
        return not self.up

    def should_long(self) -> bool:

        super_trend = ta.supertrend(self.candles)

        if self.up:
            atr = ta.atr(self.candles)
            sma = ta.sma(candles=self.candles, period=20)
            if self.close > sma + atr / 2:
                ic(datetime.fromtimestamp(self.time/1000).strftime('%Y-%m-%d %H:%M'))
                ic(self.open, self.close)
                return True
        return False

    def should_cancel_entry(self) -> bool:
        return False

    def go_long(self):
        self.buy = 1, self.price

    def update_position(self) -> None:
        sma = ta.sma(self.candles, period=20)
        atr = ta.atr(self.candles)

        if self.close < (sma - atr / 2):
            ic(datetime.fromtimestamp(self.time / 1000).strftime('%Y-%m-%d %H:%M'))
            ic(f"closing position: current_sma {sma} - close: {self.close}")
            self.liquidate()
        else: ic(f"all still fine: {datetime.fromtimestamp(self.time/1000).strftime('%H:%M')} - {self.close}")
