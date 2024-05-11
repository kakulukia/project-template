from random import random

import numpy as np
import jesse.indicators as ta
from jesse import utils

from custom_indicators.wrvf import williams_vix_fix as wrvf
from icecream import ic

from strategies import RentenStrategy, Trade


class Rente5_RSI_WVF(RentenStrategy):

    def __init__(self):
        super().__init__()
        self.stop_loss_percentage = 0.94  # 6% stop loss

        self.debug = True
        self.record_trades = True
        self.load_trades()

        if not self.debug:
            ic.disable()

    def reset_vars(self):
        self.vars.max_profit = 0
        self.vars.low_rsi_ts = 0
        self.vars.upper_rsi_reached = False

    def hyperparameters(self):
        return [
            {'name': 'max_signal_gap', 'type': int, 'min': 1, 'max': 50, 'default': 3},
            {'name': 'min_signal_strength_lookback', 'type': int, 'min': 1, 'max': 400, 'default': 17},
            {'name': 'min_signal_multiplier', 'type': float, 'min': 0.1, 'max': 3., 'default': 0.66},
            {'name': 'min_signal_low', 'type': float, 'min': 0.1, 'max': 20., 'default': 2.},
            {'name': 'max_signal_length', 'type': int, 'min': 1, 'max': 50, 'default': 5},

            # {'name': 'lookback_candles', 'type': int, 'min': 1, 'max': 400, 'default': 77},
            # {'name': 'bad_trades_period', 'type': int, 'min': 60_000, 'max': 20 * 24 * 60 * 60 * 1_000,
            #  'default': 86_400_000},
            # {'name': 'bad_trades_penalty', 'type': float, 'min': 0.1, 'max': 5., 'default': 1.5},
            # {'name': 'signal_penalty_threshold', 'type': float, 'min': -20., 'max': 20., 'default': 0.},
            # {'name': 'signal_reward_threshold', 'type': float, 'min': -5., 'max': 20., 'default': 5.},
            # {'name': 'lower_percentage_min', 'type': float, 'min': 0., 'max': 100., 'default': 45.},
            # {'name': 'lower_percentage_max', 'type': float, 'min': 0., 'max': 100., 'default': 65.},
            # {'name': 'upward_reward_multiplier', 'type': float, 'min': 0.1, 'max': 3., 'default': 0.5},
            # {'name': 'max_short_term_high', 'type': float, 'min': 0., 'max': 100., 'default': 5.},
            # {'name': 'max_worse_candles', 'type': int, 'min': 1, 'max': 50, 'default': 3},
            # {'name': 'lower_percentage_threshold', 'type': float, 'min': 0., 'max': 100., 'default': 77},
            # {'name': 'true_range_threshold', 'type': float, 'min': 0., 'max': 300., 'default': 100},
        ]

    def should_long(self) -> bool:

        # preparation
        ################################################################################################################
        if True:
            wvfs, signals = wrvf(self.candles, sequential=True)
            wvf = wvfs[-1]
            signal = signals[-1]
            last_signal = signals[-2]
            rsi = ta.rsi(self.candles, sequential=True)
            rsi_ma = ta.sma(rsi, 14)

            # check the signal length
            signal_length = self.get_signal_length(signals)

            # calculate the min signal strength
            indices = np.where(signals == 1)[0]
            selected_values = wvfs[indices]
            average_signal_strength = np.mean(selected_values[-self.hp['min_signal_strength_lookback']:])
            multiplier = self.hp['min_signal_multiplier']
            min_signal_strength = max([average_signal_strength * multiplier, self.hp['min_signal_low']])

        # lets start from here
        ################################################################################################################
        trade = False
        ################################################################################################################
        # min rsi is valid for one day - reset if we went past it
        check_time = self.vars.low_rsi_ts + 24 * 60 * 60 * 1_000
        if self.time > check_time:
            self.vars.low_rsi_ts = 0

        if last_signal and not signal:
            print("==================")
            ic(round(min_signal_strength, 2))
            ic(signal_length)

            # get the min rsi withing the signal length
            min_rsi = np.min(rsi[-(signal_length + 1):])
            ic(min_rsi, rsi[-1], rsi_ma)

            if min_rsi < 25 or self.vars.low_rsi_ts:
                # both conditions match - we could trade
                trade = True
                if not self.vars.low_rsi_ts:
                    self.vars.low_rsi_ts = self.time

                if rsi[-1] < rsi_ma:
                    ic("RSI is below its moving average - not trading")
                    trade = False

                max_signal = np.max(wvfs[-(signal_length + 1):])
                if max_signal < min_signal_strength:
                    ic("signal too week", max_signal)
                    trade = False

                if trade and signal_length > self.hp['max_signal_length']:
                    ic(f"{signal_length} > {self.hp['max_signal_length']} - not trading")
                    trade = False

                if trade and self.short_term_high < -5:
                    price_was_falling = f"by {round(self.short_term_high, 2)} - not trading"
                    ic(price_was_falling)
                    trade = False

        if self.date == '2024-04-14 17:30':
            breakpoint()

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

        trade = Trade(start=self.date, start_ts=self.time)
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
        rsi = ta.rsi(self.candles, sequential=True)
        rsi_ma = ta.sma(rsi, 14)
        if rsi[-1] > 70:
            ic("RSI is above 70 - using more aggressive stopp loss")
            self.vars.upper_rsi_reached = True
        if rsi_ma > rsi[-1]:
            self.vars.upper_rsi_reached = True

            # get the last high since the trade started
            indices = np.where(self.candles[:, 0] > self.vars.trades[-1].start_ts)
            trade_candles = self.candles[indices]
            high = np.max(trade_candles[:, 3])

            new_stop_loss = high * 0.98
            stop_loss = max(new_stop_loss, sl_last)
            if stop_loss > sl_last:
                ic("RSI is below its moving average - using more aggressive stopp loss")
                stop_loss_update = f"setting new stop loss level at {round(stop_loss, 4)}"
                ic(stop_loss_update)
                self.stop_loss = self.position.qty, stop_loss

        if self.position.pnl_percentage > self.vars['max_profit']:

            sl_percent = self.close * self.stop_loss_percentage
            if self.vars.upper_rsi_reached:
                sl_percent = self.close * 0.98
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
            stop_loss_update = stop_loss_update or f"setting new stop loss level at {round(stop_loss, 4)}"
            ic(stop_loss_update)
            self.stop_loss = self.position.qty, stop_loss

        if self.vars['max_profit'] < 5 < self.position.pnl_percentage:
            take_profit = f"trying to take profit at 5% - 1.7% stop loss {self.close * 0.983}"
            ic(take_profit)
            self.take_profit = self.position.qty, self.close * 0.983

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

    @property
    def short_term_high(self, length=7):
        high_prices = self.candles[-length:, 3]
        high = np.max(high_prices)
        return (self.close / high - 1) * 100

    # def dna(self):
    #     return 'FIF-?71/;4fRFF9LA'

    def get_signal_length(self, signals):
        lookback = 2
        signals_in_a_row = signals[-1]
        signal_length = 0
        gap = 0
        while lookback < len(signals) and gap <= self.hp['max_signal_gap']:
            if signals[-lookback]:
                signal_length += gap
                gap = 0
                signals_in_a_row += 1
            else:
                gap += 1
            lookback += 1
        signal_length = int(signals_in_a_row + signal_length)
        return signal_length
