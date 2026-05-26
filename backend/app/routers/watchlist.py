from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession
from ..database import get_db
from ..models.user import User
from ..models.watchlist import WatchlistItem
from ..services.auth import get_current_user
from ..services.market_data import ensure_stock

router = APIRouter(prefix="/api/watchlist", tags=["watchlist"])


class AddStockRequest(BaseModel):
    symbol: str


class UpdateWeightsRequest(BaseModel):
    selected_methods: list[str] | None = None
    method_weights: dict[str, float] | None = None
    method_params: dict[str, dict] | None = None
    notify_enabled: bool | None = None
    notify_buy: bool | None = None
    notify_sell: bool | None = None


@router.get("")
async def get_watchlist(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(WatchlistItem).where(WatchlistItem.user_id == user.id)
    )
    items = result.scalars().all()
    return {
        "items": [{
            "id": item.id,
            "symbol": item.symbol,
            "selected_methods": item.selected_methods,
            "method_weights": item.method_weights,
            "notify_enabled": item.notify_enabled,
            "added_at": str(item.added_at),
        } for item in items]
    }


@router.post("")
async def add_stock(
    req: AddStockRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    symbol = req.symbol.upper()
    await ensure_stock(db, symbol)

    existing = await db.execute(
        select(WatchlistItem).where(
            WatchlistItem.user_id == user.id,
            WatchlistItem.symbol == symbol,
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Stock already in watchlist")

    item = WatchlistItem(user_id=user.id, symbol=symbol)
    db.add(item)
    await db.commit()
    await db.refresh(item)

    return {"id": item.id, "symbol": item.symbol, "message": "Added to watchlist"}


@router.put("/{item_id}")
async def update_watchlist_item(
    item_id: int,
    req: UpdateWeightsRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(WatchlistItem).where(
            WatchlistItem.id == item_id,
            WatchlistItem.user_id == user.id,
        )
    )
    item = result.scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=404, detail="Watchlist item not found")

    if req.selected_methods is not None:
        item.selected_methods = req.selected_methods
    if req.method_weights is not None:
        item.method_weights = req.method_weights
    if req.method_params is not None:
        item.method_params = req.method_params
    if req.notify_enabled is not None:
        item.notify_enabled = req.notify_enabled
    if req.notify_buy is not None:
        item.notify_buy = req.notify_buy
    if req.notify_sell is not None:
        item.notify_sell = req.notify_sell

    await db.commit()
    return {"message": "Updated"}


@router.delete("/{item_id}")
async def remove_stock(
    item_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(WatchlistItem).where(
            WatchlistItem.id == item_id,
            WatchlistItem.user_id == user.id,
        )
    )
    item = result.scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=404, detail="Watchlist item not found")

    await db.delete(item)
    await db.commit()
    return {"message": "Removed from watchlist"}
