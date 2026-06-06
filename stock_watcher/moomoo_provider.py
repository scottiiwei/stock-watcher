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
    open_price: float | None = None
    prev_close_price: float | None = None


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
        eastern_now = datetime.now(ZoneInfo("America/New_York"))
        for row in rows:
            code = str(row.get("code", "")).upper()
            position = by_code.get(code)
            if not position:
                continue
            session = self._session_from_eastern_time(eastern_now)
            if session == "closed":
                continue
            price = self._pick_price(row, session)
            if price is None or price <= 0:
                continue
            quotes.append(
                Quote(
                    code=code,
                    symbol=position.symbol,
                    name=position.name,
                    price=price,
                    quote_time=self._pick_quote_time(row, session, eastern_now),
                    session=session,
                    open_price=self._pick_optional_price(row, "open_price"),
                    prev_close_price=self._pick_optional_price(row, "prev_close_price"),
                )
            )
        return quotes

    def close(self) -> None:
        self._ctx.close()

    @staticmethod
    def _pick_price(row: dict, session: str) -> float | None:
        preferred_fields = {
            "pre-market": ("pre_price", "last_price"),
            "regular": ("last_price",),
            "after-hours": ("after_price", "last_price"),
            "overnight": ("overnight_price", "last_price"),
        }
        for field in preferred_fields.get(session, ("last_price",)):
            value = row.get(field)
            try:
                price = float(value)
            except (TypeError, ValueError):
                continue
            if price > 0:
                return price
        return None

    @staticmethod
    def _pick_optional_price(row: dict, field: str) -> float | None:
        try:
            price = float(row.get(field))
        except (TypeError, ValueError):
            return None
        return price if price > 0 else None

    @staticmethod
    def _pick_quote_time(row: dict, session: str, eastern_now: datetime) -> str:
        if session == "regular":
            return str(row.get("data_time") or row.get("update_time") or "")
        return eastern_now.strftime("%H:%M:%S")

    @staticmethod
    def _pick_session(row: dict) -> str:
        return MoomooQuoteProvider._session_from_eastern_time(datetime.now(ZoneInfo("America/New_York")))

    @staticmethod
    def _session_from_eastern_time(now: datetime) -> str:
        current = now.time()
        weekday = now.weekday()

        if weekday == 5:
            return "closed"
        if weekday == 6:
            return "overnight" if current >= time(20, 0) else "closed"
        if weekday == 4 and current >= time(20, 0):
            return "closed"

        if time(4, 0) <= current < time(9, 30):
            return "pre-market"
        if time(9, 30) <= current < time(16, 0):
            return "regular"
        if time(16, 0) <= current < time(20, 0):
            return "after-hours"
        return "overnight"
