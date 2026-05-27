from sqlalchemy import Column, Integer, String, Float, Date, DateTime, Text, JSON, Index
from sqlalchemy.sql import func
from ..database import Base


class SentimentAnalysis(Base):
    __tablename__ = "sentiment_analyses"

    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String, index=True, nullable=False)
    date = Column(Date, nullable=False)
    signal_value = Column(Float)
    label = Column(String)
    confidence = Column(Float)
    reasoning = Column(Text)
    factors = Column(JSON)
    source_data = Column(JSON)
    model_used = Column(String)
    input_tokens = Column(Integer, default=0)
    output_tokens = Column(Integer, default=0)
    cost_usd = Column(Float, default=0.0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        Index("ix_sentiment_symbol_date", "symbol", "date", unique=True),
    )
