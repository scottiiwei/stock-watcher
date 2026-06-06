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
class AlertWindow:
    minutes: float
    ladder: tuple[float, ...]
    reset_percent: float

    @property
    def rule_id(self) -> str:
        return f"{self.minutes:g}m"

    @property
    def label(self) -> str:
        return f"{self.minutes:g}分钟"


@dataclass(frozen=True)
class WatcherConfig:
    positions_file: Path
    state_file: Path
    price_window_minutes: float
    poll_seconds: float
    send_startup_message: bool
    alert_rules: tuple[AlertRule, ...]
    alert_ladder: tuple[float, ...]
    ladder_reset_percent: float
    ladder_cooldown_seconds: float
    symbol_direction_cooldown_seconds: float
    alert_windows: tuple[AlertWindow, ...]
    opening_summary_enabled: bool
    opening_summary_threshold_percent: float
    opening_summary_window_minutes: float


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
            price_window_minutes=float(os.getenv("PRICE_WINDOW_MINUTES", "3")),
            poll_seconds=float(os.getenv("POLL_SECONDS", "10")),
            send_startup_message=env_bool("SEND_STARTUP_MESSAGE", True),
            alert_rules=load_alert_rules(),
            alert_ladder=load_alert_ladder(),
            ladder_reset_percent=float(os.getenv("LADDER_RESET_PERCENT", "0.7")),
            ladder_cooldown_seconds=float(os.getenv("LADDER_COOLDOWN_SECONDS", "60")),
            symbol_direction_cooldown_seconds=float(os.getenv("SYMBOL_DIRECTION_COOLDOWN_SECONDS", "180")),
            alert_windows=load_alert_windows(),
            opening_summary_enabled=env_bool("OPENING_SUMMARY_ENABLED", True),
            opening_summary_threshold_percent=float(os.getenv("OPENING_SUMMARY_THRESHOLD_PERCENT", "3")),
            opening_summary_window_minutes=float(os.getenv("OPENING_SUMMARY_WINDOW_MINUTES", "15")),
        ),
    )


def load_alert_ladder() -> tuple[float, ...]:
    raw = os.getenv("ALERT_LADDER", "1,1.5,2,2.5").strip()
    levels = sorted({float(item.strip()) for item in raw.split(",") if item.strip()})
    if not levels:
        raise RuntimeError("ALERT_LADDER must contain at least one threshold.")
    return tuple(levels)


def load_alert_windows() -> tuple[AlertWindow, ...]:
    raw = os.getenv(
        "ALERT_WINDOWS",
        "3:0.8|1.2|1.8:0.5,5:1|1.5|2|2.5:0.7,10:1.5|2.5|3.5:1.0",
    ).strip()
    windows: list[AlertWindow] = []
    for item in raw.split(","):
        if not item.strip():
            continue
        parts = [part.strip() for part in item.split(":")]
        if len(parts) != 3:
            raise RuntimeError(
                "ALERT_WINDOWS must use format: minutes:level|level|level:reset_percent"
            )
        minutes, ladder_raw, reset_percent = parts
        ladder = sorted({float(level.strip()) for level in ladder_raw.split("|") if level.strip()})
        if not ladder:
            raise RuntimeError("Each ALERT_WINDOWS item must contain at least one threshold.")
        windows.append(
            AlertWindow(
                minutes=float(minutes),
                ladder=tuple(ladder),
                reset_percent=float(reset_percent),
            )
        )
    if not windows:
        raise RuntimeError("ALERT_WINDOWS must contain at least one window.")
    return tuple(sorted(windows, key=lambda window: window.minutes))


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
