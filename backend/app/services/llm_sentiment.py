"""LLM-based market sentiment analysis using Claude API."""
import json
import logging
from dataclasses import dataclass
from datetime import date

import anthropic

from ..config import get_settings
from .sentiment_data import SentimentDataGatherer, FinnhubNewsProvider

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are a senior market analyst. Analyze the market sentiment for the given stock based on the provided data.

You must respond with valid JSON only, no other text.

Output format:
{
  "score": <float from -1.0 to 1.0, where -1.0 is extremely bearish and 1.0 is extremely bullish>,
  "label": <one of: "Strong Bearish", "Bearish", "Slightly Bearish", "Neutral", "Slightly Bullish", "Bullish", "Strong Bullish">,
  "confidence": <float from 0.0 to 1.0, how confident you are in this assessment>,
  "reasoning": <string, 2-4 sentences explaining your overall assessment>,
  "factors": [
    {"name": "News Sentiment", "score": <float -1 to 1>, "note": <short explanation>},
    {"name": "Analyst Consensus", "score": <float -1 to 1>, "note": <short explanation>},
    {"name": "Earnings Outlook", "score": <float -1 to 1>, "note": <short explanation>},
    {"name": "Market Context", "score": <float -1 to 1>, "note": <short explanation>}
  ]
}

Guidelines:
- Be calibrated: most stocks should score between -0.3 and +0.3 unless there is strong evidence
- If data is sparse, lower your confidence score accordingly
- Consider both bullish and bearish factors before reaching a conclusion
- The final score should reflect a weighted view of all factors"""


# Per-million-token (input, output) rates, matched against the model id by substring.
MODEL_PRICING = {
    "haiku": (1.0, 5.0),
    "sonnet": (2.0, 10.0),
    "opus": (5.0, 25.0),
}


def estimate_cost(model: str, input_tokens: int, output_tokens: int) -> float:
    rate_in, rate_out = next(
        (rates for key, rates in MODEL_PRICING.items() if key in model),
        MODEL_PRICING["sonnet"],
    )
    return round(input_tokens / 1e6 * rate_in + output_tokens / 1e6 * rate_out, 6)


@dataclass
class SentimentResult:
    score: float
    label: str
    confidence: float
    reasoning: str
    factors: list[dict]
    model_used: str
    input_tokens: int
    output_tokens: int
    source_data: dict


class LLMSentimentAnalyzer:
    def __init__(self):
        self.settings = get_settings()
        if not self.settings.anthropic_api_key:
            raise ValueError("TRADING_ANTHROPIC_API_KEY not configured")
        self.client = anthropic.Anthropic(api_key=self.settings.anthropic_api_key)
        providers = None
        if self.settings.finnhub_api_key:
            from .sentiment_data import YFinanceNewsProvider, YFinanceAnalystProvider
            providers = [
                YFinanceNewsProvider(),
                YFinanceAnalystProvider(),
                FinnhubNewsProvider(self.settings.finnhub_api_key),
            ]
        self.gatherer = SentimentDataGatherer(providers)

    async def analyze(
        self,
        symbol: str,
        stock_info: dict,
        ohlcv_summary: dict,
        mode: str = "batch",
    ) -> SentimentResult:
        data = await self.gatherer.gather_all(symbol, stock_info, ohlcv_summary)

        model = (
            self.settings.sentiment_model_deep
            if mode == "deep"
            else self.settings.sentiment_model_batch
        )

        user_prompt = self._build_user_prompt(data, mode)

        response = self.client.messages.create(
            model=model,
            max_tokens=1024,
            system=[{
                "type": "text",
                "text": SYSTEM_PROMPT,
                "cache_control": {"type": "ephemeral"},
            }],
            messages=[{"role": "user", "content": user_prompt}],
        )

        raw_text = response.content[0].text
        parsed = self._parse_response(raw_text)

        return SentimentResult(
            score=parsed["score"],
            label=parsed["label"],
            confidence=parsed["confidence"],
            reasoning=parsed["reasoning"],
            factors=parsed["factors"],
            model_used=model,
            input_tokens=response.usage.input_tokens,
            output_tokens=response.usage.output_tokens,
            source_data=data,
        )

    def _build_user_prompt(self, data: dict, mode: str) -> str:
        parts = [f"Analyze the market sentiment for {data['symbol']} ({data['name']})."]

        if data.get("sector"):
            parts.append(f"Sector: {data['sector']}")

        price = data.get("price_summary", {})
        if price:
            parts.append(f"\nRecent price data:")
            if "current_price" in price:
                parts.append(f"  Current price: ${price['current_price']}")
            if "change_1w_pct" in price:
                parts.append(f"  1-week change: {price['change_1w_pct']:.1f}%")
            if "change_1m_pct" in price:
                parts.append(f"  1-month change: {price['change_1m_pct']:.1f}%")

        items = data.get("data_items", [])
        if items:
            parts.append(f"\nMarket data ({len(items)} items):")
            for item in items:
                source = item.get("source", "unknown")
                title = item.get("title", "")
                text = item.get("text", "")
                if title:
                    parts.append(f"  [{source}] {title}")
                    if text and text != title and len(text) < 500:
                        parts.append(f"    {text}")
        else:
            parts.append("\nNo recent news or analyst data available. Base your analysis on general market knowledge and the price data provided. Set confidence low.")

        if mode == "deep":
            parts.append("\nPerform a thorough deep analysis. Consider industry trends, competitive positioning, macroeconomic factors, and any relevant catalysts.")

        return "\n".join(parts)

    def _parse_response(self, raw: str) -> dict:
        try:
            text = raw.strip()
            if text.startswith("```"):
                text = text.split("\n", 1)[1] if "\n" in text else text[3:]
                if text.endswith("```"):
                    text = text[:-3]
            return json.loads(text)
        except (json.JSONDecodeError, IndexError):
            logger.warning(f"Failed to parse LLM response, returning neutral: {raw[:200]}")
            return {
                "score": 0.0,
                "label": "Neutral",
                "confidence": 0.1,
                "reasoning": "Failed to parse LLM analysis response.",
                "factors": [],
            }
