import unittest

from stock_watcher.window import PriceWindow


class PriceWindowTests(unittest.TestCase):
    def test_reports_percent_change_inside_window(self) -> None:
        window = PriceWindow(window_seconds=300)

        self.assertIsNone(window.add("AAPL", 100, timestamp=0))
        move = window.add("AAPL", 101.5, timestamp=60)

        self.assertIsNotNone(move)
        assert move is not None
        self.assertEqual(move.symbol, "AAPL")
        self.assertAlmostEqual(move.change_percent, 1.5)
        self.assertEqual(move.direction, "up")

    def test_discards_points_outside_window(self) -> None:
        window = PriceWindow(window_seconds=300)

        window.add("AAPL", 100, timestamp=0)
        move = window.add("AAPL", 110, timestamp=301)

        self.assertIsNone(move)


if __name__ == "__main__":
    unittest.main()
