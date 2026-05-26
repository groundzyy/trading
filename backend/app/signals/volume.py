import pandas as pd
import numpy as np
from .base import SignalMethod, Signal
from .registry import register


@register
class VolumeSignal(SignalMethod):
    id = "volume"
    name = "Volume"
    category = "volume"
    chart_position = "sub_panel"
    default_params = {"avg_period": 20, "spike_multiplier": 2.0}

    def compute(self, ohlcv: pd.DataFrame, params: dict | None = None) -> pd.DataFrame:
        p = self.get_params(params)
        df = ohlcv.copy()
        df["vol_avg"] = df["volume"].rolling(window=p["avg_period"]).mean()
        df["vol_ratio"] = df["volume"] / df["vol_avg"].replace(0, np.inf)
        return df

    def signal(self, data: pd.DataFrame, params: dict | None = None) -> Signal:
        p = self.get_params(params)
        if data.empty or data["vol_ratio"].isna().all():
            return Signal(value=0.0, label="Neutral")

        last = data.iloc[-1]
        vol_ratio = last["vol_ratio"]
        price_change = last["close"] - last["open"]

        is_spike = vol_ratio >= p["spike_multiplier"]

        if is_spike and price_change > 0:
            value = min(vol_ratio / 4.0, 1.0)
            return Signal(value=round(value, 2), label="Bullish Volume Spike",
                          details={"vol_ratio": round(vol_ratio, 2)})
        if is_spike and price_change < 0:
            value = max(-vol_ratio / 4.0, -1.0)
            return Signal(value=round(value, 2), label="Bearish Volume Spike",
                          details={"vol_ratio": round(vol_ratio, 2)})
        if vol_ratio > 1.0 and price_change > 0:
            return Signal(value=0.2, label="Above Average Volume (Bullish)")
        if vol_ratio > 1.0 and price_change < 0:
            return Signal(value=-0.2, label="Above Average Volume (Bearish)")

        return Signal(value=0.0, label="Normal Volume")
