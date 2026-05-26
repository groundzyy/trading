from .base import SignalMethod

SIGNAL_REGISTRY: dict[str, type[SignalMethod]] = {}


def register(cls: type[SignalMethod]) -> type[SignalMethod]:
    SIGNAL_REGISTRY[cls.id] = cls
    return cls


def get_method(method_id: str) -> SignalMethod:
    cls = SIGNAL_REGISTRY[method_id]
    return cls()


def list_methods() -> list[dict]:
    result = []
    for method_id, cls in SIGNAL_REGISTRY.items():
        result.append({
            "id": cls.id,
            "name": cls.name,
            "category": cls.category,
            "chart_position": cls.chart_position,
            "default_params": cls.default_params,
        })
    return result
