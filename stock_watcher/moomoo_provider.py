from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, time
from typing import Iterable
from zoneinfo import ZoneInfo

from .config import MoomooConfig, Position


@dataclass(frozen=True)
class Quote:
    code: str
    symbol: str
    name: str
    price: float
    quote_time: str
    session: str


class MoomooQuoteProvider:
    def __init__(self, config: MoomooConfig) -> None:
        try:
            from moomoo import OpenQuoteContext, RET_OK, Session, SubType
        except ImportError as exc:
            raise RuntimeError(
                "Missing moomoo-api. Install it with: python -m pip install -r requirements.txt"
            ) from exc

        self._OpenQuoteContext = OpenQuoteContext
        self._RET_OK = RET_OK
        self._Session = Session
        self._SubType = SubType
        self._ctx = OpenQuoteContext(host=config.host, port=config.port)

    def subscribe(self, positions: Iterable[Position]) -> None:
        codes = [position.moomoo_code for position in positions]
        if not codes:
            raise RuntimeError("No enabled positions to watch.")

        kwargs = {"subscribe_push": False}
        if hasattr(self._Session, "ALL"):
            kwargs["session"] = self._Session.ALL

        ret, data = self._ctx.subscribe(codes, [self._SubType.QUOTE], **kwargs)
        if ret != self._RET_OK:
            raise RuntimeError(f"Moomoo subscribe failed: {data}")

    def fetch_quotes(self, positions: Iterable[Position]) -> list[Quote]:
        by_code = {position.moomoo_code: position for position in positions}
        ret, data = self._ctx.get_stock_quote(list(by_code.keys()))
        if ret != self._RET_OK:
            raise RuntimeError(f"Moomoo quote request failed: {data}")

        rows = data.to_dict("records")
        quotes: list[Quote] = []
        for row in rows:
            code = str(row.get("code", "")).upper()
            position = by_code.get(code)
            if not position:
                continue
            price = self._pick_price(row)
            if price is None or price <= 0:
                continue
            quotes.append(
                Quote(
                    code=code,
                    symbol=position.symbol,
                    name=position.name,
                    price=price,
                    quote_time=str(row.get("data_time") or row.get("update_time") or ""),
                    session=self._pick_session(row),
                )
            )
        return quotes

    def close(self) -> None:
        self._ctx.close()

    @staticmethod
    def _pick_price(row: dict) -> float | None:
        for field in ("last_price", "overnight_price", "after_price", "pre_price"):
            value = row.get(field)
            try:
                price = float(value)
            except (TypeError, ValueError):
                continue
            if price > 0:
                return price
        return None

    @staticmethod
    def _pick_session(row: dict) -> str:
        return MoomooQuoteProvider._session_from_eastern_time(datetime.now(ZoneInfo("America/New_York")))

    @staticmethod
    def _session_from_eastern_time(now: datetime) -> str:
        current = now.time()
        if time(4, 0) <= current < time(9, 30):
            return "pre-market"
        if time(9, 30) <= current < time(16, 0):
            return "regular"
        if time(16, 0) <= current < time(20, 0):
            return "after-hours"
        return "overnight"
