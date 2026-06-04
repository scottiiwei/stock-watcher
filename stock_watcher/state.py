from __future__ import annotations

import json
from pathlib import Path
import time


class AlertState:
    def __init__(self, path: Path, cooldown_seconds: float | None = None) -> None:
        self.path = path
        self.cooldown_seconds = cooldown_seconds
        self._last_alert_at: dict[str, float] = {}
        self.load()

    def load(self) -> None:
        if not self.path.exists():
            return
        raw = json.loads(self.path.read_text(encoding="utf-8"))
        alerts = raw.get("last_alert_at", {}) if isinstance(raw, dict) else {}
        if isinstance(alerts, dict):
            self._last_alert_at = {str(key): float(value) for key, value in alerts.items()}

    def save(self) -> None:
        payload = {"last_alert_at": self._last_alert_at}
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
