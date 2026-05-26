import pandas as pd
from ..signals.registry import get_method, SIGNAL_REGISTRY
from ..signals.base import Signal

# ensure all signal modules are imported so they register
from ..signals import swing_structure, macd, rsi, ma, volume, kdj  # noqa: F401


def compute_swing_structure(ohlcv: pd.DataFrame) -> tuple[pd.DataFrame, list[dict]]:
    method = get_method("swing_structure")
    result = method.compute(ohlcv)
    points = method.get_swing_points(result)
    return result, points


def compute_indicator(indicator_id: str, ohlcv: pd.DataFrame,
                      params: dict | None = None) -> tuple[pd.DataFrame, Signal]:
    method = get_method(indicator_id)
    result = method.compute(ohlcv, params)
    sig = method.signal(result, params)
    return result, sig


def compute_all_indicators(ohlcv: pd.DataFrame,
                           methods: list[str] | None = None,
                           method_params: dict | None = None) -> dict[str, Signal]:
    if methods is None:
        methods = [m for m in SIGNAL_REGISTRY if m != "swing_structure"]
    if method_params is None:
        method_params = {}

    signals = {}
    for method_id in methods:
        if method_id not in SIGNAL_REGISTRY:
            continue
        params = method_params.get(method_id)
        _, sig = compute_indicator(method_id, ohlcv, params)
        signals[method_id] = sig

    return signals


def get_indicator_data(indicator_id: str, ohlcv: pd.DataFrame,
                       params: dict | None = None) -> list[dict]:
    method = get_method(indicator_id)
    result = method.compute(ohlcv, params)

    columns_to_include = []
    for col in result.columns:
        if col.startswith(indicator_id) or col.startswith(method.id):
            columns_to_include.append(col)
        elif indicator_id == "ma" and col.startswith("ma"):
            columns_to_include.append(col)
        elif indicator_id == "kdj" and col.startswith("kdj_"):
            columns_to_include.append(col)
        elif indicator_id == "macd" and col.startswith("macd_"):
            columns_to_include.append(col)
        elif indicator_id == "volume" and col.startswith("vol_"):
            columns_to_include.append(col)

    data = []
    for _, row in result.iterrows():
        entry = {"date": str(row.get("date", row.name))}
        for col in columns_to_include:
            val = row[col]
            entry[col] = None if pd.isna(val) else round(float(val), 4)
        data.append(entry)
    return data
