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
}


def generate_signals(df: pd.DataFrame) -> pd.Series:
    """
    Given a DataFrame with columns [Open, High, Low, Close, Volume],
    return a Series of signals: 1 = go long, 0 = flat/exit.
    Index must match the input DataFrame.
    """
    close = df["Close"]
    sma_fast = close.rolling(CONFIG["sma_fast"]).mean()
    sma_slow = close.rolling(CONFIG["sma_slow"]).mean()

    signal = pd.Series(0, index=df.index)
    signal[sma_fast > sma_slow] = 1

    return signal
