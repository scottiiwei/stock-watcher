from __future__ import annotations

import argparse
from dataclasses import dataclass
from datetime import datetime, time as dt_time, timedelta, timezone
import logging
import signal
import sys
import time
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from .config import AlertWindow, load_config, load_positions
from .feishu import FeishuBot
from .moomoo_provider import MoomooQuoteProvider, Quote
from .state import AlertState
from .window import PriceMove, PriceWindow


LOG_FORMAT = "%(asctime)s %(levelname)s %(message)s"


@dataclass(frozen=True)
class AlertCandidate:
    quote: Quote
    move: PriceMove
    window: AlertWindow
    level: float


def eastern_zone():
    try:
        return ZoneInfo("America/New_York")
    except ZoneInfoNotFoundError:
        return timezone(timedelta(hours=-4), name="America/New_York")


def ladder_icon(level: float) -> str:
    if level >= 2.5:
        return "🚨"
    if level >= 2:
        return "🔥"
    if level >= 1.2:
        return "📣"
    return "⚡"


def format_eastern_timestamp(timestamp: float) -> str:
    return datetime.fromtimestamp(timestamp, eastern_zone()).strftime("%H:%M:%S")


def format_ladder_alert(quote: Quote, move: PriceMove, window: AlertWindow, level: float) -> str:
    direction = "上涨" if move.change_percent >= 0 else "下跌"
    direction_icon = "📈" if move.change_percent >= 0 else "📉"
    reference_time = format_eastern_timestamp(move.reference_timestamp)
    current_time = format_eastern_timestamp(move.current_timestamp)
    return (
        f"{ladder_icon(level)} 美股盯盘提醒｜{window.label} {level:g}% 阶梯\n"
        f"🏷️ 标的: {quote.symbol} {quote.name}\n"
        f"{direction_icon} 波动: {window.label}窗口{direction} {abs(move.change_percent):.2f}%\n"
        f"🧭 区间: {move.reference_label} {reference_time} -> 当前 {current_time}\n"
        f"💵 价格: {move.old_price:.2f} -> {move.new_price:.2f}\n"
        f"⏱️ 时段: {quote.session}\n"
        f"🕒 行情时间(美东): {quote.quote_time or 'unknown'}"
    )


def format_opening_summary(
    quotes: list[Quote],
    threshold_percent: float,
    current_time: datetime,
) -> str:
    lines = [
        "🔔 美股开盘价格快照",
        f"🕒 时间(美东): {current_time.strftime('%Y-%m-%d %H:%M:%S')}",
        "📊 开盘价 vs 昨收价",
    ]
    for quote in quotes:
        if quote.open_price is None or quote.prev_close_price is None or quote.prev_close_price <= 0:
            lines.append(f"▫️ {quote.symbol} {quote.name}: 数据暂不可用")
            continue
        change_percent = (quote.open_price - quote.prev_close_price) / quote.prev_close_price * 100
        direction = "上涨" if change_percent >= 0 else "下跌"
        marker = "🚨" if abs(change_percent) >= threshold_percent else "▫️"
        lines.append(
            f"{marker} {quote.symbol} {quote.name}: {direction} {abs(change_percent):.2f}% "
            f"({quote.prev_close_price:.2f} -> {quote.open_price:.2f})"
        )
    return "\n".join(lines)


def run_once() -> int:
    config = load_config()
    positions = load_positions(config.watcher.positions_file)
    provider = MoomooQuoteProvider(config.moomoo)
    try:
        provider.subscribe(positions)
        quotes = provider.fetch_quotes(positions)
        for quote in quotes:
            print(f"{quote.symbol} {quote.price:.4f} {quote.quote_time} {quote.session}")
        return 0
    finally:
        provider.close()


def run_watch() -> int:
    logging.basicConfig(level=logging.INFO, format=LOG_FORMAT)
    config = load_config()
    positions = load_positions(config.watcher.positions_file)
    feishu = FeishuBot(config.feishu)
    provider = MoomooQuoteProvider(config.moomoo)
    price_windows = {
        window.rule_id: PriceWindow(window.minutes * 60)
        for window in config.watcher.alert_windows
    }
    alert_state = AlertState(config.watcher.state_file)
    stop_requested = False

    def request_stop(_signum: int, _frame: object) -> None:
        nonlocal stop_requested
        stop_requested = True

    signal.signal(signal.SIGINT, request_stop)
    signal.signal(signal.SIGTERM, request_stop)

    try:
        provider.subscribe(positions)
        logging.info("Watching %s", ", ".join(position.symbol for position in positions))
        if config.watcher.send_startup_message:
            window_text = "；".join(
                f"{window.label}: {' / '.join(f'{level:g}%' for level in window.ladder)}"
                for window in config.watcher.alert_windows
            )
            reset_text = " / ".join(
                f"{window.label} {window.reset_percent:g}%"
                for window in config.watcher.alert_windows
            )
            opening_text = (
                f"\n🔔 开盘快照: 开启，超过 {config.watcher.opening_summary_threshold_percent:g}% 特别标注"
                if config.watcher.opening_summary_enabled
                else ""
            )
            feishu.send_text(
                "✅ 美股盯盘已启动\n"
                f"👀 监控: {', '.join(position.symbol for position in positions)}\n"
                f"🪟 窗口阶梯: {window_text}\n"
                f"♻️ 重置线: {reset_text}\n"
                f"🧯 兜底冷却: {config.watcher.ladder_cooldown_seconds:g} 秒\n"
                f"🧊 同方向冷静期: {config.watcher.symbol_direction_cooldown_seconds:g} 秒"
                f"{opening_text}"
            )

        while not stop_requested:
            started_at = time.time()
            try:
                quotes = provider.fetch_quotes(positions)
                maybe_send_opening_summary(quotes, alert_state, feishu, config)
                handle_quotes(quotes, price_windows, alert_state, feishu, config.watcher)
            except Exception:
                logging.exception("Watch cycle failed")

            elapsed = time.time() - started_at
            time.sleep(max(1, config.watcher.poll_seconds - elapsed))
        return 0
    finally:
        provider.close()


def handle_quotes(
    quotes: list[Quote],
    price_windows: dict[str, PriceWindow],
    alert_state: AlertState,
    feishu: FeishuBot,
    watcher_config,
) -> None:
    candidates: list[AlertCandidate] = []
    for quote in quotes:
        quote_candidates: list[AlertCandidate] = []
        for window in watcher_config.alert_windows:
            moves = price_windows[window.rule_id].add(quote.symbol, quote.price)
            if not moves:
                continue
            for move in moves:
                logging.info(
                    "%s %.4f %s move %.2f%%",
                    quote.symbol,
                    quote.price,
                    window.rule_id,
                    move.change_percent,
                )
                candidate = build_ladder_candidate(quote, move, window, alert_state, watcher_config)
                if candidate is not None:
                    quote_candidates.append(candidate)

        if not quote_candidates:
            if not any(window.has_history(quote.symbol) for window in price_windows.values()):
                logging.info("%s baseline %.4f", quote.symbol, quote.price)
            continue

        candidates.extend(select_strongest_candidates(quote_candidates))

    for candidate in candidates:
        burst_rule_id = burst_cooldown_rule_id(candidate)
        if not alert_state.should_alert(
            candidate.quote.symbol,
            candidate.move.direction,
            rule_id=burst_rule_id,
            cooldown_seconds=watcher_config.symbol_direction_cooldown_seconds,
        ):
            logging.info(
                "Ladder alert suppressed by symbol-direction cooldown for %s %s",
                candidate.quote.symbol,
                candidate.move.direction,
            )
            continue
        feishu.send_text(format_ladder_alert(candidate.quote, candidate.move, candidate.window, candidate.level))
        alert_state.mark_ladder_alerted(
            candidate.quote.symbol,
            candidate.move.direction,
            candidate.level,
            window_id=candidate.window.rule_id,
        )
        alert_state.mark_alerted(
            candidate.quote.symbol,
            candidate.move.direction,
            rule_id=burst_rule_id,
        )
        logging.info(
            "Ladder alert sent for %s %s %s %.2f%% level %.2f%%",
            candidate.quote.symbol,
            candidate.window.rule_id,
            candidate.move.direction,
            candidate.move.change_percent,
            candidate.level,
        )


def build_ladder_candidate(
    quote: Quote,
    move: PriceMove,
    window: AlertWindow,
    alert_state: AlertState,
    watcher_config,
) -> AlertCandidate | None:
    absolute_change = abs(move.change_percent)
    if absolute_change < window.reset_percent:
        alert_state.reset_ladder(quote.symbol, move.direction, window_id=window.rule_id)
        return None

    highest = alert_state.ladder_highest(quote.symbol, move.direction, window_id=window.rule_id)
    crossed = [
        level
        for level in window.ladder
        if absolute_change >= level and level > highest
    ]
    if not crossed:
        return None

    level = max(crossed)
    if not alert_state.should_ladder_alert(
        quote.symbol,
        move.direction,
        level,
        cooldown_seconds=watcher_config.ladder_cooldown_seconds,
        window_id=window.rule_id,
    ):
        return None

    return AlertCandidate(quote=quote, move=move, window=window, level=level)


def select_strongest_candidates(candidates: list[AlertCandidate]) -> list[AlertCandidate]:
    selected: dict[tuple[str, str], AlertCandidate] = {}
    for candidate in candidates:
        key = (candidate.quote.symbol, candidate.move.direction)
        current = selected.get(key)
        if current is None or candidate_priority(candidate) > candidate_priority(current):
            selected[key] = candidate
    return list(selected.values())


def candidate_priority(candidate: AlertCandidate) -> tuple[float, float, float]:
    return (
        abs(candidate.move.change_percent),
        candidate.level,
        -candidate.window.minutes,
    )


def burst_cooldown_rule_id(candidate: AlertCandidate) -> str:
    return "burst"


def maybe_send_opening_summary(quotes: list[Quote], alert_state: AlertState, feishu: FeishuBot, config) -> None:
    watcher_config = config.watcher
    if not watcher_config.opening_summary_enabled:
        return

    now = datetime.now(eastern_zone())
    if now.weekday() >= 5:
        return
    if not _is_opening_summary_time(now, watcher_config.opening_summary_window_minutes):
        return
    if not any(quote.open_price is not None and quote.prev_close_price is not None for quote in quotes):
        return

    date_key = now.date().isoformat()
    if alert_state.opening_summary_sent(date_key):
        return

    feishu.send_text(
        format_opening_summary(
            quotes,
            threshold_percent=watcher_config.opening_summary_threshold_percent,
            current_time=now,
        )
    )
    alert_state.mark_opening_summary_sent(date_key)
    logging.info("Opening summary sent for %s", date_key)


def _is_opening_summary_time(now: datetime, window_minutes: float) -> bool:
    market_open = datetime.combine(now.date(), dt_time(9, 30), tzinfo=now.tzinfo)
    elapsed_seconds = (now - market_open).total_seconds()
    return 0 <= elapsed_seconds <= window_minutes * 60


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Watch US stocks with moomoo OpenD and Feishu alerts.")
    parser.add_argument("--once", action="store_true", help="Fetch quotes once and exit.")
    args = parser.parse_args(argv)

    if args.once:
        return run_once()
    return run_watch()


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
