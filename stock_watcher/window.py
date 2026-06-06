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
    reference_timestamp: float
    current_timestamp: float
    reference_label: str
    direction_value: str = ""

    @property
    def direction(self) -> str:
        if self.direction_value:
            return self.direction_value
        return "up" if self.change_percent >= 0 else "down"


class PriceWindow:
    def __init__(self, window_seconds: float) -> None:
        self.window_seconds = window_seconds
        self._points: dict[str, deque[PricePoint]] = defaultdict(deque)
        self._first_seen_at: dict[str, float] = {}

    def add(self, symbol: str, price: float, timestamp: float | None = None) -> tuple[PriceMove, ...]:
        now = timestamp if timestamp is not None else time.time()
        self._first_seen_at.setdefault(symbol, now)
        points = self._points[symbol]
        points.append(PricePoint(now, price))

        cutoff = now - self.window_seconds
        while len(points) > 1 and points[0].timestamp < cutoff:
            points.popleft()

        if len(points) < 2:
            return ()

        if now - self._first_seen_at[symbol] < self.window_seconds:
            return ()

        lowest = min(points, key=lambda point: point.price)
        highest = max(points, key=lambda point: point.price)
        moves: list[PriceMove] = []

        if lowest.price > 0:
            moves.append(
                PriceMove(
                    symbol=symbol,
                    old_price=lowest.price,
                    new_price=price,
                    change_percent=(price - lowest.price) / lowest.price * 100,
                    window_seconds=now - lowest.timestamp,
                    reference_timestamp=lowest.timestamp,
                    current_timestamp=now,
                    reference_label="低点",
                    direction_value="up",
                )
            )

        if highest.price > 0:
            moves.append(
                PriceMove(
                    symbol=symbol,
                    old_price=highest.price,
                    new_price=price,
                    change_percent=(price - highest.price) / highest.price * 100,
                    window_seconds=now - highest.timestamp,
                    reference_timestamp=highest.timestamp,
                    current_timestamp=now,
                    reference_label="高点",
                    direction_value="down",
                )
            )

        return tuple(moves)

    def has_history(self, symbol: str) -> bool:
        return len(self._points.get(symbol, ())) > 1
