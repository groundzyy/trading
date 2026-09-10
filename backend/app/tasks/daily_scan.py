"""
Celery tasks for daily signal computation.
Run with: celery -A app.tasks.daily_scan worker -B
"""
import asyncio
from datetime import date, timedelta
from celery import Celery
from celery.schedules import crontab
from sqlalchemy import select, create_engine
from sqlalchemy.orm import Session
from ..config import get_settings
from ..services.llm_sentiment import estimate_cost

settings = get_settings()
celery_app = Celery("trading", broker=settings.redis_url)
celery_app.conf.beat_schedule = {
    "sentiment-batch": {
        "task": "app.tasks.daily_scan.run_sentiment_batch",
        "schedule": crontab(hour=1, minute=0),
    },
    "daily-scan": {
        "task": "app.tasks.daily_scan.run_daily_scan",
        # Runs after the sentiment batch so the scan reads a fresh cache.
        "schedule": crontab(hour=2, minute=0),
    },
}


def _get_sync_session():
    from sqlalchemy.orm import sessionmaker
    engine = create_engine(settings.database_url_sync)
    SessionLocal = sessionmaker(bind=engine)
    return SessionLocal()


def _ohlcv_summary(df) -> dict:
    """Price context handed to the LLM alongside news and analyst data."""
    close = df["close"]
    summary = {"current_price": round(float(close.iloc[-1]), 2)}
    for label, lookback in (("change_1w_pct", 5), ("change_1m_pct", 21)):
        if len(close) > lookback:
            past = float(close.iloc[-1 - lookback])
            if past:
                summary[label] = (float(close.iloc[-1]) - past) / past * 100
    return summary


@celery_app.task(name="app.tasks.daily_scan.run_sentiment_batch")
def run_sentiment_batch():
    """Refresh cached LLM sentiment for watchlisted symbols using the batch model."""
    import pandas as pd
    from datetime import datetime, timedelta as _timedelta, timezone
    from sqlalchemy.dialects.postgresql import insert as pg_insert
    from ..models.stock import Stock, OHLCV
    from ..models.sentiment import SentimentAnalysis
    from ..models.watchlist import WatchlistItem

    if not settings.anthropic_api_key:
        return "Sentiment batch skipped: no API key configured"

    from ..services.llm_sentiment import LLMSentimentAnalyzer

    session = _get_sync_session()
    analyzed = skipped = failed = 0
    total_cost = 0.0

    try:
        analyzer = LLMSentimentAnalyzer()

        symbols = [
            row[0]
            for row in session.query(WatchlistItem.symbol).distinct().all()
        ]
        cutoff = datetime.now(timezone.utc) - _timedelta(hours=settings.sentiment_cache_hours)

        for symbol in symbols[: settings.sentiment_max_daily_calls]:
            try:
                fresh = (
                    session.query(SentimentAnalysis)
                    .filter(
                        SentimentAnalysis.symbol == symbol,
                        SentimentAnalysis.created_at >= cutoff,
                    )
                    .first()
                )
                if fresh:
                    skipped += 1
                    continue

                rows = (
                    session.query(OHLCV)
                    .filter(
                        OHLCV.symbol == symbol,
                        OHLCV.date >= date.today() - timedelta(days=60),
                    )
                    .order_by(OHLCV.date)
                    .all()
                )
                if len(rows) < 5:
                    skipped += 1
                    continue

                df = pd.DataFrame([{"date": r.date, "close": r.close} for r in rows])
                stock = session.query(Stock).filter(Stock.symbol == symbol).first()
                stock_info = {
                    "name": stock.name if stock else symbol,
                    "sector": stock.sector if stock else "",
                }

                result = asyncio.run(
                    analyzer.analyze(symbol, stock_info, _ohlcv_summary(df), mode="batch")
                )
                cost = estimate_cost(
                    result.model_used, result.input_tokens, result.output_tokens
                )
                total_cost += cost

                session.execute(
                    pg_insert(SentimentAnalysis)
                    .values(
                        symbol=symbol,
                        date=date.today(),
                        signal_value=result.score,
                        label=result.label,
                        confidence=result.confidence,
                        reasoning=result.reasoning,
                        factors=result.factors,
                        source_data=result.source_data,
                        model_used=result.model_used,
                        input_tokens=result.input_tokens,
                        output_tokens=result.output_tokens,
                        cost_usd=cost,
                    )
                    .on_conflict_do_update(
                        index_elements=["symbol", "date"],
                        set_={
                            "signal_value": result.score,
                            "label": result.label,
                            "confidence": result.confidence,
                            "reasoning": result.reasoning,
                            "factors": result.factors,
                            "source_data": result.source_data,
                            "model_used": result.model_used,
                            "input_tokens": result.input_tokens,
                            "output_tokens": result.output_tokens,
                            "cost_usd": cost,
                        },
                    )
                )
                session.commit()
                analyzed += 1

            except Exception as e:
                session.rollback()
                failed += 1
                print(f"Sentiment analysis failed for {symbol}: {e}")
                continue
    finally:
        session.close()

    return (
        f"Sentiment batch complete: {analyzed} analyzed, {skipped} cached, "
        f"{failed} failed, ~${total_cost:.4f}"
    )


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
    from ..signals.base import Signal
    from ..models.sentiment import SentimentAnalysis
    from ..services.decision_engine import compute_decision

    session = _get_sync_session()

    try:
        stocks = session.query(Stock).all()
        swing = SwingStructure()
        indicators = {"macd": MACD(), "rsi": RSI(), "ma": MovingAverage(), "volume": VolumeSignal()}
        default_weights = {
            "macd": 0.25,
            "rsi": 0.2,
            "ma": 0.2,
            "volume": 0.15,
            "sentiment": 0.2,
        }

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

                cached = (
                    session.query(SentimentAnalysis)
                    .filter(SentimentAnalysis.symbol == stock.symbol)
                    .order_by(SentimentAnalysis.date.desc())
                    .first()
                )
                if cached:
                    indicator_signals["sentiment"] = Signal(
                        value=cached.signal_value * cached.confidence,
                        label=cached.label,
                        details={
                            "reasoning": cached.reasoning,
                            "confidence": cached.confidence,
                            "model": cached.model_used,
                        },
                    )

                decision = compute_decision(
                    stock.symbol, primary_signal, indicator_signals, default_weights
                )

                if decision.decision in ("BUY", "SELL"):
                    signal_result = SignalResult(
                        symbol=stock.symbol,
                        date=date.today(),
                        signal_type=decision.decision,
                        primary_trigger="swing_structure",
                        trigger_price=float(df.iloc[-1]["close"]),
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
