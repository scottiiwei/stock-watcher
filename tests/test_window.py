import unittest

from stock_watcher.window import PriceWindow


class PriceWindowTests(unittest.TestCase):
    def test_does_not_report_before_window_is_fully_warmed(self) -> None:
        window = PriceWindow(window_seconds=300)

        self.assertEqual(window.add("AAPL", 100, timestamp=0), ())
        self.assertEqual(window.add("AAPL", 105, timestamp=299), ())

    def test_reports_after_warmup_even_when_oldest_point_was_pruned(self) -> None:
        window = PriceWindow(window_seconds=300)

        window.add("AAPL", 100, timestamp=0)
        window.add("AAPL", 101, timestamp=10)
        window.add("AAPL", 101.5, timestamp=20)
        moves = window.add("AAPL", 103, timestamp=311)

        self.assertNotEqual(moves, ())
        up_move = next(move for move in moves if move.direction == "up")
        self.assertEqual(up_move.old_price, 101.5)
        self.assertAlmostEqual(up_move.change_percent, 1.4778325123)

    def test_reports_moves_from_window_low_and_high(self) -> None:
        window = PriceWindow(window_seconds=60)

        self.assertEqual(window.add("AAPL", 100, timestamp=0), ())
        window.add("AAPL", 98, timestamp=30)
        moves = window.add("AAPL", 101, timestamp=60)

        up_move = next(move for move in moves if move.direction == "up")
        down_move = next(move for move in moves if move.direction == "down")
        self.assertEqual(up_move.symbol, "AAPL")
        self.assertAlmostEqual(up_move.change_percent, 3.0612244898)
        self.assertEqual(up_move.old_price, 98)
        self.assertEqual(up_move.reference_label, "低点")
        self.assertAlmostEqual(down_move.change_percent, 0)
        self.assertEqual(down_move.reference_label, "高点")

    def test_reports_drop_from_window_high(self) -> None:
        window = PriceWindow(window_seconds=60)

        window.add("AAPL", 100, timestamp=0)
        window.add("AAPL", 102, timestamp=30)
        moves = window.add("AAPL", 99.5, timestamp=60)

        down_move = next(move for move in moves if move.direction == "down")
        self.assertAlmostEqual(down_move.change_percent, -2.4509803921)
        self.assertEqual(down_move.old_price, 102)
        self.assertEqual(down_move.reference_label, "高点")

    def test_discards_points_outside_window(self) -> None:
        window = PriceWindow(window_seconds=300)

        window.add("AAPL", 100, timestamp=0)
        moves = window.add("AAPL", 110, timestamp=301)

        self.assertEqual(moves, ())


if __name__ == "__main__":
    unittest.main()
