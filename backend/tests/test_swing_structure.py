import pandas as pd
import numpy as np
import pytest
from app.signals.swing_structure import SwingStructure


def make_ohlcv(highs: list[float], lows: list[float]) -> pd.DataFrame:
    n = len(highs)
    return pd.DataFrame({
        "date": pd.date_range("2024-01-01", periods=n, freq="D"),
        "open": [(h + l) / 2 for h, l in zip(highs, lows)],
        "high": highs,
        "low": lows,
        "close": [(h + l) / 2 for h, l in zip(highs, lows)],
        "volume": [1000000] * n,
    })


class TestShortTermDetection:
    def test_short_term_high(self):
        highs = [10, 12, 15, 13, 11]
        lows = [8, 9, 12, 10, 9]
        df = make_ohlcv(highs, lows)

        swing = SwingStructure()
        result = swing.compute(df)

        assert result.iloc[2]["sth"] == True
        assert result.iloc[2]["sth_price"] == 15

    def test_short_term_low(self):
        highs = [15, 13, 11, 12, 14]
        lows = [12, 10, 8, 9, 11]
        df = make_ohlcv(highs, lows)

        swing = SwingStructure()
        result = swing.compute(df)

        assert result.iloc[2]["stl"] == True
        assert result.iloc[2]["stl_price"] == 8

    def test_no_false_short_term(self):
        highs = [10, 11, 12, 13, 14]
        lows = [8, 9, 10, 11, 12]
        df = make_ohlcv(highs, lows)

        swing = SwingStructure()
        result = swing.compute(df)

        assert not result["sth"].any()
        assert not result["stl"].any()


class TestMidTermDetection:
    def test_mid_term_high(self):
        # Create a pattern with 3 short-term highs where middle is highest
        # STH at index 2 (high=15), STH at index 6 (high=20), STH at index 10 (high=17)
        highs = [10, 12, 15, 13, 11, 14, 20, 18, 15, 14, 17, 15, 13]
        lows =  [8,  10, 12, 11, 9,  12, 17, 15, 13, 12, 14, 13, 11]
        df = make_ohlcv(highs, lows)

        swing = SwingStructure()
        result = swing.compute(df)

        sth_indices = result.index[result["sth"]].tolist()
        mth_indices = result.index[result["mth"]].tolist()

        assert len(sth_indices) >= 3
        assert len(mth_indices) >= 1

    def test_mid_term_low(self):
        # Create pattern with 3 short-term lows where middle is lowest
        # STL at index 2, STL at index 6, STL at index 10
        highs = [15, 13, 11, 12, 14, 12, 9,  10, 12, 14, 11, 13, 15]
        lows =  [12, 10, 8,  9,  11, 9,  6,  8,  10, 11, 9,  10, 12]
        df = make_ohlcv(highs, lows)

        swing = SwingStructure()
        result = swing.compute(df)

        stl_indices = result.index[result["stl"]].tolist()
        mtl_indices = result.index[result["mtl"]].tolist()

        assert len(stl_indices) >= 3
        assert len(mtl_indices) >= 1


class TestSignalGeneration:
    def test_buy_signal_after_mtl(self):
        # Build a sequence: MTH forms, then MTL forms -> BUY
        highs = [10, 12, 15, 13, 11, 14, 20, 18, 15, 14, 17, 15, 13,
                 15, 13, 11, 12, 14, 12, 9, 10, 12, 14, 11, 13, 15]
        lows =  [8,  10, 12, 11, 9,  12, 17, 15, 13, 12, 14, 13, 11,
                 12, 10, 8,  9,  11, 9,  6,  8,  10, 11, 9,  10, 12]
        df = make_ohlcv(highs, lows)

        swing = SwingStructure()
        result = swing.compute(df)

        # Should have at least some swing points detected
        assert result["sth"].any() or result["stl"].any()

    def test_signal_value(self):
        swing = SwingStructure()
        highs = [10, 12, 15, 13, 11, 14, 20, 18, 15]
        lows = [8, 10, 12, 11, 9, 12, 17, 15, 13]
        df = make_ohlcv(highs, lows)

        result = swing.compute(df)
        sig = swing.signal(result)

        assert -1.0 <= sig.value <= 1.0
        assert sig.label in ["Strong Buy", "Strong Sell", "Bullish", "Bearish", "Neutral"]


class TestSwingPoints:
    def test_get_swing_points_returns_list(self):
        swing = SwingStructure()
        highs = [10, 12, 15, 13, 11]
        lows = [8, 9, 12, 10, 9]
        df = make_ohlcv(highs, lows)

        result = swing.compute(df)
        points = swing.get_swing_points(result)

        assert isinstance(points, list)
        for p in points:
            assert "date" in p
            assert "level" in p
            assert "price" in p
            assert p["level"] in ["STH", "STL", "MTH", "MTL", "LTH", "LTL", "BUY", "SELL"]
