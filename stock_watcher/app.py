from __future__ import annotations

import argparse
import logging
import signal
import sys
import time

from .config import AlertRule, load_config, load_positions
from .feishu import FeishuBot
from .moomoo_provider import MoomooQuoteProvider, Quote
from .state import AlertState
from .window import PriceMove, PriceWindow


LOG_FORMAT = "%(asctime)s %(levelname)s %(message)s"


def rule_icon(rule: AlertRule) -> str:
    if rule.rule_id == "strong":
        return "🔥"
    if rule.rule_id == "normal":
        return "⚡"
    return "🚨"


def format_alert(quote: Quote, move: PriceMove, rule: AlertRule) -> str:
    direction = "上涨" if move.change_percent >= 0 else "下跌"
    direction_icon = "📈" if move.change_percent >= 0 else "📉"
    minutes = move.window_seconds / 60
    return (
        f"{rule_icon(rule)} 美股盯盘提醒｜{rule.label}\n"
        f"🏷️ 标的: {quote.symbol} {quote.name}\n"
        f"{direction_icon} 波动: {minutes:.1f} 分钟内{direction} {abs(move.change_percent):.2f}%\n"
        f"💵 价格: {move.old_price:.2f} -> {move.new_price:.2f}\n"
        f"⏱️ 时段: {quote.session}\n"
        f"🕒 行情时间(美东): {quote.quote_time or 'unknown'}"
    )


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
    price_window = PriceWindow(config.watcher.price_window_minutes * 60)
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
            rules_text = "\n".join(
                f"🎯 策略: {rule.label} {rule.threshold_percent:g}% / 冷却 {rule.cooldown_minutes:g} 分钟"
                for rule in config.watcher.alert_rules
            )
            feishu.send_text(
                "✅ 美股盯盘已启动\n"
                f"👀 监控: {', '.join(position.symbol for position in positions)}\n"
                f"🪟 窗口: {config.watcher.price_window_minutes:g} 分钟\n"
                f"{rules_text}"
            )

        while not stop_requested:
            started_at = time.time()
            try:
                quotes = provider.fetch_quotes(positions)
                handle_quotes(quotes, price_window, alert_state, feishu, config.watcher.alert_rules)
            except Exception:
                logging.exception("Watch cycle failed")

            elapsed = time.time() - started_at
            time.sleep(max(1, config.watcher.poll_seconds - elapsed))
        return 0
    finally:
        provider.close()


def handle_quotes(
    quotes: list[Quote],
    price_window: PriceWindow,
    alert_state: AlertState,
    feishu: FeishuBot,
    alert_rules: tuple[AlertRule, ...],
) -> None:
    for quote in quotes:
        move = price_window.add(quote.symbol, quote.price)
        if move is None:
            logging.info("%s baseline %.4f", quote.symbol, quote.price)
            continue

        logging.info("%s %.4f move %.2f%%", quote.symbol, quote.price, move.change_percent)
        for rule in alert_rules:
            if abs(move.change_percent) < rule.threshold_percent:
                continue

            cooldown_seconds = rule.cooldown_minutes * 60
            if not alert_state.should_alert(
                quote.symbol,
                move.direction,
                rule_id=rule.rule_id,
                cooldown_seconds=cooldown_seconds,
            ):
                continue

            feishu.send_text(format_alert(quote, move, rule))
            alert_state.mark_alerted(quote.symbol, move.direction, rule_id=rule.rule_id)
            logging.info(
                "Alert sent for %s %s %s %.2f%%",
                quote.symbol,
                rule.rule_id,
                move.direction,
                move.change_percent,
            )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Watch US stocks with moomoo OpenD and Feishu alerts.")
    parser.add_argument("--once", action="store_true", help="Fetch quotes once and exit.")
    args = parser.parse_args(argv)

    if args.once:
        return run_once()
    return run_watch()


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
