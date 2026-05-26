"""
Celery tasks for daily signal computation.
Run with: celery -A app.tasks.daily_scan worker -B
"""
import asyncio
from datetime import date, timedelta
from celery import Celery
from sqlalchemy import select, create_engine
from sqlalchemy.orm import Session
from ..config import get_settings

settings = get_settings()
celery_app = Celery("trading", broker=settings.redis_url)
celery_app.conf.beat_schedule = {
    "daily-scan": {
        "task": "app.tasks.daily_scan.run_daily_scan",
        "schedule": 86400.0,  # every 24 hours
    },
}


def _get_sync_session():
    from sqlalchemy.orm import sessionmaker
    engine = create_engine(settings.database_url_sync)
    SessionLocal = sessionmaker(bind=engine)
    return SessionLocal()


@celery_app.task(name="app.tasks.daily_scan.run_daily_scan")
def run_daily_scan():
    import yfinance as yf
    import pandas as pd
    from ..models.stock import Stock, OHLCV
    from ..models.signal import SignalResult
    from ..signals.swing_structure import SwingStructure
    from ..signals.macd import MACD
    from ..signals.rsi import RSI
    from ..signals.ma import MovingAverage
    from ..signals.volume import VolumeSignal
    from ..services.decision_engine import compute_decision

    session = _get_sync_session()

    try:
        stocks = session.query(Stock).all()
        swing = SwingStructure()
        indicators = {"macd": MACD(), "rsi": RSI(), "ma": MovingAverage(), "volume": VolumeSignal()}
        default_weights = {"macd": 0.3, "rsi": 0.25, "ma": 0.25, "volume": 0.2}

        for stock in stocks:
            try:
                rows = session.query(OHLCV).filter(
                    OHLCV.symbol == stock.symbol,
                    OHLCV.date >= date.today() - timedelta(days=400),
                ).order_by(OHLCV.date).all()

                if len(rows) < 30:
                    continue

                df = pd.DataFrame([{
                    "date": r.date, "open": r.open, "high": r.high,
                    "low": r.low, "close": r.close, "volume": r.volume,
                } for r in rows])

                swing_result = swing.compute(df)
                primary_signal = swing.signal(swing_result)

                indicator_signals = {}
                for method_id, method in indicators.items():
                    result = method.compute(df)
                    indicator_signals[method_id] = method.signal(result)

                decision = compute_decision(
                    stock.symbol, primary_signal, indicator_signals, default_weights
                )

                if decision.decision in ("BUY", "SELL"):
                    signal_result = SignalResult(
                        symbol=stock.symbol,
                        date=date.today(),
                        signal_type=decision.decision,
                        primary_trigger="swing_structure",
                        trigger_price=df.iloc[-1]["close"],
                        composite_score=decision.composite_score,
                        indicator_scores={
                            r["id"]: r["signal"] for r in decision.indicator_results
                        },
                    )
                    session.merge(signal_result)

            except Exception as e:
                print(f"Error processing {stock.symbol}: {e}")
                continue

        session.commit()
    finally:
        session.close()

    return "Scan complete"
