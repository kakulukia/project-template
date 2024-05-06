from random import random

import numpy as np
import jesse.indicators as ta
from jesse import utils
from custom_indicators.wrvf import williams_vix_fix as wrvf
from icecream import ic

from strategies import RentenStrategy, Trade


class Rente4_WVF(RentenStrategy):

    def __init__(self):
        super().__init__()
        self.stop_loss_percentage = 0.97  # 3% stop loss

        self.debug = True
        self.record_trades = False
        self.load_trades()

        if not self.debug:
            ic.disable()

    def reset_vars(self):
        self.vars.max_profit = 0

    def should_long(self) -> bool:

        # stop_here = False
        # if random() > 0.95:
        #     stop_here = True
        #     ic.enable()
        # else:
        #     ic.disable()

        # preparation
        ################################################################################################################
        bad_trades = 0
        if True:
            wvfs, signals = wrvf(self.candles, sequential=True)
            wvf = wvfs[-1]
            signal = signals[-1]
            last_signal = signals[-2]
            # stc = ta.stc(self.candles)

            # check the signal length
            lookback = 2
            signals_in_a_row = signal
            signal_length = 0
            gap = 0
            while lookback < len(signals) and gap <= 3:
                if signals[-lookback]:
                    signal_length += gap
                    gap = 0
                    signals_in_a_row += 1
                else:
                    gap += 1
                lookback += 1
            signal_length = int(signals_in_a_row + signal_length)

            # check for the latest low
            lookback_candles = 7
            lowest_low = np.min(self.candles[-lookback_candles:, 4])
            highest_high = np.max(self.candles[-lookback_candles:, 3])
            high_index = np.argmax(self.candles[-lookback_candles:, 3])
            lowest_close = np.min(self.candles[-lookback_candles + high_index:, 2])

            # calculate percentage of low and high
            low_percentage = (self.close - lowest_low) / lowest_low * 100
            high_percentage = (highest_high - self.close) / self.close * 100

            # calculate the min signal strength
            indices = np.where(signals == 1)[0]
            selected_values = wvfs[indices]
            average_signal_strength = np.mean(selected_values[-17:])
            min_signal_strength = max([average_signal_strength * 0.66, 2.])

            # for any of the last trades that closed with a loss,
            # add 1.5 to the min_signal_strength
            if self.vars.trades:
                lookback = 1
                bad_trades = 0
                while lookback < len(self.vars.trades):
                    # but only count trades within the last day
                    if self.vars.trades[-lookback].exit_ts < self.time - 86400_000:
                        break
                    if self.vars.trades[-lookback].pnl_percentage < 0:
                        bad_trades += 1
                    else:
                        break
                    lookback += 1
                min_signal_strength += bad_trades * 1.5

                # good trade bonus
                if self.vars.trades[-lookback].pnl_percentage > 5:
                    min_signal_strength -= 1

            # slight upwards movement gets rewarded
            if 45 < self.lower_percentage < 65:
                min_signal_strength /= 2

        # lets start from here
        ################################################################################################################
        trade = False
        ################################################################################################################

        # # case 1:  acting on a weaker signal
        # if signal and wvf < wvfs[-2] - 0.5:
        #     ic(self.date)
        #     ic("wvf kleiner")
        #     if self.up and self.strong:
        #         ic("strong up")
        #         # if self.high < self.candles[-2][3]:
        #         #     ic("Kerze schießt nicht übers Ziel hinaus")
        #         trade = True
        #
        #     if self.tr_p > 100 and self.up:
        #         ic("tr_p > 100")
        #         ic("lets go!")
        #         trade = True
        #
        #     if self.down and self.close > lowest_close:
        #         ic("down - but looking good")
        #         trade = True

        # case 2: acting after a signal
        if last_signal and not signal:
            print("==================")
            # ic(self.date)
            ic(round(min_signal_strength, 2), bad_trades)
            ic(self.lower_percentage)
            ic(signals_in_a_row, signal_length,)

            trade = True
            # lets assume we start trading, but run a few more tests
            max_signal = np.max(wvfs[-(signal_length + 1):])
            if max_signal < min_signal_strength:
                ic("signal too week", max_signal)
                trade = False

            if trade and signals_in_a_row > 5:
                ic(f"{signals_in_a_row} > 5 - not trading")
                trade = False

            # if trade and not self.strong:
            #     ic("not strong enough")
            #     ic(
            #         self.range_p, self.range_p > 25, self.tr_p,
            #         (self.range_p / self.tr_p * 100),
            #         ((self.range_p / self.tr_p * 100) > 30)
            #     )
            #     trade = False
            #
            #     upward_movement = (self.close / lowest_low - 1) * 100
            #     if upward_movement > 2:
            #         ic(upward_movement)
            #         trade = True
            #
            #     if self.tr_p > 100:
            #         ic("tr_p > 100")
            #         trade = True

            if trade and high_percentage > 5:
                if self.close == lowest_close:
                    ic("free fall - not trading")
                    trade = False
                if self.num_worse_candles < 3:
                    ic("risky trade - not trading")
                    trade = False

            if trade and self.vars.trades:
                last_trade = self.vars.trades[-1]
                if last_trade.pnl_percentage < 0:
                    compare_time = self.candles[-signal_length][0]
                    if last_trade.exit_ts > compare_time:
                        print("last trade was a loss and within this signal period - not trading")
                        trade = False

            if trade and self.down:
                if self.lower_percentage < 77 or self.tr_p > 100:
                    ic("downwards movement - not trading")
                    trade = False

        # if self.date == '2024-05-04 02:30':
        #     breakpoint()

        if trade:
            ic(trade)
            next_trade_index = len(self.vars.trades)
            # we want to break if self.vars.prev_trades has no more trades or the current trade does
            # not start at self.date
            stop = True
            if self.vars.prev_trades:
                if next_trade_index < len(self.vars.prev_trades):
                    if self.date == self.vars.prev_trades[next_trade_index].start:
                        ic("SAME TRADE")
                        stop = False
            if stop and self.debug:
                breakpoint()

            # if stop_here:
            #     breakpoint()
        else:
            next_trade_index = len(self.vars.trades)
            if self.vars.prev_trades and len(self.vars.prev_trades) > next_trade_index:
                next_trade = self.vars.prev_trades[next_trade_index]
                if self.date == next_trade.start:
                    ic("WE FORGOT SOMETHING")
                    breakpoint()

        return trade

    def go_long(self):
        # Open long position and use entire balance to buy
        qty = utils.size_to_qty(self.balance, self.price, fee_rate=self.fee_rate)
        self.buy = qty, self.price

    def on_open_position(self, order):
        stop_atr = self.close - 2 * self.atr
        stop_percent = self.close * self.stop_loss_percentage
        stop_price = min(stop_atr, stop_percent)
        ic(stop_atr, stop_percent)

        ic(f"setting stop price at {stop_price}")
        self.stop_loss = self.position.qty, stop_price

        trade = Trade(start=self.date)
        self.vars['trades'].append(trade)

        self.save_trades()

    def should_short(self) -> bool:
        # For futures trading only
        return False

    def go_short(self):
        # For futures trading only
        pass

    def should_cancel_entry(self) -> bool:
        return True

    def update_position(self):

        # if self.date == '2024-04-18 11:00':
        #     breakpoint()

        # update stop loss
        sl_last = self.stop_loss[0][1] if self.stop_loss is not None else 0
        if self.position.pnl_percentage > self.vars['max_profit']:
            sl_percent = self.close * self.stop_loss_percentage
            sl_atr = self.close - self.atr * 2
            new_stop_loss = min(sl_percent, sl_atr)
            take_profit = 0
            stop_loss_update = ""

            if self.percent > 2:
                ic(self.percent)
                take_profit = self.open + (self.close - self.open) * 0.66
                ic(self.tr_p)
                stop_loss_update = f"trying to take profit at {round(take_profit, 4)}"

            stop_loss = max(new_stop_loss, sl_last, take_profit)
            # ic(stop_loss, new_sl_percentage)
            # stop_loss = stop_loss * new_sl_percentage
            # ic("after", stop_loss)
            # ic(sl_percent, sl_atr, sl_last, take_profit)
            stop_loss_update = stop_loss_update or f"setting new stop loss level at {round(stop_loss, 4)}"
            ic(stop_loss_update)
            self.stop_loss = self.position.qty, stop_loss

        if self.vars['max_profit'] < 5 < self.position.pnl_percentage:
            ic("trying to take profit at 5% - 1.5% stop loss")
            self.take_profit = self.position.qty, self.close * 0.987

        self.vars['max_profit'] = max(self.vars['max_profit'], self.position.pnl_percentage)

    def on_close_position(self, order) -> None:
        if order.is_take_profit:
            ic("Take-profit closed the position")
        elif order.is_stop_loss:
            ic("Stop-loss closed the position")
        ic(self.trades[-1].pnl_percentage)
        # update the last trade with results
        last_trade = self.vars.trades[-1]
        last_trade.exit = self.date
        last_trade.exit_ts = self.time
        last_trade.pnl_percentage = round(self.trades[-1].pnl_percentage, 2)

        stop = True
        if self.vars.prev_trades:
            if len(self.vars.prev_trades) >= len(self.vars.trades):
                compare_trade = self.vars.prev_trades[len(self.vars.trades) - 1]

                if compare_trade.exit:
                    exit_match = compare_trade.exit == last_trade.exit
                    pnl_match = compare_trade.pnl_percentage == last_trade.pnl_percentage

                    if not exit_match:
                        message = f"EXIT DATE NOT MATCHING - was: {compare_trade.exit}"
                        print(message)
                    if not pnl_match:
                        message = f"PnL NOT MATCHING - was {compare_trade.pnl_percentage}"
                        print(message)

                    stop = not (exit_match and pnl_match)

        if stop and self.debug:
            ic(self.vars['max_profit'])
            breakpoint()

        # if that was fine, save the trade
        if len(self.vars.trades) >= len(self.vars.prev_trades):
            self.save_trades()
        self.reset_vars()

    @property
    def num_worse_candles(self):
        worse_candles = 0
        lookback = 2
        while lookback < len(self.candles) and self.candles[-lookback][2] < self.close:
            worse_candles += 1
            lookback += 1
        return worse_candles

    @property
    def lower_percentage(self, length=77):
        close_prices = self.candles[-length:, 2]
        lower_count = np.sum(close_prices < self.close)
        total_count = len(close_prices)

        # Calculate the percentage of lower close prices
        lower_percentage = lower_count / total_count

        # # Determine the direction based on the lower percentage
        # if lower_percentage >= 0.8:
        #     direction = 2  # Strong upward direction
        # elif lower_percentage >= 0.6:
        #     direction = 1  # Mild upward direction
        # elif lower_percentage <= 0.2:
        #     direction = -2  # Strong downward direction
        # elif lower_percentage <= 0.4:
        #     direction = -1  # Mild downward direction
        # else:
        #     direction = 0  # Sideways direction

        return lower_percentage * 100

