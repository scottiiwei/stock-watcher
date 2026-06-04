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


if __name__ == "__main__":
    unittest.main()
