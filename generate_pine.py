"""
generate_pine.py - Translate strategy.py into TradingView Pine Script.

Reads the CONFIG dict and generate_signals() source code from strategy.py,
detects common indicator patterns, and produces equivalent Pine Script v5.

Usage:
    python generate_pine.py                  # prints to stdout
    python generate_pine.py -o results/best_strategy.pine  # writes to file
"""

import ast
import importlib
import inspect
import re
import sys
from pathlib import Path


def detect_patterns(source: str, config: dict) -> list[dict]:
    """
    Detect indicator patterns from generate_signals() source code.
    Returns a list of pattern dicts with type and parameters.
    """
    patterns = []

    # SMA detection (only on close/price, not on ATR/TR intermediate calcs)
    sma_matches = re.findall(r'\.rolling\(CONFIG\["(\w+)"\]\)\.mean\(\)', source)
    if sma_matches:
        for key in sma_matches:
            if key in config and "atr" not in key and "tr" != key:
                patterns.append({"type": "sma", "param_key": key, "period": config[key]})

    # EMA detection (exclude ATR-related keys)
    ema_matches = re.findall(r'\.ewm\(span=CONFIG\["(\w+)"\]', source)
    if ema_matches:
        for key in ema_matches:
            if key in config and "atr" not in key:
                patterns.append({"type": "ema", "param_key": key, "period": config[key]})

    # RSI detection
    if "rsi" in source.lower() or any("rsi" in k for k in config):
        rsi_period = config.get("rsi_period", config.get("rsi_len", 14))
        patterns.append({"type": "rsi", "period": rsi_period})
        # Detect RSI thresholds
        for key in config:
            if "oversold" in key or "rsi_low" in key or "rsi_buy" in key:
                patterns.append({"type": "rsi_threshold_low", "value": config[key]})
            if "overbought" in key or "rsi_high" in key or "rsi_sell" in key:
                patterns.append({"type": "rsi_threshold_high", "value": config[key]})

    # ATR detection
    if "atr" in source.lower() or any("atr" in k for k in config):
        atr_period = config.get("atr_period", config.get("atr_len", 20))
        patterns.append({"type": "atr", "period": atr_period})

    # ATR multiplier/threshold detection (handles various orderings)
    atr_filter_patterns = [
        r'atr_pct\s*<\s*([\d.]+)\s*\*\s*atr_pct_avg',    # atr_pct < 2.0 * atr_pct_avg
        r'atr_pct\s*<\s*atr_pct_avg\s*\*\s*([\d.]+)',      # atr_pct < atr_pct_avg * 2.0
        r'atr_pct\s*<\s*\w+\s*\*\s*([\d.]+)',              # atr_pct < atr_median * 1.5
        r'atr_pct\s*<\s*([\d.]+)\s*\*\s*\w+',              # atr_pct < 1.5 * atr_median
    ]
    atr_mult_found = False
    for pat in atr_filter_patterns:
        m = re.findall(pat, source)
        if m:
            patterns.append({"type": "atr_vol_filter", "multiplier": float(m[0])})
            atr_mult_found = True
            break
    if not atr_mult_found:
        # Check for CONFIG-based multiplier
        m = re.findall(r'atr_pct\s*<\s*CONFIG\["(\w+)"\]', source)
        if m:
            patterns.append({"type": "atr_vol_filter", "multiplier": config.get(m[0], 2.0)})

    # MACD detection
    if "macd" in source.lower() or any("macd" in k for k in config):
        fast = config.get("macd_fast", 12)
        slow = config.get("macd_slow", 26)
        signal = config.get("macd_signal", 9)
        patterns.append({"type": "macd", "fast": fast, "slow": slow, "signal": signal})

    # Bollinger Bands detection
    if "bollinger" in source.lower() or "bband" in source.lower() or any("bb_" in k or "boll" in k for k in config):
        bb_period = config.get("bb_period", config.get("boll_period", 20))
        bb_std = config.get("bb_std", config.get("boll_std", 2.0))
        patterns.append({"type": "bollinger", "period": bb_period, "std": bb_std})

    # ADX detection
    if "adx" in source.lower() or any("adx" in k for k in config):
        adx_period = config.get("adx_period", config.get("adx_len", 14))
        adx_thresh = config.get("adx_threshold", config.get("adx_min", 25))
        patterns.append({"type": "adx", "period": adx_period, "threshold": adx_thresh})

    # Volume filter detection (must reference df["Volume"] explicitly)
    if re.search(r'df\["Volume"\]', source) or any("vol_period" in k or "volume_period" in k for k in config):
        vol_period = config.get("vol_period", config.get("volume_period", 20))
        patterns.append({"type": "volume_filter", "period": vol_period})

    # Donchian channel detection
    if "donchian" in source.lower() or any("donch" in k for k in config):
        dc_period = config.get("donchian_period", config.get("dc_period", 20))
        patterns.append({"type": "donchian", "period": dc_period})

    # Stochastic detection
    if "stoch" in source.lower() or any("stoch" in k for k in config):
        k_period = config.get("stoch_k", 14)
        d_period = config.get("stoch_d", 3)
        patterns.append({"type": "stochastic", "k": k_period, "d": d_period})

    return patterns


def detect_signal_logic(source: str) -> list[str]:
    """
    Extract the signal conditions from generate_signals() source.
    Returns a list of condition description strings.
    """
    conditions = []

    # SMA crossover: sma_fast > sma_slow
    if re.search(r'sma_fast\s*>\s*sma_slow', source):
        conditions.append("sma_crossover_bullish")
    if re.search(r'sma_fast\s*<\s*sma_slow', source):
        conditions.append("sma_crossover_bearish")

    # EMA crossover
    if re.search(r'ema_fast\s*>\s*ema_slow', source):
        conditions.append("ema_crossover_bullish")

    # RSI conditions
    if re.search(r'rsi\s*[<>]', source):
        conditions.append("rsi_threshold")

    # ATR volatility filter
    if re.search(r'atr_pct\s*<', source):
        conditions.append("atr_vol_filter")

    # MACD crossover
    if re.search(r'macd.*signal|signal.*macd', source, re.IGNORECASE):
        conditions.append("macd_signal_cross")

    # Price above/below MA
    if re.search(r'close\s*>\s*sma', source):
        conditions.append("price_above_sma")

    # ADX filter
    if re.search(r'adx\s*>', source):
        conditions.append("adx_trend_filter")

    # Volume filter
    if re.search(r'volume\s*>', source, re.IGNORECASE):
        conditions.append("volume_above_avg")

    return conditions


def generate_pine_script(strategy_path: str = "strategy.py") -> str:
    """
    Read strategy.py and generate equivalent TradingView Pine Script v5.
    """
    # Import strategy to get CONFIG
    sys.path.insert(0, str(Path(strategy_path).parent))
    if "strategy" in sys.modules:
        strategy_module = importlib.reload(sys.modules["strategy"])
    else:
        strategy_module = importlib.import_module("strategy")

    config = getattr(strategy_module, "CONFIG", {})

    # Read source of generate_signals
    source = inspect.getsource(strategy_module.generate_signals)

    # Detect patterns and logic
    patterns = detect_patterns(source, config)
    conditions = detect_signal_logic(source)
    pattern_types = {p["type"] for p in patterns}

    # Build Pine Script
    lines = []
    lines.append('//@version=5')
    lines.append('strategy("Autoresearch Strategy", overlay=true, default_qty_type=strategy.percent_of_equity, default_qty_value=100)')
    lines.append('')

    # Input parameters from CONFIG
    lines.append('// ── Parameters ──')
    input_vars = {}
    for key, value in config.items():
        var_name = key
        if isinstance(value, int):
            lines.append(f'{var_name} = input.int({value}, "{key}")')
        elif isinstance(value, float):
            lines.append(f'{var_name} = input.float({value}, "{key}")')
        input_vars[key] = var_name
    lines.append('')

    # Indicators
    lines.append('// ── Indicators ──')

    # SMA
    sma_patterns = [p for p in patterns if p["type"] == "sma"]
    sma_vars = {}
    for p in sma_patterns:
        var_name = f'sma_{p["param_key"]}'
        lines.append(f'{var_name} = ta.sma(close, {p["param_key"]})')
        sma_vars[p["param_key"]] = var_name

    # EMA
    ema_patterns = [p for p in patterns if p["type"] == "ema"]
    ema_vars = {}
    for p in ema_patterns:
        var_name = f'ema_{p["param_key"]}'
        lines.append(f'{var_name} = ta.ema(close, {p["param_key"]})')
        ema_vars[p["param_key"]] = var_name

    # RSI
    if "rsi" in pattern_types:
        rsi_p = next(p for p in patterns if p["type"] == "rsi")
        rsi_input = input_vars.get("rsi_period", input_vars.get("rsi_len", str(rsi_p["period"])))
        lines.append(f'rsi_val = ta.rsi(close, {rsi_input})')

    # ATR
    if "atr" in pattern_types:
        atr_p = next(p for p in patterns if p["type"] == "atr")
        atr_input = input_vars.get("atr_period", input_vars.get("atr_len", str(atr_p["period"])))
        lines.append(f'atr_val = ta.atr({atr_input})')
        lines.append(f'atr_pct = atr_val / close')
        lines.append(f'atr_pct_avg = ta.sma(atr_pct, 100)')

    # MACD
    if "macd" in pattern_types:
        macd_p = next(p for p in patterns if p["type"] == "macd")
        fast_input = input_vars.get("macd_fast", str(macd_p["fast"]))
        slow_input = input_vars.get("macd_slow", str(macd_p["slow"]))
        signal_input = input_vars.get("macd_signal", str(macd_p["signal"]))
        lines.append(f'[macd_line, signal_line, _] = ta.macd(close, {fast_input}, {slow_input}, {signal_input})')

    # Bollinger Bands
    if "bollinger" in pattern_types:
        bb_p = next(p for p in patterns if p["type"] == "bollinger")
        bb_period_input = input_vars.get("bb_period", input_vars.get("boll_period", str(bb_p["period"])))
        bb_std_input = input_vars.get("bb_std", input_vars.get("boll_std", str(bb_p["std"])))
        lines.append(f'[bb_mid, bb_upper, bb_lower] = ta.bb(close, {bb_period_input}, {bb_std_input})')

    # ADX
    if "adx" in pattern_types:
        adx_p = next(p for p in patterns if p["type"] == "adx")
        adx_input = input_vars.get("adx_period", input_vars.get("adx_len", str(adx_p["period"])))
        lines.append(f'[_, _, adx_val] = ta.dmi({adx_input}, {adx_input})')

    # Volume filter
    if "volume_filter" in pattern_types:
        vol_p = next(p for p in patterns if p["type"] == "volume_filter")
        vol_input = input_vars.get("vol_period", input_vars.get("volume_period", str(vol_p["period"])))
        lines.append(f'vol_avg = ta.sma(volume, {vol_input})')

    # Donchian
    if "donchian" in pattern_types:
        dc_p = next(p for p in patterns if p["type"] == "donchian")
        dc_input = input_vars.get("donchian_period", input_vars.get("dc_period", str(dc_p["period"])))
        lines.append(f'dc_upper = ta.highest(high, {dc_input})')
        lines.append(f'dc_lower = ta.lowest(low, {dc_input})')
        lines.append(f'dc_mid = (dc_upper + dc_lower) / 2')

    # Stochastic
    if "stochastic" in pattern_types:
        stoch_p = next(p for p in patterns if p["type"] == "stochastic")
        k_input = input_vars.get("stoch_k", str(stoch_p["k"]))
        d_input = input_vars.get("stoch_d", str(stoch_p["d"]))
        lines.append(f'stoch_k = ta.stoch(close, high, low, {k_input})')
        lines.append(f'stoch_d = ta.sma(stoch_k, {d_input})')

    lines.append('')

    # Signal conditions
    lines.append('// ── Entry/Exit Conditions ──')

    entry_parts = []
    exit_parts = []

    if "sma_crossover_bullish" in conditions:
        fast_keys = [k for k in config if "fast" in k and "sma" in k]
        slow_keys = [k for k in config if "slow" in k and "sma" in k]
        if fast_keys and slow_keys:
            fast_var = sma_vars.get(fast_keys[0], "sma_fast")
            slow_var = sma_vars.get(slow_keys[0], "sma_slow")
            entry_parts.append(f'{fast_var} > {slow_var}')
            exit_parts.append(f'{fast_var} < {slow_var}')

    if "ema_crossover_bullish" in conditions:
        fast_keys = [k for k in config if "fast" in k and "ema" in k]
        slow_keys = [k for k in config if "slow" in k and "ema" in k]
        if fast_keys and slow_keys:
            fast_var = ema_vars.get(fast_keys[0], "ema_fast")
            slow_var = ema_vars.get(slow_keys[0], "ema_slow")
            entry_parts.append(f'{fast_var} > {slow_var}')
            exit_parts.append(f'{fast_var} < {slow_var}')

    if "rsi_threshold" in conditions:
        low_thresh = None
        high_thresh = None
        for p in patterns:
            if p["type"] == "rsi_threshold_low":
                low_thresh = p["value"]
            if p["type"] == "rsi_threshold_high":
                high_thresh = p["value"]
        if low_thresh:
            entry_parts.append(f'rsi_val < {low_thresh}')
        if high_thresh:
            entry_parts.append(f'rsi_val < {high_thresh}')
            exit_parts.append(f'rsi_val > {high_thresh}')

    if "atr_vol_filter" in conditions:
        atr_vf = next((p for p in patterns if p["type"] == "atr_vol_filter"), None)
        if atr_vf:
            mult = atr_vf["multiplier"]
            entry_parts.append(f'atr_pct < {mult} * atr_pct_avg')

    if "macd_signal_cross" in conditions:
        entry_parts.append('macd_line > signal_line')
        exit_parts.append('macd_line < signal_line')

    if "price_above_sma" in conditions and not entry_parts:
        slow_keys = [k for k in config if "slow" in k]
        if slow_keys:
            slow_var = sma_vars.get(slow_keys[0], "sma_slow")
            entry_parts.append(f'close > {slow_var}')
            exit_parts.append(f'close < {slow_var}')

    if "adx_trend_filter" in conditions:
        adx_p = next((p for p in patterns if p["type"] == "adx"), None)
        if adx_p:
            entry_parts.append(f'adx_val > {adx_p["threshold"]}')

    if "volume_above_avg" in conditions:
        entry_parts.append('volume > vol_avg')

    # Build condition strings
    if entry_parts:
        entry_condition = " and ".join(entry_parts)
    else:
        entry_condition = "true  // Could not auto-detect entry logic - check strategy.py"

    if exit_parts:
        exit_condition = " or ".join(exit_parts)
    else:
        exit_condition = f"not ({entry_condition})"

    lines.append(f'long_entry = {entry_condition}')
    lines.append(f'long_exit = {exit_condition}')
    lines.append('')

    # Strategy execution
    lines.append('// ── Strategy Execution ──')
    lines.append('if long_entry')
    lines.append('    strategy.entry("Long", strategy.long)')
    lines.append('if long_exit')
    lines.append('    strategy.close("Long")')
    lines.append('')

    # Plot indicators
    lines.append('// ── Plots ──')
    for key, var in sma_vars.items():
        color = "color.blue" if "fast" in key else "color.orange"
        lines.append(f'plot({var}, "{key}", {color})')
    for key, var in ema_vars.items():
        color = "color.blue" if "fast" in key else "color.orange"
        lines.append(f'plot({var}, "{key}", {color})')
    if "bollinger" in pattern_types:
        lines.append('plot(bb_upper, "BB Upper", color.gray)')
        lines.append('plot(bb_lower, "BB Lower", color.gray)')
        lines.append('plot(bb_mid, "BB Mid", color.gray, style=plot.style_dashed)')

    # Background color for signal
    lines.append('')
    lines.append('bgcolor(long_entry ? color.new(color.green, 90) : na)')

    return "\n".join(lines)


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Generate TradingView Pine Script from strategy.py")
    parser.add_argument("-o", "--output", help="Output file path (default: stdout)")
    args = parser.parse_args()

    pine = generate_pine_script()

    if args.output:
        Path(args.output).write_text(pine)
        print(f"Pine Script written to {args.output}")
    else:
        print(pine)
