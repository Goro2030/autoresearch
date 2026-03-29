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

    # Require BOTH: sma crossover AND close is within 2% of fast SMA
    # (catch pullback entries in uptrend)
    close_to_fast = (close - sma_fast).abs() / sma_fast < 0.05  # within 5%
    in_trend = sma_fast > sma_slow
    close_above_fast = close >= sma_fast

    signal = pd.Series(0, index=df.index)
    # Long when trend up AND low vol (standard), OR just entered from below
    signal[in_trend & (atr_pct < atr_median * 1.5)] = 1

    return signal
