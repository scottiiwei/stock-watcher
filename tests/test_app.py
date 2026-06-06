import unittest
from datetime import datetime

from stock_watcher.app import _is_opening_summary_time, format_ladder_alert, format_opening_summary
from stock_watcher.config import AlertWindow
from stock_watcher.moomoo_provider import Quote
from stock_watcher.window import PriceMove


class AppFormattingTests(unittest.TestCase):
    def test_format_ladder_alert_uses_level_icon(self) -> None:
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
            reference_timestamp=1780669800,
            current_timestamp=1780669920,
            reference_label="低点",
            direction_value="up",
        )
        window = AlertWindow(minutes=5, ladder=(1, 1.5, 2, 2.5), reset_percent=0.7)

        message = format_ladder_alert(quote, move, window, 2)

        self.assertIn("🔥 美股盯盘提醒｜5分钟 2% 阶梯", message)
        self.assertIn("🏷️ 标的: AAPL Apple", message)
        self.assertIn("📈 波动: 5分钟窗口上涨 2.00%", message)
        self.assertIn("🧭 区间: 低点", message)
        self.assertNotIn("🎯 策略:", message)
        self.assertIn("⏱️ 时段: regular", message)

    def test_opening_summary_marks_large_gap(self) -> None:
        quote = Quote(
            code="US.NVDA",
            symbol="NVDA",
            name="NVIDIA",
            price=104,
            quote_time="2026-06-05 10:30:00",
            session="regular",
            open_price=104,
            prev_close_price=100,
        )

        message = format_opening_summary(
            [quote],
            threshold_percent=3,
            current_time=datetime(2026, 6, 5, 9, 31),
        )

        self.assertIn("🔔 美股开盘价格快照", message)
        self.assertIn("🚨 NVDA NVIDIA: 上涨 4.00%", message)
        self.assertIn("(100.00 -> 104.00)", message)

    def test_opening_summary_time_window_uses_eastern_time(self) -> None:
        self.assertFalse(_is_opening_summary_time(datetime(2026, 6, 5, 9, 29), 15))
        self.assertTrue(_is_opening_summary_time(datetime(2026, 6, 5, 9, 30), 15))
        self.assertTrue(_is_opening_summary_time(datetime(2026, 6, 5, 9, 45), 15))
        self.assertFalse(_is_opening_summary_time(datetime(2026, 6, 5, 9, 46), 15))


if __name__ == "__main__":
    unittest.main()
