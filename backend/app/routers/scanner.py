from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import date, timedelta
from ..database import get_db
from ..models.signal import SignalResult
from ..services.auth import get_current_user
from ..models.user import User

router = APIRouter(prefix="/api/scanner", tags=["scanner"])


@router.get("")
async def scan_signals(
    signal_type: str = Query(None, enum=["BUY", "SELL"]),
    days: int = Query(3, ge=1, le=30),
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    start = date.today() - timedelta(days=days)
    stmt = select(SignalResult).where(SignalResult.date >= start)

    if signal_type:
        stmt = stmt.where(SignalResult.signal_type == signal_type)

    stmt = stmt.order_by(SignalResult.date.desc()).limit(limit)
    result = await db.execute(stmt)
    rows = result.scalars().all()

    return {
        "signals": [{
            "symbol": r.symbol,
            "date": str(r.date),
            "signal_type": r.signal_type,
            "primary_trigger": r.primary_trigger,
            "trigger_price": r.trigger_price,
            "composite_score": r.composite_score,
            "indicator_scores": r.indicator_scores,
        } for r in rows]
    }
