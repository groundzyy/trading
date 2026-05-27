"""Data gathering for LLM sentiment analysis."""
from abc import ABC, abstractmethod
import httpx
import logging

logger = logging.getLogger(__name__)


class DataProvider(ABC):
    @abstractmethod
    async def gather(self, symbol: str) -> list[dict]:
        ...


class YFinanceNewsProvider(DataProvider):
    async def gather(self, symbol: str) -> list[dict]:
        try:
            import yfinance as yf
            import asyncio
            ticker = await asyncio.to_thread(lambda: yf.Ticker(symbol))
            news = await asyncio.to_thread(lambda: ticker.news)
            if not news:
                return []
            items = []
            for article in news[:10]:
                items.append({
                    "source": "yahoo_finance",
                    "title": article.get("title", ""),
                    "text": article.get("title", ""),
                    "date": "",
                    "url": article.get("link", ""),
                })
            return items
        except Exception as e:
            logger.warning(f"YFinance news fetch failed for {symbol}: {e}")
            return []


class YFinanceAnalystProvider(DataProvider):
    async def gather(self, symbol: str) -> list[dict]:
        try:
            import yfinance as yf
            import asyncio
            ticker = await asyncio.to_thread(lambda: yf.Ticker(symbol))
            info = await asyncio.to_thread(lambda: ticker.info)
            items = []
            if info:
                rec = info.get("recommendationKey", "")
                target = info.get("targetMeanPrice")
                current = info.get("currentPrice") or info.get("regularMarketPrice")
                if rec or target:
                    items.append({
                        "source": "analyst_consensus",
                        "title": f"Analyst consensus: {rec}",
                        "text": f"Recommendation: {rec}. Target price: ${target}. Current: ${current}.",
                        "date": "",
                        "url": "",
                    })
                earnings_growth = info.get("earningsGrowth")
                revenue_growth = info.get("revenueGrowth")
                if earnings_growth is not None or revenue_growth is not None:
                    items.append({
                        "source": "earnings",
                        "title": "Earnings & Revenue Growth",
                        "text": f"Earnings growth: {earnings_growth}, Revenue growth: {revenue_growth}",
                        "date": "",
                        "url": "",
                    })
            return items
        except Exception as e:
            logger.warning(f"YFinance analyst data fetch failed for {symbol}: {e}")
            return []


class FinnhubNewsProvider(DataProvider):
    def __init__(self, api_key: str):
        self.api_key = api_key

    async def gather(self, symbol: str) -> list[dict]:
        if not self.api_key:
            return []
        try:
            from datetime import date, timedelta
            today = date.today()
            week_ago = today - timedelta(days=7)
            url = f"https://finnhub.io/api/v1/company-news?symbol={symbol}&from={week_ago}&to={today}&token={self.api_key}"
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.get(url)
                resp.raise_for_status()
                data = resp.json()
            items = []
            for article in data[:15]:
                items.append({
                    "source": "finnhub",
                    "title": article.get("headline", ""),
                    "text": article.get("summary", ""),
                    "date": article.get("datetime", ""),
                    "url": article.get("url", ""),
                })
            return items
        except Exception as e:
            logger.warning(f"Finnhub news fetch failed for {symbol}: {e}")
            return []


class SentimentDataGatherer:
    def __init__(self, providers: list[DataProvider] | None = None):
        self.providers = providers or [YFinanceNewsProvider(), YFinanceAnalystProvider()]

    async def gather_all(self, symbol: str, stock_info: dict, ohlcv_summary: dict) -> dict:
        all_items: list[dict] = []
        for provider in self.providers:
            try:
                items = await provider.gather(symbol)
                all_items.extend(items)
            except Exception as e:
                logger.warning(f"Provider {provider.__class__.__name__} failed: {e}")

        return {
            "symbol": symbol,
            "name": stock_info.get("name", symbol),
            "sector": stock_info.get("sector", ""),
            "exchange": stock_info.get("exchange", ""),
            "price_summary": ohlcv_summary,
            "data_items": all_items,
        }
