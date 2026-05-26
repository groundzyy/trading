from sqlalchemy import Column, Integer, String, Boolean, DateTime, Float, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from ..database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    username = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    notify_buy = Column(Boolean, default=True)
    notify_sell = Column(Boolean, default=True)
    notify_threshold = Column(Float, default=0.3)
    default_weights = Column(JSON, default=dict)

    watchlist_items = relationship("WatchlistItem", back_populates="user", cascade="all, delete-orphan")
