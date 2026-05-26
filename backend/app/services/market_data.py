import asyncio
import yfinance as yf
import pandas as pd
from datetime import date, timedelta
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.dialects.postgresql import insert as pg_insert
from ..models.stock import Stock, OHLCV


def _fetch_yf_history(symbol: str, period: str) -> pd.DataFrame:
    ticker = yf.Ticker(symbol)
    return ticker.history(period=period, auto_adjust=True)


async def fetch_ohlcv_from_provider(symbol: str, period: str = "1y") -> pd.DataFrame:
    df = await asyncio.to_thread(_fetch_yf_history, symbol, period)
    if df.empty:
        return df
    df = df.reset_index()
    df = df.rename(columns={"Date": "date", "Open": "open", "High": "high",
                             "Low": "low", "Close": "close", "Volume": "volume"})
    df["date"] = pd.to_datetime(df["date"]).dt.date
    df["symbol"] = symbol
    return df[["symbol", "date", "open", "high", "low", "close", "volume"]]


async def save_ohlcv(db: AsyncSession, df: pd.DataFrame):
    if df.empty:
        return
    records = df.to_dict("records")
    stmt = pg_insert(OHLCV).values(records).on_conflict_do_update(
        index_elements=["symbol", "date"],
        set_={
            "open": pg_insert(OHLCV).excluded.open,
            "high": pg_insert(OHLCV).excluded.high,
            "low": pg_insert(OHLCV).excluded.low,
            "close": pg_insert(OHLCV).excluded.close,
            "volume": pg_insert(OHLCV).excluded.volume,
        },
    )
    await db.execute(stmt)
    await db.commit()


async def get_ohlcv(db: AsyncSession, symbol: str, start_date: date | None = None,
                    end_date: date | None = None) -> pd.DataFrame:
    stmt = select(OHLCV).where(OHLCV.symbol == symbol)
    if start_date:
        stmt = stmt.where(OHLCV.date >= start_date)
    if end_date:
        stmt = stmt.where(OHLCV.date <= end_date)
    stmt = stmt.order_by(OHLCV.date)

    result = await db.execute(stmt)
    rows = result.scalars().all()

    if not rows:
        return pd.DataFrame(columns=["date", "open", "high", "low", "close", "volume"])

    data = [{
        "date": r.date, "open": r.open, "high": r.high,
        "low": r.low, "close": r.close, "volume": r.volume,
    } for r in rows]
    return pd.DataFrame(data)


async def ensure_stock(db: AsyncSession, symbol: str) -> Stock:
    result = await db.execute(select(Stock).where(Stock.symbol == symbol))
    stock = result.scalar_one_or_none()
    if stock:
        return stock

    try:
        info = await asyncio.to_thread(lambda: yf.Ticker(symbol).info)
        name = info.get("shortName", info.get("longName", symbol))
        exchange = info.get("exchange", "")
        sector = info.get("sector", "")
    except Exception:
        name, exchange, sector = symbol, "", ""

    stock = Stock(symbol=symbol, name=name, exchange=exchange, sector=sector)
    db.add(stock)
    await db.commit()
    await db.refresh(stock)
    return stock


async def search_stocks(query: str) -> list[dict]:
    try:
        results = await asyncio.to_thread(lambda: yf.Tickers(query))
        return [{"symbol": t, "name": t} for t in results.tickers]
    except Exception:
        return [{"symbol": query.upper(), "name": query.upper()}]
