import tempfile
import unittest
from pathlib import Path

from stock_watcher.state import AlertState


class AlertStateTests(unittest.TestCase):
    def test_cooldown_blocks_duplicate_direction(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "state.json"
            state = AlertState(path, cooldown_seconds=600)

            self.assertTrue(state.should_alert("AAPL", "up", now=1000))
            state.mark_alerted("AAPL", "up", now=1000)

            self.assertFalse(state.should_alert("AAPL", "up", now=1200))
            self.assertTrue(state.should_alert("AAPL", "down", now=1200))
            self.assertTrue(state.should_alert("AAPL", "up", now=1601))

    def test_rule_cooldowns_are_independent(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "state.json"
            state = AlertState(path)

            state.mark_alerted("AAPL", "up", now=1000, rule_id="normal")

            self.assertFalse(
                state.should_alert(
                    "AAPL",
                    "up",
                    now=1100,
                    rule_id="normal",
                    cooldown_seconds=180,
                )
            )
            self.assertTrue(
                state.should_alert(
                    "AAPL",
                    "up",
                    now=1100,
                    rule_id="strong",
                    cooldown_seconds=180,
                )
            )

    def test_ladder_state_tracks_highest_level_and_cooldown(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "state.json"
            state = AlertState(path)

            self.assertEqual(state.ladder_highest("AAPL", "up"), 0)
            self.assertTrue(state.should_ladder_alert("AAPL", "up", 1, cooldown_seconds=60, now=1000))

            state.mark_ladder_alerted("AAPL", "up", 1.5, now=1000)

            self.assertEqual(state.ladder_highest("AAPL", "up"), 1.5)
            self.assertFalse(state.should_ladder_alert("AAPL", "up", 1.5, cooldown_seconds=60, now=1030))
            self.assertTrue(state.should_ladder_alert("AAPL", "up", 2, cooldown_seconds=60, now=1030))

            state.reset_ladder("AAPL", "up")
            self.assertEqual(state.ladder_highest("AAPL", "up"), 0)

    def test_ladder_state_is_independent_per_window(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "state.json"
            state = AlertState(path)

            state.mark_ladder_alerted("AAPL", "up", 1, window_id="3m", now=1000)

            self.assertEqual(state.ladder_highest("AAPL", "up", window_id="3m"), 1)
            self.assertEqual(state.ladder_highest("AAPL", "up", window_id="5m"), 0)
            self.assertFalse(
                state.should_ladder_alert("AAPL", "up", 1, cooldown_seconds=60, window_id="3m", now=1030)
            )
            self.assertTrue(
                state.should_ladder_alert("AAPL", "up", 1, cooldown_seconds=60, window_id="5m", now=1030)
            )

    def test_opening_summary_date_is_persisted(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "state.json"
            state = AlertState(path)

            self.assertFalse(state.opening_summary_sent("2026-06-05"))
            state.mark_opening_summary_sent("2026-06-05")

            reloaded = AlertState(path)
            self.assertTrue(reloaded.opening_summary_sent("2026-06-05"))


if __name__ == "__main__":
    unittest.main()
