from sqlalchemy import Column, Integer, String, ForeignKey, JSON, Float, Boolean, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from ..database import Base


class WatchlistItem(Base):
    __tablename__ = "watchlist_items"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    symbol = Column(String, index=True, nullable=False)
    added_at = Column(DateTime(timezone=True), server_default=func.now())

    selected_methods = Column(JSON, default=lambda: ["macd", "rsi", "ma", "volume"])
    method_weights = Column(JSON, default=lambda: {"macd": 0.3, "rsi": 0.25, "ma": 0.25, "volume": 0.2})
    method_params = Column(JSON, default=dict)

    notify_enabled = Column(Boolean, default=True)
    notify_buy = Column(Boolean, default=True)
    notify_sell = Column(Boolean, default=True)

    user = relationship("User", back_populates="watchlist_items")
