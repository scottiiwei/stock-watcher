from __future__ import annotations

from collections import defaultdict, deque
from dataclasses import dataclass
import time


@dataclass(frozen=True)
class PricePoint:
    timestamp: float
    price: float


@dataclass(frozen=True)
class PriceMove:
    symbol: str
    old_price: float
    new_price: float
    change_percent: float
    window_seconds: float

    @property
    def direction(self) -> str:
        return "up" if self.change_percent >= 0 else "down"


class PriceWindow:
    def __init__(self, window_seconds: float) -> None:
        self.window_seconds = window_seconds
        self._points: dict[str, deque[PricePoint]] = defaultdict(deque)

    def add(self, symbol: str, price: float, timestamp: float | None = None) -> PriceMove | None:
        now = timestamp if timestamp is not None else time.time()
        points = self._points[symbol]
        points.append(PricePoint(now, price))

        cutoff = now - self.window_seconds
        while len(points) > 1 and points[0].timestamp < cutoff:
            points.popleft()

        if len(points) < 2:
            return None

        oldest = points[0]
        if oldest.price <= 0:
            return None

        change_percent = (price - oldest.price) / oldest.price * 100
        return PriceMove(
            symbol=symbol,
            old_price=oldest.price,
            new_price=price,
            change_percent=change_percent,
            window_seconds=now - oldest.timestamp,
        )
