import pandas as pd
import numpy as np
from .base import SignalMethod, Signal
from .registry import register


@register
class KDJ(SignalMethod):
    id = "kdj"
    name = "KDJ"
    category = "momentum"
    chart_position = "sub_panel"
    default_params = {"period": 9, "k_smooth": 3, "d_smooth": 3}

    def compute(self, ohlcv: pd.DataFrame, params: dict | None = None) -> pd.DataFrame:
        p = self.get_params(params)
        df = ohlcv.copy()
        period = p["period"]

        low_min = df["low"].rolling(window=period).min()
        high_max = df["high"].rolling(window=period).max()

        rsv = (df["close"] - low_min) / (high_max - low_min).replace(0, np.inf) * 100

        df["kdj_k"] = rsv.ewm(span=p["k_smooth"], adjust=False).mean()
        df["kdj_d"] = df["kdj_k"].ewm(span=p["d_smooth"], adjust=False).mean()
        df["kdj_j"] = 3 * df["kdj_k"] - 2 * df["kdj_d"]
        return df

    def signal(self, data: pd.DataFrame, params: dict | None = None) -> Signal:
        if len(data) < 2:
            return Signal(value=0.0, label="Neutral")

        curr = data.iloc[-1]
        prev = data.iloc[-2]

        k, d, j = curr["kdj_k"], curr["kdj_d"], curr["kdj_j"]

        if k > d and prev["kdj_k"] <= prev["kdj_d"] and k < 30:
            return Signal(value=0.8, label="Golden Cross (Oversold)")
        if k > d and prev["kdj_k"] <= prev["kdj_d"]:
            return Signal(value=0.5, label="Golden Cross")
        if k < d and prev["kdj_k"] >= prev["kdj_d"] and k > 70:
            return Signal(value=-0.8, label="Death Cross (Overbought)")
        if k < d and prev["kdj_k"] >= prev["kdj_d"]:
            return Signal(value=-0.5, label="Death Cross")

        if j < 0:
            return Signal(value=0.6, label="J Oversold")
        if j > 100:
            return Signal(value=-0.6, label="J Overbought")

        return Signal(value=0.0, label="Neutral", details={"k": round(k, 2), "d": round(d, 2), "j": round(j, 2)})
