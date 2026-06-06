import unittest
from datetime import datetime

from stock_watcher.moomoo_provider import MoomooQuoteProvider


class MoomooQuoteProviderTests(unittest.TestCase):
    def test_pick_price_uses_session_specific_extended_price(self) -> None:
        row = {
            "last_price": 100,
            "pre_price": 101,
            "after_price": 102,
            "overnight_price": 103,
        }

        self.assertEqual(MoomooQuoteProvider._pick_price(row, "regular"), 100)
        self.assertEqual(MoomooQuoteProvider._pick_price(row, "pre-market"), 101)
        self.assertEqual(MoomooQuoteProvider._pick_price(row, "after-hours"), 102)
        self.assertEqual(MoomooQuoteProvider._pick_price(row, "overnight"), 103)

    def test_pick_price_falls_back_to_last_price_when_extended_price_missing(self) -> None:
        row = {
            "last_price": 100,
            "after_price": 0,
        }

        self.assertEqual(MoomooQuoteProvider._pick_price(row, "after-hours"), 100)

    def test_pick_quote_time_uses_data_time_during_regular_session(self) -> None:
        row = {"data_time": "10:30:12.123"}
        eastern_now = datetime(2026, 6, 5, 10, 31, 0)

        self.assertEqual(
            MoomooQuoteProvider._pick_quote_time(row, "regular", eastern_now),
            "10:30:12.123",
        )

    def test_pick_quote_time_uses_sample_time_during_extended_session(self) -> None:
        row = {"data_time": "16:00:00.330"}
        eastern_now = datetime(2026, 6, 5, 22, 19, 45)

        self.assertEqual(
            MoomooQuoteProvider._pick_quote_time(row, "overnight", eastern_now),
            "22:19:45",
        )

    def test_session_from_eastern_time(self) -> None:
        self.assertEqual(
            MoomooQuoteProvider._session_from_eastern_time(datetime(2026, 6, 4, 3, 59)),
            "overnight",
        )
        self.assertEqual(
            MoomooQuoteProvider._session_from_eastern_time(datetime(2026, 6, 4, 4, 0)),
            "pre-market",
        )
        self.assertEqual(
            MoomooQuoteProvider._session_from_eastern_time(datetime(2026, 6, 4, 9, 30)),
            "regular",
        )
        self.assertEqual(
            MoomooQuoteProvider._session_from_eastern_time(datetime(2026, 6, 4, 16, 0)),
            "after-hours",
        )
        self.assertEqual(
            MoomooQuoteProvider._session_from_eastern_time(datetime(2026, 6, 4, 20, 0)),
            "overnight",
        )

    def test_session_is_closed_during_us_weekend(self) -> None:
        self.assertEqual(
            MoomooQuoteProvider._session_from_eastern_time(datetime(2026, 6, 5, 20, 0)),
            "closed",
        )
        self.assertEqual(
            MoomooQuoteProvider._session_from_eastern_time(datetime(2026, 6, 6, 13, 51)),
            "closed",
        )
        self.assertEqual(
            MoomooQuoteProvider._session_from_eastern_time(datetime(2026, 6, 7, 19, 59)),
            "closed",
        )
        self.assertEqual(
            MoomooQuoteProvider._session_from_eastern_time(datetime(2026, 6, 7, 20, 0)),
            "overnight",
        )


if __name__ == "__main__":
    unittest.main()
