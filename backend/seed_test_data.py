"""
Seed the database with realistic OHLCV data for testing.
Generates data that includes clear swing patterns for signal testing.
"""
import asyncio
import numpy as np
import pandas as pd
from datetime import date, timedelta
from app.database import engine, Base, async_session
from app.models.stock import Stock, OHLCV
from app.services.market_data import save_ohlcv
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy import select


def generate_ohlcv(symbol: str, days: int = 500, base_price: float = 100.0,
                   volatility: float = 0.02, trend: float = 0.0003) -> pd.DataFrame:
    """Generate realistic OHLCV data with swing patterns."""
    np.random.seed(hash(symbol) % 2**31)

    dates = [date.today() - timedelta(days=days - i) for i in range(days)]

    # Generate prices with trend + mean-reverting swings
    prices = [base_price]
    for i in range(1, days):
        # Add cyclical component (creates swing patterns)
        cycle = 0.01 * np.sin(2 * np.pi * i / 40) + 0.005 * np.sin(2 * np.pi * i / 120)
        drift = trend + cycle
        shock = np.random.normal(0, volatility)
        new_price = prices[-1] * (1 + drift + shock)
        prices.append(max(new_price, 1.0))

    records = []
    for i, (d, close) in enumerate(zip(dates, prices)):
        daily_range = close * np.random.uniform(0.005, 0.025)
        high = close + np.random.uniform(0, daily_range)
        low = close - np.random.uniform(0, daily_range)
        open_price = low + np.random.uniform(0, high - low)
        volume = int(np.random.lognormal(16, 0.5))

        records.append({
            "symbol": symbol,
            "date": d,
            "open": round(open_price, 2),
            "high": round(high, 2),
            "low": round(low, 2),
            "close": round(close, 2),
            "volume": volume,
        })

    return pd.DataFrame(records)


STOCKS = [
    {"symbol": "AAPL", "name": "Apple Inc.", "exchange": "NASDAQ", "sector": "Technology",
     "base": 190, "vol": 0.018, "trend": 0.0004},
    {"symbol": "TSLA", "name": "Tesla Inc.", "exchange": "NASDAQ", "sector": "Automotive",
     "base": 250, "vol": 0.035, "trend": -0.0001},
    {"symbol": "NVDA", "name": "NVIDIA Corp.", "exchange": "NASDAQ", "sector": "Technology",
     "base": 130, "vol": 0.028, "trend": 0.0008},
    {"symbol": "MSFT", "name": "Microsoft Corp.", "exchange": "NASDAQ", "sector": "Technology",
     "base": 380, "vol": 0.015, "trend": 0.0003},
    {"symbol": "GOOG", "name": "Alphabet Inc.", "exchange": "NASDAQ", "sector": "Technology",
     "base": 155, "vol": 0.02, "trend": 0.0002},
    {"symbol": "META", "name": "Meta Platforms Inc.", "exchange": "NASDAQ", "sector": "Technology",
     "base": 480, "vol": 0.025, "trend": 0.0005},
    {"symbol": "AMZN", "name": "Amazon.com Inc.", "exchange": "NASDAQ", "sector": "Consumer Cyclical",
     "base": 180, "vol": 0.022, "trend": 0.0003},
    {"symbol": "JPM", "name": "JPMorgan Chase", "exchange": "NYSE", "sector": "Financial Services",
     "base": 195, "vol": 0.014, "trend": 0.0002},
]


async def seed():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with async_session() as db:
        for s in STOCKS:
            # Upsert stock
            result = await db.execute(select(Stock).where(Stock.symbol == s["symbol"]))
            stock = result.scalar_one_or_none()
            if not stock:
                stock = Stock(symbol=s["symbol"], name=s["name"],
                              exchange=s["exchange"], sector=s["sector"])
                db.add(stock)
            else:
                stock.name = s["name"]
                stock.exchange = s["exchange"]
                stock.sector = s["sector"]

            # Generate and save OHLCV
            df = generate_ohlcv(s["symbol"], days=500,
                                base_price=s["base"], volatility=s["vol"],
                                trend=s["trend"])
            await save_ohlcv(db, df)
            print(f"  Seeded {s['symbol']}: {len(df)} candles, "
                  f"price range ${df['low'].min():.2f} - ${df['high'].max():.2f}")

        await db.commit()

    print("\nDone! Database seeded with test data.")


if __name__ == "__main__":
    asyncio.run(seed())
