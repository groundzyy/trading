# TradingSignal

Multi-user stock trading signal app. Larry Williams swing structure detection as the
primary gate, combined with MACD / RSI / KDJ / MA / volume and an optional LLM
sentiment read through a weighted decision matrix.

## Run it

```bash
docker compose up --build
```

- App: <http://localhost:3001>
- API docs: <http://localhost:8000/docs>

Register an account on first load. Market data comes from yfinance and needs no key.

Port 3001 is the default to stay clear of the crowded 3000. Override with
`FRONTEND_PORT=3005 docker compose up`.

## AI sentiment (optional)

The sentiment panel stays dark until a key is set:

```bash
export TRADING_ANTHROPIC_API_KEY=sk-ant-...
docker compose up --build
```

Without it the panel reads "no analysis" and `POST /api/sentiment/{symbol}/analyze`
returns 503 — nothing crashes, and the decision matrix renormalizes the remaining
weights. Analyses are cached per symbol per day; a nightly Celery task refreshes
watchlisted symbols at 01:00 with the cheap batch model, and the scanner runs at
02:00 so it reads a warm cache.

## Run without Docker

Three terminals:

```bash
# 1. infrastructure
docker compose up db redis

# 2. backend
cd backend
pip install -e ".[dev]"
TRADING_SECRET_KEY=dev-secret uvicorn app.main:app --reload

# 3. frontend
cd frontend
npm install
npm run dev          # http://localhost:3000, proxies /api to :8000
```

Tables are created on backend startup; no migration step.

If you install the backend outside this project's pin, make sure you end up with
`bcrypt<5`. passlib 1.7.4 cannot drive bcrypt 5.x — every login fails with a
misleading "password cannot be longer than 72 bytes".

## Tests

```bash
cd backend && python3 -m pytest -q
```

## Layout

```
backend/
  app/signals/      indicator plugins, self-registering via @register
  app/services/     decision engine, LLM sentiment, data providers
  app/routers/      FastAPI routes
  app/tasks/        Celery beat schedule: sentiment batch + daily scan
frontend/
  src/pages/        Dashboard, StockDetail, Scanner, Login
  src/components/   CandlestickChart, DecisionMatrix, SentimentPanel
```

Adding an indicator means dropping a `SignalMethod` subclass into `app/signals/`
with the `@register` decorator and importing it in `services/signal_engine.py`; it
then appears in `/api/signals/methods` and can be weighted in the matrix.

See `DESIGN.md` for the signal model and decision logic.
