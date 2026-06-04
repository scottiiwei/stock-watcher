import os
import unittest
from unittest.mock import patch

from stock_watcher.config import load_alert_rules


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


if __name__ == "__main__":
    unittest.main()
