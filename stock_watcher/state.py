from __future__ import annotations

import json
from pathlib import Path
import time
from typing import Any


class AlertState:
    def __init__(self, path: Path, cooldown_seconds: float | None = None) -> None:
        self.path = path
        self.cooldown_seconds = cooldown_seconds
        self._last_alert_at: dict[str, float] = {}
        self._ladder_highest: dict[str, float] = {}
        self._opening_summary_dates: dict[str, bool] = {}
        self.load()

    def load(self) -> None:
        if not self.path.exists():
            return
        raw = json.loads(self.path.read_text(encoding="utf-8"))
        alerts = raw.get("last_alert_at", {}) if isinstance(raw, dict) else {}
        if isinstance(alerts, dict):
            self._last_alert_at = {str(key): float(value) for key, value in alerts.items()}
        ladder = raw.get("ladder_highest", {}) if isinstance(raw, dict) else {}
        if isinstance(ladder, dict):
            self._ladder_highest = {str(key): float(value) for key, value in ladder.items()}
        opening = raw.get("opening_summary_dates", {}) if isinstance(raw, dict) else {}
        if isinstance(opening, dict):
            self._opening_summary_dates = {str(key): bool(value) for key, value in opening.items()}

    def save(self) -> None:
        payload: dict[str, Any] = {
            "last_alert_at": self._last_alert_at,
            "ladder_highest": self._ladder_highest,
            "opening_summary_dates": self._opening_summary_dates,
        }
        self.path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    def should_alert(
        self,
        symbol: str,
        direction: str,
        now: float | None = None,
        rule_id: str = "default",
        cooldown_seconds: float | None = None,
    ) -> bool:
        current_time = now if now is not None else time.time()
        cooldown = cooldown_seconds if cooldown_seconds is not None else self.cooldown_seconds
        if cooldown is None:
            raise RuntimeError("Missing alert cooldown.")
        key = f"{rule_id}:{symbol}:{direction}"
        last_time = self._last_alert_at.get(key, 0)
        return current_time - last_time >= cooldown

    def mark_alerted(
        self,
        symbol: str,
        direction: str,
        now: float | None = None,
        rule_id: str = "default",
    ) -> None:
        current_time = now if now is not None else time.time()
        self._last_alert_at[f"{rule_id}:{symbol}:{direction}"] = current_time
        self.save()

    def ladder_highest(self, symbol: str, direction: str, window_id: str = "default") -> float:
        return self._ladder_highest.get(self._ladder_state_key(symbol, direction, window_id), 0.0)

    def mark_ladder_alerted(
        self,
        symbol: str,
        direction: str,
        level: float,
        window_id: str = "default",
        now: float | None = None,
    ) -> None:
        current_time = now if now is not None else time.time()
        level_key = self._format_level(level)
        self._last_alert_at[f"ladder:{window_id}:{symbol}:{direction}:{level_key}"] = current_time
        state_key = self._ladder_state_key(symbol, direction, window_id)
        self._ladder_highest[state_key] = max(level, self._ladder_highest.get(state_key, 0.0))
        self.save()

    def should_ladder_alert(
        self,
        symbol: str,
        direction: str,
        level: float,
        cooldown_seconds: float,
        window_id: str = "default",
        now: float | None = None,
    ) -> bool:
        current_time = now if now is not None else time.time()
        level_key = self._format_level(level)
        last_time = self._last_alert_at.get(f"ladder:{window_id}:{symbol}:{direction}:{level_key}", 0)
        return current_time - last_time >= cooldown_seconds

    def reset_ladder(self, symbol: str, direction: str, window_id: str = "default") -> None:
        key = self._ladder_state_key(symbol, direction, window_id)
        if key in self._ladder_highest:
            self._ladder_highest.pop(key, None)
            self.save()

    def opening_summary_sent(self, date_key: str) -> bool:
        return self._opening_summary_dates.get(date_key, False)

    def mark_opening_summary_sent(self, date_key: str) -> None:
        self._opening_summary_dates[date_key] = True
        self.save()

    @staticmethod
    def _format_level(level: float) -> str:
        return f"{level:g}"

    @staticmethod
    def _ladder_state_key(symbol: str, direction: str, window_id: str) -> str:
        return f"{window_id}:{symbol}:{direction}"
