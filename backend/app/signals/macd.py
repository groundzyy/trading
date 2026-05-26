import pandas as pd
import numpy as np
from .base import SignalMethod, Signal
from .registry import register


@register
class MACD(SignalMethod):
    id = "macd"
    name = "MACD"
    category = "momentum"
    chart_position = "sub_panel"
    default_params = {"fast": 12, "slow": 26, "signal": 9}

    def compute(self, ohlcv: pd.DataFrame, params: dict | None = None) -> pd.DataFrame:
        p = self.get_params(params)
        df = ohlcv.copy()
        close = df["close"]

        ema_fast = close.ewm(span=p["fast"], adjust=False).mean()
        ema_slow = close.ewm(span=p["slow"], adjust=False).mean()

        df["macd_dif"] = ema_fast - ema_slow
        df["macd_dea"] = df["macd_dif"].ewm(span=p["signal"], adjust=False).mean()
        df["macd_hist"] = (df["macd_dif"] - df["macd_dea"]) * 2
        return df

    def signal(self, data: pd.DataFrame, params: dict | None = None) -> Signal:
        if len(data) < 2:
            return Signal(value=0.0, label="Neutral")

        curr = data.iloc[-1]
        prev = data.iloc[-2]

        dif = curr["macd_dif"]
        dea = curr["macd_dea"]
        hist = curr["macd_hist"]
        prev_hist = prev["macd_hist"]

        if dif > dea and prev["macd_dif"] <= prev["macd_dea"]:
            return Signal(value=0.8, label="Bullish Crossover")
        if dif < dea and prev["macd_dif"] >= prev["macd_dea"]:
            return Signal(value=-0.8, label="Bearish Crossover")

        if hist > 0 and hist > prev_hist:
            return Signal(value=0.5, label="Bullish Momentum")
        if hist < 0 and hist < prev_hist:
            return Signal(value=-0.5, label="Bearish Momentum")
        if hist > 0:
            return Signal(value=0.2, label="Bullish")
        if hist < 0:
            return Signal(value=-0.2, label="Bearish")

        return Signal(value=0.0, label="Neutral")
