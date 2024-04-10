from jesse.strategies import Strategy, cached
import jesse.indicators as ta
from jesse import utils
from icecream import ic


class Rente1(Strategy):
    def should_long(self) -> bool:
        supertrend, change = ta.supertrend(self.candles)
        self.log(f"Trend is {supertrend} and change is {change}")
        return self.price > supertrend and change

    def go_long(self):
        # Open long position and use entire balance to buy
        qty = utils.size_to_qty(self.balance, self.price, fee_rate=self.fee_rate)
        ic(qty, self.price, self.fee_rate)
        breakpoint()

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
        supertrend, change = ta.supertrend(self.candles)
        self.log(f"Trend is {supertrend} and change is {change}")
        if self.price < supertrend and change:
            self.liquidate()
