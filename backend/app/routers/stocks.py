from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import date, timedelta
from ..database import get_db
from ..services.market_data import fetch_ohlcv_from_provider, save_ohlcv, get_ohlcv, ensure_stock
from ..services.auth import get_current_user
from ..models.user import User

router = APIRouter(prefix="/api/stocks", tags=["stocks"])


RANGE_MAP = {
    "1M": 30, "3M": 90, "6M": 180, "1Y": 365, "5Y": 1825, "Max": 3650,
}


@router.get("/{symbol}/ohlcv")
async def get_stock_ohlcv(
    symbol: str,
    range: str = Query("1Y", enum=list(RANGE_MAP.keys())),
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    symbol = symbol.upper()
    await ensure_stock(db, symbol)

    days = RANGE_MAP.get(range, 365)
    start = date.today() - timedelta(days=days)

    df = await get_ohlcv(db, symbol, start_date=start)
    if df.empty:
        provider_df = await fetch_ohlcv_from_provider(symbol, period="5y")
        if not provider_df.empty:
            await save_ohlcv(db, provider_df)
            df = await get_ohlcv(db, symbol, start_date=start)

    candles = []
    for _, row in df.iterrows():
        candles.append({
            "time": str(row["date"]),
            "open": round(row["open"], 2),
            "high": round(row["high"], 2),
            "low": round(row["low"], 2),
            "close": round(row["close"], 2),
            "volume": int(row["volume"]),
        })

    return {"symbol": symbol, "range": range, "candles": candles}


@router.get("/{symbol}/info")
async def get_stock_info(
    symbol: str,
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    symbol = symbol.upper()
    stock = await ensure_stock(db, symbol)
    return {
        "symbol": stock.symbol,
        "name": stock.name,
        "exchange": stock.exchange,
        "sector": stock.sector,
    }


@router.get("/search/{query}")
async def search(
    query: str,
    _user: User = Depends(get_current_user),
):
    from ..services.market_data import search_stocks
    results = await search_stocks(query)
    return {"results": results}
