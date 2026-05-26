import pandas as pd
import numpy as np
from .base import SignalMethod, Signal
from .registry import register


@register
class SwingStructure(SignalMethod):
    id = "swing_structure"
    name = "Larry Williams Swing Structure"
    category = "structure"
    chart_position = "overlay"
    default_params = {}

    def compute(self, ohlcv: pd.DataFrame, params: dict | None = None) -> pd.DataFrame:
        df = ohlcv.copy()
        df = self._detect_short_term(df)
        df = self._detect_mid_term(df)
        df = self._detect_long_term(df)
        df = self._generate_signals(df)
        return df

    def _detect_short_term(self, df: pd.DataFrame) -> pd.DataFrame:
        highs = df["high"].values
        lows = df["low"].values
        n = len(df)

        sth = np.zeros(n, dtype=bool)
        stl = np.zeros(n, dtype=bool)

        for i in range(1, n - 1):
            if highs[i] > highs[i - 1] and highs[i] > highs[i + 1]:
                sth[i] = True
            if lows[i] < lows[i - 1] and lows[i] < lows[i + 1]:
                stl[i] = True

        df["sth"] = sth
        df["stl"] = stl
        df["sth_price"] = np.where(sth, highs, np.nan)
        df["stl_price"] = np.where(stl, lows, np.nan)
        return df

    def _detect_mid_term(self, df: pd.DataFrame) -> pd.DataFrame:
        n = len(df)
        mth = np.zeros(n, dtype=bool)
        mtl = np.zeros(n, dtype=bool)

        st_high_indices = df.index[df["sth"]].tolist()
        st_low_indices = df.index[df["stl"]].tolist()

        for idx, pos in enumerate(st_high_indices):
            if idx == 0 or idx == len(st_high_indices) - 1:
                continue
            prev_i = st_high_indices[idx - 1]
            next_i = st_high_indices[idx + 1]
            if df.at[pos, "sth_price"] > df.at[prev_i, "sth_price"] and \
               df.at[pos, "sth_price"] > df.at[next_i, "sth_price"]:
                mth[df.index.get_loc(pos)] = True

        for idx, pos in enumerate(st_low_indices):
            if idx == 0 or idx == len(st_low_indices) - 1:
                continue
            prev_i = st_low_indices[idx - 1]
            next_i = st_low_indices[idx + 1]
            if df.at[pos, "stl_price"] < df.at[prev_i, "stl_price"] and \
               df.at[pos, "stl_price"] < df.at[next_i, "stl_price"]:
                mtl[df.index.get_loc(pos)] = True

        df["mth"] = mth
        df["mtl"] = mtl
        df["mth_price"] = np.where(mth, df["high"].values, np.nan)
        df["mtl_price"] = np.where(mtl, df["low"].values, np.nan)
        return df

    def _detect_long_term(self, df: pd.DataFrame) -> pd.DataFrame:
        n = len(df)
        lth = np.zeros(n, dtype=bool)
        ltl = np.zeros(n, dtype=bool)

        mt_high_indices = df.index[df["mth"]].tolist()
        mt_low_indices = df.index[df["mtl"]].tolist()

        for idx, pos in enumerate(mt_high_indices):
            if idx == 0 or idx == len(mt_high_indices) - 1:
                continue
            prev_i = mt_high_indices[idx - 1]
            next_i = mt_high_indices[idx + 1]
            if df.at[pos, "mth_price"] > df.at[prev_i, "mth_price"] and \
               df.at[pos, "mth_price"] > df.at[next_i, "mth_price"]:
                lth[df.index.get_loc(pos)] = True

        for idx, pos in enumerate(mt_low_indices):
            if idx == 0 or idx == len(mt_low_indices) - 1:
                continue
            prev_i = mt_low_indices[idx - 1]
            next_i = mt_low_indices[idx + 1]
            if df.at[pos, "mtl_price"] < df.at[prev_i, "mtl_price"] and \
               df.at[pos, "mtl_price"] < df.at[next_i, "mtl_price"]:
                ltl[df.index.get_loc(pos)] = True

        df["lth"] = lth
        df["ltl"] = ltl
        df["lth_price"] = np.where(lth, df["high"].values, np.nan)
        df["ltl_price"] = np.where(ltl, df["low"].values, np.nan)
        return df

    def _generate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        n = len(df)
        buy_signal = np.zeros(n, dtype=bool)
        sell_signal = np.zeros(n, dtype=bool)

        last_mth_idx = None
        last_mtl_idx = None

        for i in range(n):
            iloc = df.index[i] if not isinstance(df.index, pd.RangeIndex) else i
            if df.at[iloc, "mth"]:
                last_mth_idx = i
                if last_mtl_idx is not None:
                    sell_signal[i] = True
                    last_mtl_idx = None
            if df.at[iloc, "mtl"]:
                last_mtl_idx = i
                if last_mth_idx is not None:
                    buy_signal[i] = True
                    last_mth_idx = None

        df["buy_signal"] = buy_signal
        df["sell_signal"] = sell_signal
        return df

    def signal(self, data: pd.DataFrame, params: dict | None = None) -> Signal:
        if data.empty:
            return Signal(value=0.0, label="Neutral")

        last = data.iloc[-1]
        if last.get("buy_signal", False):
            return Signal(value=1.0, label="Strong Buy", details={"trigger": "MTL confirmed"})
        if last.get("sell_signal", False):
            return Signal(value=-1.0, label="Strong Sell", details={"trigger": "MTH confirmed"})

        mt_lows = data[data["mtl"]]["mtl_price"].dropna()
        if len(mt_lows) >= 2:
            if mt_lows.iloc[-1] > mt_lows.iloc[-2]:
                return Signal(value=0.3, label="Bullish", details={"trend": "Higher MTLs"})
            else:
                return Signal(value=-0.3, label="Bearish", details={"trend": "Lower MTLs"})

        return Signal(value=0.0, label="Neutral")

    def get_swing_points(self, data: pd.DataFrame) -> list[dict]:
        points = []
        for _, row in data.iterrows():
            date = str(row.get("date", row.name))
            for level, col in [("STH", "sth"), ("STL", "stl"), ("MTH", "mth"),
                               ("MTL", "mtl"), ("LTH", "lth"), ("LTL", "ltl")]:
                if row.get(col, False):
                    price_col = col + "_price"
                    points.append({
                        "date": date,
                        "level": level,
                        "price": float(row[price_col]),
                    })
            if row.get("buy_signal", False):
                points.append({"date": date, "level": "BUY", "price": float(row["low"])})
            if row.get("sell_signal", False):
                points.append({"date": date, "level": "SELL", "price": float(row["high"])})
        return points
