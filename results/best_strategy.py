"""
Trading Strategy - EDITABLE BY AGENT
The agent may modify anything in this file.
"""

import numpy as np
import pandas as pd

# CONFIG dict: agent tunes these values
# The keys in CONFIG are counted for complexity scoring
CONFIG = {
    "sma_fast": 40,
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

    sma_fast = close.rolling(CONFIG["sma_fast"]).mean()
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

    # SMA200 must be above its own 200-day MA (long-term trend filter)
    sma_slow_ma = sma_slow.rolling(200).mean()

    signal = pd.Series(0, index=df.index)
    # Long when crossover + low vol + SMA200 itself is in an uptrend
    signal[(sma_fast > sma_slow) & (atr_pct < atr_median * 1.5) & (sma_slow > sma_slow_ma)] = 1

    return signal
