from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import date, timedelta
from ..database import get_db
from ..services.market_data import get_ohlcv, ensure_stock, fetch_ohlcv_from_provider, save_ohlcv
from ..services.signal_engine import compute_swing_structure, compute_all_indicators
from ..services.decision_engine import compute_decision
from ..services.auth import get_current_user
from ..models.user import User
from ..signals.registry import get_method

router = APIRouter(prefix="/api/decision", tags=["decision"])


class MethodConfig(BaseModel):
    id: str
    weight: float = 0.25
    params: dict | None = None


class DecisionRequest(BaseModel):
    methods: list[MethodConfig]
    range: str = "1Y"


@router.post("/{symbol}")
async def get_decision(
    symbol: str,
    req: DecisionRequest,
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    symbol = symbol.upper()
    range_days = {"1M": 30, "3M": 90, "6M": 180, "1Y": 365, "5Y": 1825, "Max": 3650}
    days = range_days.get(req.range, 365)
    start = date.today() - timedelta(days=max(days, 365))

    await ensure_stock(db, symbol)
    df = await get_ohlcv(db, symbol, start_date=start)
    if df.empty:
        provider_df = await fetch_ohlcv_from_provider(symbol, period="5y")
        if not provider_df.empty:
            await save_ohlcv(db, provider_df)
        df = await get_ohlcv(db, symbol, start_date=start)

    if df.empty:
        return {"symbol": symbol, "error": "No data available"}

    result_df, _ = compute_swing_structure(df)
    swing_method = get_method("swing_structure")
    primary_signal = swing_method.signal(result_df)

    method_ids = [m.id for m in req.methods if m.id != "swing_structure"]
    method_params = {m.id: m.params for m in req.methods if m.params}
    weights = {m.id: m.weight for m in req.methods if m.id != "swing_structure"}

    indicator_signals = compute_all_indicators(df, method_ids, method_params)
    result = compute_decision(symbol, primary_signal, indicator_signals, weights)

    primary_details = dict(result.primary_signal.details) if result.primary_signal and result.primary_signal.details else {}
    if not df.empty:
        primary_details["current_price"] = round(float(df.iloc[-1]["close"]), 2)

    return {
        "symbol": symbol,
        "primary": {
            "active": result.primary_active,
            "signal": result.primary_signal.value if result.primary_signal else 0,
            "label": result.primary_signal.label if result.primary_signal else "N/A",
            "details": primary_details,
        },
        "indicators": result.indicator_results,
        "composite_score": result.composite_score,
        "decision": result.decision,
    }
