from __future__ import annotations

from dataclasses import dataclass
import json
import os
from pathlib import Path


def load_dotenv(path: str | Path = ".env") -> None:
    env_path = Path(path)
    if not env_path.exists():
        return

    for line in env_path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, value = stripped.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        os.environ.setdefault(key, value)


def env(name: str, default: str | None = None) -> str:
    value = os.getenv(name, default if default is not None else "")
    value = value.strip() if value else ""
    if not value:
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value


def env_bool(name: str, default: bool = False) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "y", "on"}


@dataclass(frozen=True)
class FeishuConfig:
    app_id: str
    app_secret: str
    receive_id_type: str
    receive_id: str


@dataclass(frozen=True)
class MoomooConfig:
    host: str
    port: int


@dataclass(frozen=True)
class AlertRule:
    rule_id: str
    label: str
    threshold_percent: float
    cooldown_minutes: float


@dataclass(frozen=True)
class WatcherConfig:
    positions_file: Path
    state_file: Path
    price_window_minutes: float
    poll_seconds: float
    send_startup_message: bool
    alert_rules: tuple[AlertRule, ...]


@dataclass(frozen=True)
class Position:
    symbol: str
    name: str
    enabled: bool = True

    @property
    def moomoo_code(self) -> str:
        symbol = self.symbol.strip().upper()
        return symbol if "." in symbol else f"US.{symbol}"


@dataclass(frozen=True)
class AppConfig:
    feishu: FeishuConfig
    moomoo: MoomooConfig
    watcher: WatcherConfig


def load_config() -> AppConfig:
    load_dotenv()
    return AppConfig(
        feishu=FeishuConfig(
            app_id=env("FEISHU_APP_ID"),
            app_secret=env("FEISHU_APP_SECRET"),
            receive_id_type=os.getenv("FEISHU_RECEIVE_ID_TYPE", "open_id").strip() or "open_id",
            receive_id=env("FEISHU_RECEIVE_ID"),
        ),
        moomoo=MoomooConfig(
            host=os.getenv("MOOMOO_OPEND_HOST", "127.0.0.1").strip() or "127.0.0.1",
            port=int(os.getenv("MOOMOO_OPEND_PORT", "11111")),
        ),
        watcher=WatcherConfig(
            positions_file=Path(os.getenv("POSITIONS_FILE", "positions.json")),
            state_file=Path(os.getenv("STATE_FILE", "state.json")),
            price_window_minutes=float(os.getenv("PRICE_WINDOW_MINUTES", "5")),
            poll_seconds=float(os.getenv("POLL_SECONDS", "10")),
            send_startup_message=env_bool("SEND_STARTUP_MESSAGE", True),
            alert_rules=load_alert_rules(),
        ),
    )


def load_alert_rules() -> tuple[AlertRule, ...]:
    raw = os.getenv("ALERT_RULES", "").strip()
    if not raw:
        return (
            AlertRule(
                rule_id="default",
                label="异动",
                threshold_percent=float(os.getenv("PRICE_THRESHOLD_PERCENT", "1")),
                cooldown_minutes=float(os.getenv("ALERT_COOLDOWN_MINUTES", "10")),
            ),
        )

    labels = {
        "normal": "普通异动",
        "strong": "强异动",
    }
    rules: list[AlertRule] = []
    for item in raw.split(","):
        parts = [part.strip() for part in item.split(":")]
        if len(parts) != 3:
            raise RuntimeError(
                "ALERT_RULES must use format: rule_id:threshold_percent:cooldown_minutes"
            )
        rule_id, threshold_percent, cooldown_minutes = parts
        if not rule_id:
            raise RuntimeError("Alert rule id cannot be empty.")
        rules.append(
            AlertRule(
                rule_id=rule_id,
                label=labels.get(rule_id, rule_id),
                threshold_percent=float(threshold_percent),
                cooldown_minutes=float(cooldown_minutes),
            )
        )
    return tuple(sorted(rules, key=lambda rule: rule.threshold_percent))


def load_positions(path: Path) -> list[Position]:
    if not path.exists():
        raise RuntimeError(f"Positions file not found: {path}")

    raw = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw, list):
        raise RuntimeError("Positions file must contain a JSON array.")

    positions: list[Position] = []
    for item in raw:
        if not isinstance(item, dict):
            raise RuntimeError("Each position must be an object.")
        symbol = str(item.get("symbol", "")).strip().upper()
        if not symbol:
            raise RuntimeError("Each position requires a symbol.")
        positions.append(
            Position(
                symbol=symbol,
                name=str(item.get("name") or symbol),
                enabled=bool(item.get("enabled", True)),
            )
        )
    return [position for position in positions if position.enabled]
