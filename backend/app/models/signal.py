from sqlalchemy import Column, Integer, String, Float, Date, DateTime, JSON, Index
from sqlalchemy.sql import func
from ..database import Base


class SwingPoint(Base):
    __tablename__ = "swing_points"

    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String, index=True, nullable=False)
    date = Column(Date, nullable=False)
    level = Column(String, nullable=False)  # "STH", "STL", "MTH", "MTL", "LTH", "LTL"
    price = Column(Float, nullable=False)

    __table_args__ = (
        Index("ix_swing_symbol_date_level", "symbol", "date", "level", unique=True),
    )


class SignalResult(Base):
    __tablename__ = "signal_results"

    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String, index=True, nullable=False)
    date = Column(Date, nullable=False)
    signal_type = Column(String, nullable=False)  # "BUY", "SELL"
    primary_trigger = Column(String, nullable=False)  # e.g. "swing_structure"
    trigger_price = Column(Float)
    indicator_scores = Column(JSON, default=dict)
    composite_score = Column(Float)
    swing_state = Column(String, default="")  # current swing structure state
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        Index("ix_signal_symbol_date", "symbol", "date"),
    )


class IndicatorCache(Base):
    __tablename__ = "indicator_cache"

    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String, index=True, nullable=False)
    date = Column(Date, nullable=False)
    indicator = Column(String, nullable=False)  # "macd", "rsi", etc.
    values = Column(JSON, nullable=False)
    signal_value = Column(Float)  # [-1.0, +1.0]

    __table_args__ = (
        Index("ix_indicator_cache_unique", "symbol", "date", "indicator", unique=True),
    )
