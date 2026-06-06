import os
import unittest
from unittest.mock import patch

from stock_watcher.config import load_config, load_alert_ladder, load_alert_rules, load_alert_windows


class ConfigTests(unittest.TestCase):
    def test_loads_multiple_alert_rules(self) -> None:
        with patch.dict(os.environ, {"ALERT_RULES": "normal:1:3,strong:2:3"}, clear=False):
            rules = load_alert_rules()

        self.assertEqual([rule.rule_id for rule in rules], ["normal", "strong"])
        self.assertEqual([rule.label for rule in rules], ["普通异动", "强异动"])
        self.assertEqual([rule.threshold_percent for rule in rules], [1.0, 2.0])
        self.assertEqual([rule.cooldown_minutes for rule in rules], [3.0, 3.0])

    def test_falls_back_to_legacy_threshold(self) -> None:
        env = {
            "PRICE_THRESHOLD_PERCENT": "1.5",
            "ALERT_COOLDOWN_MINUTES": "4",
        }
        with patch.dict(os.environ, env, clear=True):
            rules = load_alert_rules()

        self.assertEqual(len(rules), 1)
        self.assertEqual(rules[0].rule_id, "default")
        self.assertEqual(rules[0].threshold_percent, 1.5)
        self.assertEqual(rules[0].cooldown_minutes, 4.0)

    def test_loads_alert_ladder(self) -> None:
        with patch.dict(os.environ, {"ALERT_LADDER": "2,1,1.5,2.5"}, clear=False):
            ladder = load_alert_ladder()

        self.assertEqual(ladder, (1.0, 1.5, 2.0, 2.5))

    def test_loads_alert_windows(self) -> None:
        with patch.dict(os.environ, {"ALERT_WINDOWS": "5:1|1.5|2:0.7,3:0.8|1.2:0.5"}, clear=False):
            windows = load_alert_windows()

        self.assertEqual([window.minutes for window in windows], [3.0, 5.0])
        self.assertEqual(windows[0].ladder, (0.8, 1.2))
        self.assertEqual(windows[0].reset_percent, 0.5)
        self.assertEqual(windows[1].ladder, (1.0, 1.5, 2.0))
        self.assertEqual(windows[1].rule_id, "5m")

    def test_loads_symbol_direction_cooldown(self) -> None:
        env = {
            "FEISHU_APP_ID": "cli_test",
            "FEISHU_APP_SECRET": "secret",
            "FEISHU_RECEIVE_ID": "ou_test",
            "SYMBOL_DIRECTION_COOLDOWN_SECONDS": "240",
        }
        with patch.dict(os.environ, env, clear=True):
            config = load_config()

        self.assertEqual(config.watcher.symbol_direction_cooldown_seconds, 240)


if __name__ == "__main__":
    unittest.main()
