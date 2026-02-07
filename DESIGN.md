# Trading App — Design Document

## 1. Overview

A web-accessible trading analysis application that provides:

- **Candlestick charting** with configurable time ranges
- **Technical analysis indicators** (MA, MACD, KDJ, and extensible for more)
- **Weighted decision matrix** to combine multiple indicators into a Buy / Hold / Sell recommendation per stock

The system is designed to be **extensible** — new analysis methods can be added over time (e.g., from books or research) without restructuring the core.

---

## 2. Architecture

```
┌─────────────────────────────────────────────────┐
│                  Browser (SPA)                  │
│                                                 │
│  ┌───────────┐  ┌────────────┐  ┌────────────┐ │
│  │ Chart View│  │ Indicators │  │  Decision  │ │
│  │(Candlestk)│  │   Panel    │  │   Panel    │ │
│  └─────┬─────┘  └─────┬──────┘  └─────┬──────┘ │
│        └───────────────┼───────────────┘        │
│                        │ REST / WebSocket        │
└────────────────────────┼────────────────────────┘
                         │
┌────────────────────────┼────────────────────────┐
│               Backend API Server                │
│                                                 │
│  ┌────────────┐ ┌──────────────┐ ┌───────────┐ │
│  │  Market    │ │  Indicator   │ │  Decision  │ │
│  │  Data Svc  │ │   Engine     │ │   Engine   │ │
│  └─────┬──────┘ └──────────────┘ └───────────┘ │
│        │                                        │
│  ┌─────▼──────┐                                 │
│  │  Data Store│  (cache + user preferences)     │
│  └────────────┘                                 │
└─────────────────────────────────────────────────┘
         │
         ▼
   External Market
   Data Providers
   (Yahoo Finance,
    Alpha Vantage, etc.)
```

### Tech Stack

| Layer     | Technology                        | Rationale                                    |
|-----------|-----------------------------------|----------------------------------------------|
| Frontend  | React + TypeScript                | Component-based, large ecosystem             |
| Charting  | Lightweight Charts (TradingView)  | Purpose-built financial charting, free/OSS    |
| Backend   | Python (FastAPI)                  | Strong finance/data libs (pandas, ta-lib)     |
| Data      | SQLite (dev) / PostgreSQL (prod)  | Simple start, easy to scale later             |
| Cache     | Redis (optional)                  | Cache market data to avoid rate limits        |

---

## 3. Data Model

### 3.1 Stock

```
Stock
├── symbol: str          (e.g. "AAPL")
├── name: str            (e.g. "Apple Inc.")
└── exchange: str        (e.g. "NASDAQ")
```

### 3.2 OHLCV (candlestick data)

```
OHLCV
├── symbol: str
├── timestamp: datetime
├── open: float
├── high: float
├── low: float
├── close: float
└── volume: int
```

### 3.3 Indicator Method (extensible registry)

```
IndicatorMethod
├── id: str              (e.g. "ma", "macd", "kdj")
├── display_name: str    (e.g. "Moving Average")
├── category: str        (e.g. "trend", "momentum", "volume")
├── default_params: dict (e.g. {"period": 20})
└── description: str
```

### 3.4 User Stock Config (per stock, per user)

```
StockAnalysisConfig
├── symbol: str
├── selected_methods: list[str]        (which indicators are active)
├── method_weights: dict[str, float]   (weight for decision matrix)
└── method_params: dict[str, dict]     (override default params)
```

---

## 4. Core Features

### 4.1 Candlestick Chart

- **Time ranges**: 1D, 5D, 1M, 3M, 6M, YTD, 1Y, 5Y, Max
- **Intervals**: 1min, 5min, 15min, 1hr, 1day, 1week (depending on range)
- Interactive zoom, pan, crosshair with OHLCV tooltip
- Volume bars below the price chart

### 4.2 Technical Analysis Indicators

Indicators are rendered as overlays on the price chart or in sub-panels below it.

#### Built-in Indicators (Phase 1)

| Indicator | Type     | Default Params               | Chart Position |
|-----------|----------|------------------------------|----------------|
| MA        | Trend    | periods: [5, 10, 20, 60]    | Overlay        |
| EMA       | Trend    | periods: [12, 26]            | Overlay        |
| MACD      | Momentum | fast=12, slow=26, signal=9   | Sub-panel      |
| KDJ       | Momentum | period=9, k=3, d=3           | Sub-panel      |
| RSI       | Momentum | period=14                    | Sub-panel      |
| Bollinger | Volatil. | period=20, std_dev=2         | Overlay        |

#### Adding New Methods (Extensibility)

New indicators are added by implementing a simple interface:

```python
class Indicator(ABC):
    """Base class for all technical indicators."""

    id: str
    display_name: str
    category: str  # "trend" | "momentum" | "volume" | "volatility"
    default_params: dict
    chart_position: str  # "overlay" | "sub_panel"

    @abstractmethod
    def compute(self, ohlcv: pd.DataFrame, params: dict) -> pd.DataFrame:
        """
        Given OHLCV data and params, return a DataFrame with
        computed indicator columns.
        """
        ...

    @abstractmethod
    def signal(self, result: pd.DataFrame) -> Signal:
        """
        Interpret the computed values into a signal:
        returns Signal with value in [-1.0, +1.0]
          -1.0 = strong sell
           0.0 = neutral
          +1.0 = strong buy
        """
        ...
```

New methods are **registered** in a central registry:

```python
# indicators/registry.py
INDICATOR_REGISTRY: dict[str, type[Indicator]] = {}

def register(cls: type[Indicator]):
    INDICATOR_REGISTRY[cls.id] = cls
    return cls
```

```python
# indicators/ma.py
@register
class MovingAverage(Indicator):
    id = "ma"
    display_name = "Moving Average"
    ...
```

This means adding a new method from a book is:
1. Create a new file `indicators/new_method.py`
2. Implement `compute()` and `signal()`
3. Decorate with `@register`
4. It automatically appears in the UI

### 4.3 Weighted Decision Matrix

For each stock, the user selects N indicators and assigns a weight to each. The system computes a composite score.

#### How It Works

```
For stock AAPL, user selects:
  MA(20)   — weight 0.3
  MACD     — weight 0.3
  KDJ      — weight 0.2
  RSI(14)  — weight 0.2
                     ─────
                 sum = 1.0

Each indicator produces a signal ∈ [-1.0, +1.0]

Composite Score = Σ (weight_i × signal_i)

Decision:
  score >  0.3  →  BUY
  score < -0.3  →  SELL
  otherwise     →  HOLD

(Thresholds are configurable)
```

#### UI for Decision Matrix

```
┌──────────────────────────────────────────────────┐
│  AAPL — Decision Matrix                          │
├────────────┬────────┬────────┬───────────────────┤
│ Indicator  │ Weight │ Signal │ Weighted Score    │
├────────────┼────────┼────────┼───────────────────┤
│ MA(20)     │  0.30  │ +0.60  │  +0.18           │
│ MACD       │  0.30  │ +0.80  │  +0.24           │
│ KDJ        │  0.20  │ -0.20  │  -0.04           │
│ RSI(14)    │  0.20  │ +0.40  │  +0.08           │
├────────────┼────────┼────────┼───────────────────┤
│ TOTAL      │  1.00  │        │  +0.46  → BUY    │
└────────────┴────────┴────────┴───────────────────┘
```

---

## 5. API Design

### 5.1 Market Data

```
GET /api/stocks/{symbol}/ohlcv?range=1M&interval=1d
  → { candles: [ {t, o, h, l, c, v}, ... ] }
```

### 5.2 Indicators

```
GET /api/indicators
  → [ { id, display_name, category, default_params, chart_position }, ... ]

GET /api/stocks/{symbol}/indicators/{indicator_id}?range=1M&interval=1d&params=...
  → { indicator_id, data: [ {t, values...}, ... ], signal: {value, label} }
```

### 5.3 Decision Matrix

```
POST /api/stocks/{symbol}/decision
  Body: {
    methods: [
      { id: "ma",   weight: 0.3, params: { period: 20 } },
      { id: "macd", weight: 0.3 },
      { id: "kdj",  weight: 0.2 },
      { id: "rsi",  weight: 0.2, params: { period: 14 } }
    ],
    range: "3M",
    interval: "1d"
  }
  → {
      symbol: "AAPL",
      results: [
        { id: "ma",   signal: 0.60, weight: 0.3, weighted: 0.18 },
        { id: "macd", signal: 0.80, weight: 0.3, weighted: 0.24 },
        ...
      ],
      composite_score: 0.46,
      decision: "BUY"
    }
```

### 5.4 User Config

```
GET  /api/config/{symbol}         → saved analysis config
PUT  /api/config/{symbol}         → save/update config
GET  /api/config                  → list all configured stocks
```

---

## 6. Frontend Pages

### 6.1 Dashboard (`/`)

- Search / add stocks to watchlist
- Watchlist table showing: symbol, price, change%, mini sparkline, current decision

### 6.2 Stock Detail (`/stock/:symbol`)

- **Top**: Candlestick chart with overlay indicators
- **Middle**: Sub-panel indicators (MACD, KDJ, RSI, etc.)
- **Right sidebar**: Indicator selector (checkboxes to toggle on/off)
- **Bottom**: Decision matrix table with weight sliders

### 6.3 Layout

```
┌──────────────────────────────────────────────────────┐
│  Navbar:  [Logo]  [Search...]           [Watchlist]  │
├──────────────────────────────────────┬───────────────┤
│                                      │  Indicators   │
│     Candlestick Chart                │  ☑ MA(20)     │
│     + overlay indicators             │  ☑ EMA(12,26) │
│                                      │  ☑ Bollinger  │
│                                      │  ☐ VWAP       │
├──────────────────────────────────────┤  ☑ MACD       │
│     MACD sub-panel                   │  ☑ KDJ        │
├──────────────────────────────────────┤  ☑ RSI        │
│     KDJ sub-panel                    │  ☐ OBV        │
├──────────────────────────────────────┤               │
│     RSI sub-panel                    │  [+ Add New]  │
├──────────────────────────────────────┴───────────────┤
│  Decision Matrix                                     │
│  ┌────────────┬────────┬────────┬──────────────────┐ │
│  │ Indicator  │ Weight │ Signal │ Weighted Score   │ │
│  │ MA(20)     │ ===●== │ +0.60  │ +0.18           │ │
│  │ MACD       │ ===●== │ +0.80  │ +0.24           │ │
│  │ KDJ        │ =●==== │ -0.20  │ -0.04           │ │
│  │ RSI        │ ==●=== │ +0.40  │ +0.08           │ │
│  ├────────────┴────────┴────────┼──────────────────┤ │
│  │                    TOTAL     │ +0.46  →  BUY    │ │
│  └──────────────────────────────┴──────────────────┘ │
└──────────────────────────────────────────────────────┘
```

---

## 7. Project Structure

```
trading/
├── DESIGN.md
├── backend/
│   ├── pyproject.toml
│   ├── app/
│   │   ├── main.py                 # FastAPI app entry
│   │   ├── config.py               # App config
│   │   ├── models/
│   │   │   ├── stock.py            # Stock, OHLCV models
│   │   │   └── config.py           # User analysis config
│   │   ├── routers/
│   │   │   ├── stocks.py           # /api/stocks/...
│   │   │   ├── indicators.py       # /api/indicators/...
│   │   │   ├── decision.py         # /api/stocks/{symbol}/decision
│   │   │   └── config.py           # /api/config/...
│   │   ├── services/
│   │   │   ├── market_data.py      # Fetch OHLCV from providers
│   │   │   ├── indicator_engine.py # Run indicators, produce signals
│   │   │   └── decision_engine.py  # Weighted matrix computation
│   │   └── indicators/
│   │       ├── __init__.py
│   │       ├── base.py             # Indicator ABC + Signal model
│   │       ├── registry.py         # Auto-discovery registry
│   │       ├── ma.py               # Moving Average
│   │       ├── ema.py              # Exponential MA
│   │       ├── macd.py             # MACD
│   │       ├── kdj.py              # KDJ Stochastic
│   │       ├── rsi.py              # RSI
│   │       └── bollinger.py        # Bollinger Bands
│   └── tests/
├── frontend/
│   ├── package.json
│   ├── src/
│   │   ├── App.tsx
│   │   ├── pages/
│   │   │   ├── Dashboard.tsx
│   │   │   └── StockDetail.tsx
│   │   ├── components/
│   │   │   ├── CandlestickChart.tsx
│   │   │   ├── IndicatorPanel.tsx
│   │   │   ├── IndicatorSelector.tsx
│   │   │   ├── DecisionMatrix.tsx
│   │   │   └── Watchlist.tsx
│   │   ├── services/
│   │   │   └── api.ts              # API client
│   │   └── types/
│   │       └── index.ts            # TypeScript interfaces
│   └── public/
└── docker-compose.yml              # (optional) for deployment
```

---

## 8. Implementation Phases

### Phase 1 — Core (MVP)

- [ ] Backend: FastAPI skeleton with market data service (Yahoo Finance via `yfinance`)
- [ ] Backend: Indicator engine with MA, MACD, KDJ
- [ ] Backend: Decision engine with weighted matrix
- [ ] Frontend: Candlestick chart with range selector
- [ ] Frontend: Indicator overlays and sub-panels
- [ ] Frontend: Decision matrix UI with weight sliders

### Phase 2 — Expand

- [ ] Add more indicators: RSI, Bollinger, EMA, VWAP, OBV
- [ ] Watchlist / dashboard page
- [ ] Save/load user configs (selected indicators + weights per stock)
- [ ] Indicator parameter customization UI

### Phase 3 — Polish & Extend

- [ ] Real-time data via WebSocket (optional paid data source)
- [ ] Comparison mode (overlay multiple stocks)
- [ ] Backtest: run decision matrix against historical data, show accuracy
- [ ] Mobile-responsive layout
- [ ] User accounts & persistence (PostgreSQL)
- [ ] "Book mode" — annotated indicator pages explaining the theory

---

## 9. Adding a New Indicator (Guide)

When reading a book and finding a new technical analysis method:

1. **Create** `backend/app/indicators/your_method.py`
2. **Implement** the `Indicator` interface:

```python
from .base import Indicator, Signal
from .registry import register

@register
class YourMethod(Indicator):
    id = "your_method"
    display_name = "Your Method Name"
    category = "momentum"  # or trend, volatility, volume
    default_params = {"period": 14}
    chart_position = "sub_panel"  # or "overlay"

    def compute(self, ohlcv, params):
        # Your calculation logic using pandas
        ...
        return result_df

    def signal(self, result):
        # Interpret into -1.0 to +1.0
        ...
        return Signal(value=0.5, label="Bullish")
```

3. **Done.** The registry auto-discovers it. The API and frontend will list it automatically.

---

## 10. Key Design Decisions

| Decision | Choice | Why |
|----------|--------|-----|
| Chart lib | Lightweight Charts | Free, fast, built for finance, TradingView quality |
| Signal range | [-1, +1] float | Unified scale makes weighted sum straightforward |
| Indicator as plugin | ABC + registry | New methods need zero changes to existing code |
| Separate signal() | Per-indicator | Each method has its own interpretation logic |
| Weight normalization | User must sum to 1.0 (UI enforces) | Keeps scoring transparent and simple |
| Backend language | Python | Best ecosystem for financial data (pandas, numpy, ta-lib, yfinance) |
