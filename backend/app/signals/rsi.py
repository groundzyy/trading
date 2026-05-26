import pandas as pd
import numpy as np
from .base import SignalMethod, Signal
from .registry import register


@register
class RSI(SignalMethod):
    id = "rsi"
    name = "RSI"
    category = "momentum"
    chart_position = "sub_panel"
    default_params = {"period": 14}

    def compute(self, ohlcv: pd.DataFrame, params: dict | None = None) -> pd.DataFrame:
        p = self.get_params(params)
        df = ohlcv.copy()
        delta = df["close"].diff()

        gain = delta.clip(lower=0)
        loss = (-delta).clip(lower=0)

        avg_gain = gain.ewm(alpha=1.0 / p["period"], min_periods=p["period"], adjust=False).mean()
        avg_loss = loss.ewm(alpha=1.0 / p["period"], min_periods=p["period"], adjust=False).mean()

        rs = avg_gain / avg_loss.replace(0, np.nan)
        df["rsi"] = np.where(avg_loss == 0, 100.0, 100 - (100 / (1 + rs)))
        return df

    def signal(self, data: pd.DataFrame, params: dict | None = None) -> Signal:
        if data.empty or data["rsi"].isna().all():
            return Signal(value=0.0, label="Neutral")

        rsi = data.iloc[-1]["rsi"]

        if rsi < 20:
            return Signal(value=0.9, label="Strongly Oversold", details={"rsi": rsi})
        if rsi < 30:
            return Signal(value=0.6, label="Oversold", details={"rsi": rsi})
        if rsi < 40:
            return Signal(value=0.2, label="Mildly Oversold", details={"rsi": rsi})
        if rsi > 80:
            return Signal(value=-0.9, label="Strongly Overbought", details={"rsi": rsi})
        if rsi > 70:
            return Signal(value=-0.6, label="Overbought", details={"rsi": rsi})
        if rsi > 60:
            return Signal(value=-0.2, label="Mildly Overbought", details={"rsi": rsi})

        return Signal(value=0.0, label="Neutral", details={"rsi": rsi})
