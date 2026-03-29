"""
Trading Strategy - EDITABLE BY AGENT
The agent may modify anything in this file.
"""

import numpy as np
import pandas as pd

# CONFIG dict: agent tunes these values
# The keys in CONFIG are counted for complexity scoring
CONFIG = {
    "channel_period": 40,
    "sma_slow": 200,
    "atr_period": 10,
}


def generate_signals(df: pd.DataFrame) -> pd.Series:
    """
    Given a DataFrame with columns [Open, High, Low, Close, Volume],
    return a Series of signals: 1 = go long, 0 = flat/exit.
    Index must match the input DataFrame.
    """
    close = df["Close"]
    high = df["High"]
    low = df["Low"]

    # Donchian-style channel
    period_high = high.rolling(CONFIG["channel_period"]).max()
    period_low = low.rolling(CONFIG["channel_period"]).min()
    channel_mid = (period_high + period_low) / 2

    # Trend filter
    sma_slow = close.rolling(CONFIG["sma_slow"]).mean()

    # ATR-based volatility filter
    tr = pd.concat([
        high - low,
        (high - close.shift(1)).abs(),
        (low - close.shift(1)).abs()
    ], axis=1).max(axis=1)
    atr = tr.rolling(CONFIG["atr_period"]).mean()
    atr_pct = atr / close
    atr_median = atr_pct.rolling(200).median()

    signal = pd.Series(0, index=df.index)
    # Long when close above channel midpoint AND in SMA200 uptrend + low vol
    signal[(close > channel_mid) & (close > sma_slow) & (atr_pct < atr_median * 1.5)] = 1

    return signal
