from abc import ABC, abstractmethod
from dataclasses import dataclass
import pandas as pd


@dataclass
class Signal:
    value: float  # [-1.0, +1.0]
    label: str  # "Strong Buy", "Buy", "Neutral", "Sell", "Strong Sell"
    details: dict | None = None


class SignalMethod(ABC):
    id: str
    name: str
    category: str  # "trend", "momentum", "volume", "volatility", "structure"
    chart_position: str  # "overlay" or "sub_panel"
    default_params: dict

    @abstractmethod
    def compute(self, ohlcv: pd.DataFrame, params: dict | None = None) -> pd.DataFrame:
        ...

    @abstractmethod
    def signal(self, data: pd.DataFrame, params: dict | None = None) -> Signal:
        ...

    def get_params(self, overrides: dict | None = None) -> dict:
        params = dict(self.default_params)
        if overrides:
            params.update(overrides)
        return params
