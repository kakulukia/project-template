from enum import Enum

import numpy as np
from jesse.strategies import Strategy, cached
import jesse.indicators as ta
from gymnasium import spaces, Space
from jesse import utils
from jesse.research.reinforcement_learning import AgentSettings


class Rente6_RL(Strategy):

    class MyCustomActions(Enum):
        NONE = 0
        GO_LONG = 1
        LIQUIDATE = 2

    def __init__(self) -> None:
        super().__init__()
        self._prev_pnl = 0
        self.curr_reward = 0

    def before(self) -> None:
        self.curr_reward = self.position.pnl - self._prev_pnl
        self._prev_pnl = self.position.pnl

    def agent_settings(self) -> AgentSettings:
        return AgentSettings(
            # agent_path=r"storage\agents\LongRLVPStrategy-generation-1000-1714631910",
            agent_path=None,
            actions_space=list(Rente6_RL.MyCustomActions),
            env_space=spaces.Box(
                low=0,
                high=1,
                shape=(2,),
                dtype=float,
            ),
            net_config={
                "arch": "mlp",
                "hidden_size": [32, 32],
            }
        )

    def env_observation(self) -> np.ndarray:
        close_ratio = (self.close - self.low) / (self.high - self.low)
        open_ratio = (self.open - self.low) / (self.high - self.low)
        return np.array([open_ratio, close_ratio])

    def agent_reward(self) -> float:
        return self.curr_reward

    def should_long(self) -> bool:
        return self.agent_action == Rente6_RL.MyCustomActions.GO_LONG

    def go_long(self) -> None:
        qty = utils.size_to_qty(1000, self.price, fee_rate=self.fee_rate)
        self.buy = qty, self.price

    def update_position(self) -> None:
        if self.agent_action == Rente6_RL.MyCustomActions.LIQUIDATE:
            self.liquidate()

    def should_cancel_entry(self) -> bool:
        return False


open  3.2676
high  3.3647
low   3.2270
close 3.3059
