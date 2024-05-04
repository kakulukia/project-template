import json
from dataclasses import dataclass, asdict
from datetime import datetime

import numpy as np
import pytz
from benedict import benedict
from jesse.strategies import Strategy, cached
import jesse.indicators as ta
from jesse import utils
from custom_indicators.wrvf import williams_vix_fix as wrvf
from icecream import ic

from strategies import RentenStrategy

from collections import namedtuple


@dataclass
class Trade:
    start: str
    exit: str = None
    exit_ts: int = None
    pnl_percentage: float = None

    def to_dict(self):
        return asdict(self)


class Rente4_WVF(RentenStrategy):

    def __init__(self):
        super().__init__()
        self.vars = benedict(self.vars)
        self.vars.trades = []
        self.vars.prev_trades = []
        self.debug = False

        self.load_trades()

    def reset_vars(self):

        self.vars['last_wvf'] = 0
        self.vars['last_signal'] = 0
        self.vars['max_stc'] = 0
        self.vars['winning_cycle'] = False
        self.vars['num_signals'] = []
        self.vars['trade_next_stc'] = False
        self.vars['max_profit'] = 0

    def save_trades(self):
        if not self.debug:
            return
        filename = 'trades.json'
        trades_dict = [trade.to_dict() for trade in self.vars['trades']]
        with open(filename, 'w') as f:
            json.dump(trades_dict, f, indent=2)

    def load_trades(self):
        if not self.debug:
            return
        filename = 'trades.json'
        try:
            with open(filename, 'r') as f:
                trades_dict = json.load(f)
            self.vars.prev_trades = [Trade(**trade) for trade in trades_dict]
        except FileNotFoundError:
            pass

    def should_long(self) -> bool:

        # preparation
        ########################################################
        if True:
            wvfs, signals = wrvf(self.candles, sequential=True)
            wvf = wvfs[-1]
            signal = signals[-1]
            # stc = ta.stc(self.candles)

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
            trade = False

            # calculate the min signal strength
            indices = np.where(signals == 1)[0]
            selected_values = wvfs[indices]
            average_signal_strength = np.mean(selected_values[-17:])
            min_signal_strength = max([average_signal_strength * 0.66, 2.])

            # for any of the last trades that closed with a loss,
            # add 1. to the min_signal_strength
            if self.vars.trades:
                lookback = 1
                bad_trades = 0
                while lookback < len(self.vars.trades):
                    # but only count trades within the last day
                    if self.vars.trades[-lookback].exit_ts < self.time - 86400_000:
                        # breakpoint()
                        break
                    if self.vars.trades[-lookback].pnl_percentage < 0:
                        bad_trades += 1
                    else:
                        break
                    lookback += 1
                min_signal_strength += bad_trades * 1.5

            ema = ta.ema(self.candles, 77)

        # case 1: acting after a signal
        if self.vars['last_signal'] and not signal:
            ic(self.date)
            ic(round(min_signal_strength, 2))
            ic(signal_length, signals_in_a_row)
            if self.vars['last_wvf'] < min_signal_strength:
                ic("signal too week")

            else:
                ic("strong signal!")
                ic("strong movement - trading: ", self.strong)
                trade = self.strong
                # if self.close > lowest_close:
                #     if low_percentage < 2:
                #         trade = True

        # case 2: acting on a weaker signal
        if signal and wvf < wvfs[-2] - 0.5:
            ic(self.date)
            ic("wvf kleiner")
            if self.up and self.strong:
                ic("strong up")
                # if self.high < self.candles[-2][3]:
                #     ic("Kerze schießt nicht übers Ziel hinaus")
                trade = True

            if self.tr_p > 100 and self.up:
                ic("tr_p > 100")
                ic("lets go!")
                trade = True

            if self.down and self.close > lowest_close:
                ic("down - but looking good")
                trade = True

        # # case 3: acting on specials - not yet
        # if self.vars['trade_next_stc'] and stc > 25.:
        #     ic(self.date)
        #     ic("trading next stc up")
        #     trade = True

        if trade:
            # cross check some things ..
            if self.direction == -2:
                if signals_in_a_row > 5:
                    ic(f"{signals_in_a_row} > 5 - not trading")
                    # TODO: breakpoint()
                    trade = False
            if high_percentage > 5 and self.close == lowest_close:
                ic("free fall - not trading")
                trade = False
            if self.num_worse_candles < 3:
                ic("risky trade - not trading")
                # self.vars['trade_next_stc'] = True
                trade = False
            if self.vars.trades:
                last_trade = self.vars.trades[-1]
                if last_trade.pnl_percentage < 0:
                    compare_time = self.candles[-signal_length][0]
                    if last_trade.exit_ts > compare_time:
                        ic("last trade was a loss and within this signal period - not trading")
                        trade = False
                    if signals_in_a_row > 5:
                        ic(f"{signals_in_a_row} > 5 - not trading")
                        trade = False

        self.vars['last_wvf'] = wvf
        self.vars['last_signal'] = signal

        if trade:
            ic(signals_in_a_row, trade)
            next_trade_index = len(self.vars.trades)
            # we want to break if self.vars.prev_trades has no more trades or the next trade does
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
        stop_atr = self.close - self.atr
        stop_percent = self.close * 0.97
        stop_price = min(stop_atr, stop_percent)
        ic(stop_atr, stop_percent)
        ic("setting stop price at", stop_price)
        self.stop_loss = self.position.qty, stop_price

        # self.take_profit = self.position.qty, self.close * 1.055

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

        stc = ta.stc(self.candles)
        # aroon = ta.aroon(self.candles)

        # if self.date == '2024-03-21 08:00':
        #     breakpoint()

        # update stop loss
        if self.position.pnl_percentage > self.vars['max_profit']:
            sl_percent = self.close * 0.97
            sl_atr = self.close - self.atr * 2
            sl_last = self.stop_loss[0][1] if self.stop_loss is not None else 0
            new_stop_loss = min(sl_percent, sl_atr)
            take_profit = 0
            message = ""

            # if self.vars['winning_cycle'] and stc < 98:
            #     take_profit = self.close - 2 * self.atr
            #     ic("tighter stop due to STC down")
            #     message = f"trying to take profit at {round(take_profit, 4)}"

            if self.tr_p > 200:
                take_profit = self.open + (self.close - self.open) / 2
                ic(self.tr_p)
                message = f"trying to take profit at {round(take_profit, 4)}"

            stop_loss = max(new_stop_loss, sl_last, take_profit)
            ic(sl_percent, sl_atr, sl_last, take_profit)
            message = message or f"setting new stop loss level at {round(stop_loss, 4)}"
            ic(self.date)
            print(message)
            self.stop_loss = self.position.qty, stop_loss

        self.vars['max_profit'] = max(self.vars['max_profit'], self.position.pnl_percentage)

        self.vars['max_stc'] = max([stc, self.vars['max_stc']])
        if self.vars['max_stc'] > 98:
            self.vars['winning_cycle'] = True

    def on_close_position(self, order) -> None:
        ic(self.date)
        if order.is_take_profit:
            ic("Take-profit closed the position")
        elif order.is_stop_loss:
            ic("Stop-loss closed the position")
        ic(self.trades[-1].pnl_percentage)
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
                        ic("EXIT DATE NOT MATCHING")
                    if not pnl_match:
                        ic("PnL NOT MATCHING")

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
        while self.candles[-lookback][2] < self.close:
            worse_candles += 1
            lookback += 1
        return worse_candles

    @property
    def direction(self, length=77):
        close_prices = self.candles[-length:, 2]
        lower_count = np.sum(close_prices < self.close)
        total_count = len(close_prices)

        # Calculate the percentage of lower close prices
        lower_percentage = lower_count / total_count

        # Determine the direction based on the lower percentage
        if lower_percentage >= 0.8:
            direction = 2  # Strong upward direction
        elif lower_percentage >= 0.6:
            direction = 1  # Mild upward direction
        elif lower_percentage <= 0.2:
            direction = -2  # Strong downward direction
        elif lower_percentage <= 0.4:
            direction = -1  # Mild downward direction
        else:
            direction = 0  # Sideways direction

        return direction

