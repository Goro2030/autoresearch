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

    # Distance from fast SMA and slow SMA
    distance_fast = (close - sma_fast) / sma_fast
    distance_slow = (close - sma_slow) / sma_slow

    # Primary conditions
    trend_ok = sma_fast > sma_slow
    vol_ok = atr_pct < atr_median * 1.5
    dist_ok = (distance_slow < 0.25) & (distance_fast < 0.10)

    # Try using absolute distance from SMA200 in normalized units (ATR-scaled)
    dist_slow_atr = (close - sma_slow) / atr  # in ATR units

    signal = pd.Series(0, index=df.index)
    # Long when all primary conditions + distance in ATR units < 10 ATRs
    signal[trend_ok & vol_ok & dist_ok & (dist_slow_atr < 10)] = 1

    return signal
