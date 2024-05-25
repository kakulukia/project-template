#!/usr/bin/env python
# -*- coding: utf-8 -*-

import jesse.helpers as jh
from jesse.research import get_candles
from jesse.research.reinforcement_learning import train, AgentTrainingConfig


if __name__ == "__main__":
    exchange_name = "Binance Spot"
    timeframe = "30m"

    start_date = jh.date_to_timestamp("2024-01-01")
    end_date = jh.date_to_timestamp("2024-05-10")

    strategy = "Rente6_RL"

    btc_30m_config = AgentTrainingConfig(
        candles={
            jh.key(exchange_name, "BTC-USDT"): {
                "exchange": exchange_name,
                "symbol": "BTC-USDT",
                "candles": get_candles(
                    exchange_name,
                    "BTC-USDT",
                    timeframe=timeframe,
                    start_date_timestamp=start_date,
                    finish_date_timestamp=end_date,
                    warmup_candles_num=0,
                    caching=True,
                    is_for_jesse=True,
                )[1],
            },
        },
        route={
            "exchange": exchange_name,
            "symbol": "BTC-USDT",
            "timeframe": timeframe,
            "strategy": strategy,
        },
    )

    eth_30m_config = AgentTrainingConfig(
        candles={
            jh.key(exchange_name, "ETH-USDT"): {
                "exchange": exchange_name,
                "symbol": "ETH-USDT",
                "candles": get_candles(
                    exchange_name,
                    "ETH-USDT",
                    timeframe=timeframe,
                    start_date_timestamp=start_date,
                    finish_date_timestamp=end_date,
                    warmup_candles_num=0,
                    caching=True,
                    is_for_jesse=True,
                )[1],
            },
        },
        route={
            "exchange": exchange_name,
            "symbol": "ETH-USDT",
            "timeframe": timeframe,
            "strategy": strategy,
        },
    )

    sol_30m_config = AgentTrainingConfig(
        candles={
            jh.key(exchange_name, "SOL-USDT"): {
                "exchange": exchange_name,
                "symbol": "SOL-USDT",
                "candles": get_candles(
                    exchange_name,
                    "SOL-USDT",
                    timeframe=timeframe,
                    start_date_timestamp=start_date,
                    finish_date_timestamp=end_date,
                    warmup_candles_num=0,
                    caching=True,
                    is_for_jesse=True,
                )[1],
            },
        },
        route={
            "exchange": exchange_name,
            "symbol": "SOL-USDT",
            "timeframe": timeframe,
            "strategy": strategy,
        },
    )
    train_configs = [btc_30m_config, eth_30m_config, sol_30m_config]
    train(
        train_configs,
        n_jobs=1,
        episodes=2000,
        candles_per_episode=48 * 14,
        num_warmup_candles=48 * 30,
    )
