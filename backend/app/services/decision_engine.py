from dataclasses import dataclass
from ..signals.base import Signal
from ..config import get_settings


@dataclass
class DecisionResult:
    symbol: str
    primary_signal: Signal | None
    indicator_results: list[dict]
    composite_score: float
    decision: str  # "BUY", "SELL", "HOLD"
    primary_active: bool


def compute_decision(
    symbol: str,
    primary_signal: Signal | None,
    indicator_signals: dict[str, Signal],
    weights: dict[str, float],
) -> DecisionResult:
    settings = get_settings()

    primary_active = primary_signal is not None and primary_signal.value != 0.0

    indicator_results = []
    total_weight = sum(weights.get(k, 0) for k in indicator_signals)

    if total_weight == 0:
        total_weight = 1.0

    composite = 0.0
    for method_id, sig in indicator_signals.items():
        w = weights.get(method_id, 0)
        normalized_weight = w / total_weight if total_weight > 0 else 0
        weighted_score = normalized_weight * sig.value
        composite += weighted_score
        indicator_results.append({
            "id": method_id,
            "signal": round(sig.value, 2),
            "label": sig.label,
            "weight": round(normalized_weight, 2),
            "weighted_score": round(weighted_score, 4),
            "details": sig.details,
        })

    composite = round(composite, 4)

    if primary_active and composite > settings.buy_threshold:
        decision = "BUY"
    elif primary_active and composite < settings.sell_threshold:
        decision = "SELL"
    elif not primary_active and composite > settings.buy_threshold * 1.5:
        decision = "BUY"
    elif not primary_active and composite < settings.sell_threshold * 1.5:
        decision = "SELL"
    else:
        decision = "HOLD"

    return DecisionResult(
        symbol=symbol,
        primary_signal=primary_signal,
        indicator_results=indicator_results,
        composite_score=composite,
        decision=decision,
        primary_active=primary_active,
    )
