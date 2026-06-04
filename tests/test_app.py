import unittest

from stock_watcher.app import format_alert
from stock_watcher.config import AlertRule
from stock_watcher.moomoo_provider import Quote
from stock_watcher.window import PriceMove


class AppFormattingTests(unittest.TestCase):
    def test_format_alert_uses_readable_icons(self) -> None:
        quote = Quote(
            code="US.AAPL",
            symbol="AAPL",
            name="Apple",
            price=102,
            quote_time="2026-06-05 10:30:00",
            session="regular",
        )
        move = PriceMove(
            symbol="AAPL",
            old_price=100,
            new_price=102,
            change_percent=2,
            window_seconds=120,
        )
        rule = AlertRule("strong", "强异动", 2, 3)

        message = format_alert(quote, move, rule)

        self.assertIn("🔥 美股盯盘提醒｜强异动", message)
        self.assertIn("🏷️ 标的: AAPL Apple", message)
        self.assertIn("📈 波动: 2.0 分钟内上涨 2.00%", message)
        self.assertNotIn("🎯 策略:", message)
        self.assertIn("⏱️ 时段: regular", message)

    def test_normal_alert_uses_distinct_icon(self) -> None:
        quote = Quote(
            code="US.NVDA",
            symbol="NVDA",
            name="NVIDIA",
            price=101.2,
            quote_time="2026-06-05 10:30:00",
            session="regular",
        )
        move = PriceMove(
            symbol="NVDA",
            old_price=100,
            new_price=101.2,
            change_percent=1.2,
            window_seconds=60,
        )
        rule = AlertRule("normal", "普通异动", 1, 3)

        message = format_alert(quote, move, rule)

        self.assertIn("⚡ 美股盯盘提醒｜普通异动", message)
        self.assertIn("📈 波动: 1.0 分钟内上涨 1.20%", message)


if __name__ == "__main__":
    unittest.main()
