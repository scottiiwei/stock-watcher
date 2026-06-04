import unittest
from datetime import datetime

from stock_watcher.moomoo_provider import MoomooQuoteProvider


class MoomooQuoteProviderTests(unittest.TestCase):
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


if __name__ == "__main__":
    unittest.main()
