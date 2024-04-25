from jesse.strategies import Strategy, cached
import jesse.indicators as ta
from jesse import utils
from custom_indicators.wrvf import williams_vix_fix as wrvf
from icecream import ic

from strategies import RentenStrategy


class Testerei(RentenStrategy):

    def reset_vars(self):
        self.vars['last_wvf'] = 0
        self.vars['last_signal'] = 0
        self.vars['max_stc'] = 0
        self.vars['winning_cycle'] = False

    def should_long(self) -> bool:

        wvf, signal = wrvf(self.candles)
        if self.vars['last_wvf'] > wvf and self.vars['last_signal'] and not signal:
            ic(self.date)
            # breakpoint()
            return True

        self.vars['last_wvf'] = wvf
        self.vars['last_signal'] = signal

        return False

    def go_long(self):
        # Open long position and use entire balance to buy
        qty = utils.size_to_qty(self.balance, self.price, fee_rate=self.fee_rate)
        self.buy = qty, self.price

    def on_open_position(self, order):
        self.stop_loss = self.position.qty, self.close * 0.985

    def should_short(self) -> bool:
        # For futures trading only
        return False

    def go_short(self):
        # For futures trading only
        pass

    def should_cancel_entry(self) -> bool:
        return True

    def update_position(self):

        stc = ta.stc(self.candles)
        self.vars['max_stc'] = max([stc, self.vars['max_stc']])
        if self.vars['max_stc'] > 95:
            self.vars['winning_cycle'] = True

        if self.vars['winning_cycle']:
            if stc < 75:
                self.liquidate()
                self.reset_vars()
                self.vars['max_stc'] = 0

    def on_close_position(self, order) -> None:
        ic(self.date)
        if order.is_take_profit:
            ic("Take-profit closed the position")
        elif order.is_stop_loss:
            ic("Stop-loss closed the position")
        ic(self.trades[-1].pnl_percentage)
