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
│   │   ├── models/          (user, stock, watchlist, signal)
│   │   ├── routers/         (auth, stocks, signals, decision, watchlist, scanner)
│   │   ├── services/        (market_data, signal_engine, decision_engine, auth)
│   │   ├── signals/         (base, registry, swing_structure, macd, rsi, ma, volume, kdj)
│   │   └── tasks/           (daily_scan)
│   └── tests/
├── frontend/
│   ├── package.json
│   ├── Dockerfile
│   ├── src/
│   │   ├── pages/           (Dashboard, StockDetail, Scanner, Login)
│   │   ├── components/      (CandlestickChart, IndicatorPanel, DecisionMatrix, WatchlistTable)
│   │   ├── services/        (api.ts)
│   │   └── types/           (index.ts)
│   └── public/
└── mobile/                  (Phase 3)
```

---

## Implementation Phases

### Phase 1 — Core Engine + Web MVP (current)
- Backend: FastAPI + PostgreSQL + JWT auth
- Backend: Market data fetcher (yfinance, US stocks, daily bars)
- Backend: Larry Williams swing structure detection
- Backend: Secondary indicators (MACD, RSI, MA, Volume, KDJ)
- Backend: Decision engine (weighted matrix)
- Backend: Celery daily scan job
- Frontend: Login/register, Dashboard, Stock detail with chart, Decision matrix

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
