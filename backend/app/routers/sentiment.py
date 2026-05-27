from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from datetime import date, timedelta
from ..database import get_db
from ..models.sentiment import SentimentAnalysis
from ..services.auth import get_current_user
from ..models.user import User

router = APIRouter(prefix="/api/sentiment", tags=["sentiment"])


async def _get_cached(db: AsyncSession, symbol: str) -> SentimentAnalysis | None:
    result = await db.execute(
        select(SentimentAnalysis)
        .where(SentimentAnalysis.symbol == symbol)
        .order_by(SentimentAnalysis.created_at.desc())
        .limit(1)
    )
    return result.scalar_one_or_none()


@router.get("/{symbol}")
async def get_sentiment(
    symbol: str,
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    symbol = symbol.upper()
    cached = await _get_cached(db, symbol)
    if not cached:
        return {"symbol": symbol, "available": False}

    return {
        "symbol": symbol,
        "available": True,
        "signal_value": cached.signal_value,
        "label": cached.label,
        "confidence": cached.confidence,
        "reasoning": cached.reasoning,
        "factors": cached.factors,
        "model_used": cached.model_used,
        "analyzed_at": str(cached.created_at),
    }


@router.post("/{symbol}/analyze")
async def trigger_analysis(
    symbol: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    from ..config import get_settings
    settings = get_settings()

    symbol = symbol.upper()

    if not settings.anthropic_api_key:
        raise HTTPException(status_code=503, detail="LLM analysis not configured")

    cached = await _get_cached(db, symbol)
    cache_hours = settings.sentiment_cache_hours
    if cached and cached.created_at:
        from datetime import datetime, timezone
        age = datetime.now(timezone.utc) - cached.created_at
        if age.total_seconds() < cache_hours * 3600:
            return {
                "symbol": symbol,
                "available": True,
                "signal_value": cached.signal_value,
                "label": cached.label,
                "confidence": cached.confidence,
                "reasoning": cached.reasoning,
                "factors": cached.factors,
                "model_used": cached.model_used,
                "analyzed_at": str(cached.created_at),
                "cached": True,
            }

    daily_count_result = await db.execute(
        select(func.count(SentimentAnalysis.id)).where(
            SentimentAnalysis.date == date.today()
        )
    )
    daily_count = daily_count_result.scalar() or 0
    if daily_count >= settings.sentiment_max_daily_calls:
        raise HTTPException(status_code=429, detail="Daily analysis limit reached")

    try:
        from ..services.llm_sentiment import LLMSentimentAnalyzer
        from ..services.market_data import get_ohlcv, ensure_stock

        analyzer = LLMSentimentAnalyzer()

        stock = await ensure_stock(db, symbol)
        stock_info = {
            "name": stock.name or symbol,
            "sector": stock.sector or "",
            "exchange": stock.exchange or "",
        }

        start = date.today() - timedelta(days=60)
        df = await get_ohlcv(db, symbol, start_date=start)
        ohlcv_summary = {}
        if not df.empty:
            current = float(df.iloc[-1]["close"])
            ohlcv_summary["current_price"] = round(current, 2)
            if len(df) >= 5:
                week_ago_price = float(df.iloc[-5]["close"])
                ohlcv_summary["change_1w_pct"] = round((current - week_ago_price) / week_ago_price * 100, 1)
            if len(df) >= 20:
                month_ago_price = float(df.iloc[-20]["close"])
                ohlcv_summary["change_1m_pct"] = round((current - month_ago_price) / month_ago_price * 100, 1)

        result = await analyzer.analyze(symbol, stock_info, ohlcv_summary, mode="deep")

        record = SentimentAnalysis(
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
            cost_usd=_estimate_cost(result.model_used, result.input_tokens, result.output_tokens),
        )

        from sqlalchemy.dialects.postgresql import insert as pg_insert
        stmt = pg_insert(SentimentAnalysis).values(
            symbol=record.symbol,
            date=record.date,
            signal_value=record.signal_value,
            label=record.label,
            confidence=record.confidence,
            reasoning=record.reasoning,
            factors=record.factors,
            source_data=record.source_data,
            model_used=record.model_used,
            input_tokens=record.input_tokens,
            output_tokens=record.output_tokens,
            cost_usd=record.cost_usd,
        ).on_conflict_do_update(
            index_elements=["symbol", "date"],
            set_={
                "signal_value": record.signal_value,
                "label": record.label,
                "confidence": record.confidence,
                "reasoning": record.reasoning,
                "factors": record.factors,
                "source_data": record.source_data,
                "model_used": record.model_used,
                "input_tokens": record.input_tokens,
                "output_tokens": record.output_tokens,
                "cost_usd": record.cost_usd,
            },
        )
        await db.execute(stmt)
        await db.commit()

        return {
            "symbol": symbol,
            "available": True,
            "signal_value": result.score,
            "label": result.label,
            "confidence": result.confidence,
            "reasoning": result.reasoning,
            "factors": result.factors,
            "model_used": result.model_used,
            "analyzed_at": str(date.today()),
            "cached": False,
        }

    except ValueError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")


def _estimate_cost(model: str, input_tokens: int, output_tokens: int) -> float:
    if "haiku" in model:
        return (input_tokens * 0.25 + output_tokens * 1.25) / 1_000_000
    elif "sonnet" in model:
        return (input_tokens * 3.0 + output_tokens * 15.0) / 1_000_000
    elif "opus" in model:
        return (input_tokens * 15.0 + output_tokens * 75.0) / 1_000_000
    return 0.0
