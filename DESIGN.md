# Trading Signal App — Design Document

## Context

Build a publishable, multi-user stock signal app (web + mobile). The core idea:

1. Server **pre-computes signals for all stocks** in the market continuously
2. Each user maintains a personal **watchlist**
3. The primary buy signal is **Larry Williams' intermediate-term low** (triggered by the formation of an intermediate-term high)
4. Once the primary signal fires, the system checks **secondary indicators** (MACD, RSI, MA, etc.)
5. A **weighted decision matrix** combines primary + secondary signals into a final BUY/SELL/HOLD decision
6. Users receive **push notifications** or check manually

This is intended for personal use AND public release as a product.

---

## Key Functions

### F1. Server-Side Signal Pre-Computation

The server proactively computes everything daily after market close:

1. Fetch OHLCV for ALL tracked stocks (US market first)
2. Compute swing structure (short-term -> mid-term highs/lows) for every stock
3. Compute secondary indicators (MACD, RSI, MA, KDJ, etc.) for every stock
4. Store results in DB
5. Match signals to user watchlists and dispatch notifications

### F2. Primary Signal — Larry Williams Swing Structure

Hierarchical swing point detection:

- **Short-term High**: a daily HIGH with lower highs on both sides
- **Short-term Low**: a daily LOW with higher lows on both sides
- **Mid-term High**: a short-term high with lower short-term highs on both sides
- **Mid-term Low**: a short-term low with higher short-term lows on both sides
- **Long-term High/Low**: same pattern at mid-term level

Signal logic:
- Mid-term high forms -> activates buy watch
- Mid-term low forms -> **BUY signal fires**
- Price breaks below mid-term low -> **SELL signal**

### F3. Trigger Signal Catalog

Signals serve as either **primary triggers** (gate) or **confirmation indicators** (weighted matrix).

**Category A — Structural**: Larry Williams Mid-term H/L, 1-2-3 Reversal, Wyckoff Spring, OOPS, Smash Day, Inside/Outside Day

**Category B — Momentum**: MACD, RSI, KDJ, Williams %R, Ultimate Oscillator, Bollinger Squeeze

**Category C — Trend**: MA Crossover, Multi-MA Alignment, EMA Ribbon, Price vs MA

**Category D — Volume**: Volume Spike, OBV, VPT, Accumulation/Distribution

**Category E — Volatility**: Larry Williams Volatility Breakout, ATR Breakout, Bollinger Band Width

**Category F — Price Level**: Fibonacci Retracement, Support/Resistance

### F4. Weighted Decision Matrix

Primary signal gates evaluation; secondary indicators produce signals in [-1.0, +1.0]; composite = weighted sum; BUY if > threshold, SELL if < -threshold.

### F5. UI — Traditional Charting Software Style

- Candlestick chart with MA overlays and swing markers (STH/STL, MTH/MTL, LTH/LTL, BUY/SELL arrows)
- Sub-panels for Volume, MACD, KDJ
- Decision matrix panel with weight sliders
- Dashboard with watchlist table
- Market scanner for signal discovery
- Dark trading theme

### F6. Notification System

Push notifications + manual check. Pluggable channels (in-app, FCM, email, Telegram).

### F7. Market-Wide Scanner

Browse pre-computed signals across all stocks. Filter by signal type, date, score.

### F8. LLM-Based Market Sentiment Analysis

AI-powered sentiment analysis using Claude API. Gathers market data (news, analyst ratings, earnings), feeds it to an LLM, and produces a sentiment signal that integrates into the weighted decision matrix.

#### Architecture

**Hybrid plugin approach**: Registered as a signal plugin (`sentiment`) for discovery and weight management, but uses cached LLM results instead of computing over OHLCV data.

```
Data Flow:
  1. Data Gatherer collects news + analyst + earnings data (pluggable providers)
  2. LLM Analyzer constructs structured prompt with market context
  3. Claude API returns JSON: { score, label, confidence, reasoning, factors }
  4. Result cached in PostgreSQL (SentimentAnalysis table, 24h TTL)
  5. Decision router injects cached signal into weighted matrix
  6. Frontend displays reasoning + factor breakdown in SentimentPanel
```

#### Data Sources (Pluggable Providers)

| Provider | Data | API Key Required |
|----------|------|:----------------:|
| **yfinance News** (Tier 1) | Headlines, summaries | No |
| **yfinance Analyst** (Tier 1) | Consensus rating, target price, earnings growth | No |
| **Finnhub** (Tier 2) | Company news with summaries | Yes (free tier: 60 calls/min) |
| **NewsAPI** (future) | Broad news coverage | Yes |
| **Reddit/Twitter** (future) | Social sentiment | Yes |

#### LLM Prompt Strategy

- **System prompt**: Senior market analyst role, structured JSON output schema, calibration guidelines
- **User prompt**: Stock info, price context (1w/1m changes), news headlines, analyst data
- **Output**: `score` [-1.0, +1.0], `label`, `confidence` [0-1], `reasoning` (2-4 sentences), `factors` (sub-scores with notes)
- **Prompt caching**: System prompt uses `cache_control: ephemeral` for 90% cost reduction in batch windows
- **Model selection**: Haiku for batch (cheap, ~$0.03/day for 50 stocks), Sonnet for on-demand deep analysis

#### Signal Integration

The sentiment signal value fed into the decision matrix = `score × confidence`. This attenuates uncertain assessments — a +0.8 score at 40% confidence becomes +0.32 effective signal.

Default weight: 20% of composite (alongside swing_structure 35%, macd/kdj/rsi 15% each).

When no cached sentiment exists, the signal is excluded and remaining weights auto-renormalize.

#### Cost Management

| Control | Default |
|---------|---------|
| Daily LLM call cap | 50 calls/day |
| Cache TTL | 24 hours |
| Per-user on-demand limit | Rate-limited via daily cap |
| Budget tracking | Input/output tokens + cost_usd per analysis |
| Batch model | Claude Haiku (~$0.03/day at 50 stocks) |
| Deep model | Claude Sonnet (user-triggered only) |

#### API Endpoints

```
GET  /api/sentiment/{symbol}          → cached analysis or { available: false }
POST /api/sentiment/{symbol}/analyze  → trigger on-demand analysis (rate-limited)
```

#### Database Schema

```sql
sentiment_analyses:
  id, symbol, date (unique: symbol+date),
  signal_value, label, confidence,
  reasoning (text), factors (json), source_data (json),
  model_used, input_tokens, output_tokens, cost_usd,
  created_at
```

#### Frontend Components

- **SentimentPanel**: Score gauge, label, confidence indicator, reasoning text, expandable factor breakdown with horizontal score bars, "Run Analysis" / "Re-analyze" buttons
- **DecisionMatrix**: AI badge on sentiment row to distinguish from technical indicators

#### Configuration

```
TRADING_ANTHROPIC_API_KEY=sk-ant-...     # Required to enable
TRADING_SENTIMENT_MODEL_BATCH=claude-haiku-4-5-20241022
TRADING_SENTIMENT_MODEL_DEEP=claude-sonnet-4-20250514
TRADING_SENTIMENT_MAX_DAILY_CALLS=50
TRADING_SENTIMENT_CACHE_HOURS=24
TRADING_FINNHUB_API_KEY=               # Optional, for Finnhub news
```

---

## Tech Stack

| Layer | Choice |
|-------|--------|
| Frontend Web | React + TypeScript |
| Mobile App | React Native (Phase 3) |
| Charting | Lightweight Charts (TradingView) |
| Backend | Python (FastAPI) |
| Database | PostgreSQL |
| Task Queue | Celery + Redis |
| Auth | JWT |
| LLM | Claude API (Anthropic SDK) |
| Push | Firebase Cloud Messaging |
| Deployment | Docker Compose |

---

## Project Structure

```
trading/
├── DESIGN.md
├── docker-compose.yml
├── backend/
│   ├── pyproject.toml
│   ├── Dockerfile
│   ├── app/
│   │   ├── main.py
│   │   ├── config.py
│   │   ├── database.py
│   │   ├── models/          (user, stock, watchlist, signal, sentiment)
│   │   ├── routers/         (auth, stocks, signals, decision, watchlist, scanner, sentiment)
│   │   ├── services/        (market_data, signal_engine, decision_engine, auth, llm_sentiment, sentiment_data)
│   │   ├── signals/         (base, registry, swing_structure, macd, rsi, ma, volume, kdj, sentiment)
│   │   └── tasks/           (daily_scan)
│   └── tests/
├── frontend/
│   ├── package.json
│   ├── Dockerfile
│   ├── src/
│   │   ├── pages/           (Dashboard, StockDetail, Scanner, Login)
│   │   ├── components/      (CandlestickChart, IndicatorPanel, DecisionMatrix, SentimentPanel, WatchlistTable)
│   │   ├── services/        (api.ts)
│   │   └── types/           (index.ts)
│   └── public/
└── mobile/                  (Phase 3)
```

---

## Implementation Phases

### Phase 1 — Core Engine + Web MVP [DONE]
- [x] Backend: FastAPI + PostgreSQL + JWT auth
- [x] Backend: Market data fetcher (yfinance, US stocks, daily bars)
- [x] Backend: Larry Williams swing structure detection
- [x] Backend: Secondary indicators (MACD, RSI, MA, Volume, KDJ)
- [x] Backend: Decision engine (weighted matrix)
- [x] Backend: Celery daily scan job
- [x] Frontend: Login/register, Dashboard, Stock detail with chart, Decision matrix
- [x] Symbol validation and error handling

### Phase 1.5 — LLM Sentiment Analysis [DONE]
- [x] Data gathering service (pluggable providers: yfinance, Finnhub)
- [x] Claude API integration with structured JSON output
- [x] Sentiment signal plugin registered in signal registry
- [x] Cached sentiment injection into decision matrix
- [x] REST API: GET cached / POST trigger analysis
- [x] SentimentPanel component with reasoning + factor breakdown
- [x] AI badge in DecisionMatrix
- [x] Cost tracking and rate limiting
- [ ] Finnhub / additional data provider integration (needs API key)
- [ ] Sentiment in daily Celery scan batch
- [ ] Sentiment trend chart (historical scores over time)

### Phase 2 — Notifications + Scanner
- Push notification system (FCM + in-app)
- Market-wide scanner page
- More indicators (Bollinger, Williams %R, Ultimate Oscillator)
- Strategy profiles

### Phase 3 — Mobile + Expansion
- React Native mobile app
- Additional markets (HK, CN, crypto)
- Additional timeframes (weekly, intraday)
- Backtesting engine
