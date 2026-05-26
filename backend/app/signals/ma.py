import pandas as pd
import numpy as np
from .base import SignalMethod, Signal
from .registry import register


@register
class MovingAverage(SignalMethod):
    id = "ma"
    name = "Moving Average"
    category = "trend"
    chart_position = "overlay"
    default_params = {"periods": [5, 10, 20, 60]}

    def compute(self, ohlcv: pd.DataFrame, params: dict | None = None) -> pd.DataFrame:
        p = self.get_params(params)
        df = ohlcv.copy()

        for period in p["periods"]:
            df[f"ma{period}"] = df["close"].rolling(window=period).mean()

        return df

    def signal(self, data: pd.DataFrame, params: dict | None = None) -> Signal:
        p = self.get_params(params)
        if data.empty:
            return Signal(value=0.0, label="Neutral")

        last = data.iloc[-1]
        close = last["close"]
        periods = sorted(p["periods"])

        score = 0.0
        count = 0
        for period in periods:
            col = f"ma{period}"
            if col in last and not pd.isna(last[col]):
                ma_val = last[col]
                if close > ma_val:
                    score += 1.0
                else:
                    score -= 1.0
                count += 1

        if count == 0:
            return Signal(value=0.0, label="Neutral")

        normalized = score / count

        ma_values = {}
        for period in periods:
            col = f"ma{period}"
            if col in last and not pd.isna(last[col]):
                ma_values[col] = last[col]

        bullish_aligned = True
        bearish_aligned = True
        vals = list(ma_values.values())
        for i in range(len(vals) - 1):
            if vals[i] < vals[i + 1]:
                bullish_aligned = False
            if vals[i] > vals[i + 1]:
                bearish_aligned = False

        if bullish_aligned and len(vals) >= 3:
            normalized = min(normalized + 0.3, 1.0)
        elif bearish_aligned and len(vals) >= 3:
            normalized = max(normalized - 0.3, -1.0)

        if normalized > 0.5:
            label = "Bullish"
        elif normalized < -0.5:
            label = "Bearish"
        else:
            label = "Neutral"

        return Signal(value=round(normalized, 2), label=label, details=ma_values)
