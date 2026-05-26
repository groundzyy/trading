from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import date, timedelta
from ..database import get_db
from ..services.market_data import get_ohlcv, fetch_ohlcv_from_provider, save_ohlcv, ensure_stock
from ..services.signal_engine import compute_swing_structure, compute_indicator, get_indicator_data
from ..signals.registry import list_methods
from ..services.auth import get_current_user
from ..models.user import User

router = APIRouter(prefix="/api/signals", tags=["signals"])

RANGE_MAP = {"1M": 30, "3M": 90, "6M": 180, "1Y": 365, "5Y": 1825, "Max": 3650}


async def _ensure_ohlcv(db: AsyncSession, symbol: str, days: int = 365):
    start = date.today() - timedelta(days=max(days, 365))
    df = await get_ohlcv(db, symbol, start_date=start)
    if df.empty:
        await ensure_stock(db, symbol)
        provider_df = await fetch_ohlcv_from_provider(symbol, period="5y")
        if not provider_df.empty:
            await save_ohlcv(db, provider_df)
        df = await get_ohlcv(db, symbol, start_date=start)
    return df


@router.get("/methods")
async def get_methods():
    return {"methods": list_methods()}


@router.get("/{symbol}/swing")
async def get_swing_points(
    symbol: str,
    range: str = Query("1Y", enum=list(RANGE_MAP.keys())),
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    symbol = symbol.upper()
    days = RANGE_MAP.get(range, 365)
    df = await _ensure_ohlcv(db, symbol, days)

    if df.empty:
        return {"symbol": symbol, "swing_points": [], "signal": None}

    result_df, points = compute_swing_structure(df)
    from ..signals.registry import get_method
    method = get_method("swing_structure")
    sig = method.signal(result_df)

    return {
        "symbol": symbol,
        "swing_points": points,
        "signal": {"value": sig.value, "label": sig.label, "details": sig.details},
    }


@router.get("/{symbol}/indicator/{indicator_id}")
async def get_indicator(
    symbol: str,
    indicator_id: str,
    range: str = Query("1Y", enum=list(RANGE_MAP.keys())),
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    symbol = symbol.upper()
    days = RANGE_MAP.get(range, 365)
    df = await _ensure_ohlcv(db, symbol, days)

    if df.empty:
        return {"symbol": symbol, "indicator_id": indicator_id, "data": [], "signal": None}

    _, sig = compute_indicator(indicator_id, df)
    data = get_indicator_data(indicator_id, df)

    return {
        "symbol": symbol,
        "indicator_id": indicator_id,
        "data": data,
        "signal": {"value": sig.value, "label": sig.label, "details": sig.details},
    }
