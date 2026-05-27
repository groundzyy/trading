import pandas as pd
from .base import SignalMethod, Signal
from .registry import register


@register
class SentimentLLM(SignalMethod):
    id = "sentiment"
    name = "LLM Sentiment"
    category = "sentiment"
    chart_position = "none"
    default_params = {"mode": "batch"}

    def compute(self, ohlcv: pd.DataFrame, params: dict | None = None) -> pd.DataFrame:
        return ohlcv

    def signal(self, data: pd.DataFrame, params: dict | None = None) -> Signal:
        if params and "_cached_signal" in params:
            return params["_cached_signal"]
        return Signal(value=0.0, label="No Analysis", details={"available": False})
