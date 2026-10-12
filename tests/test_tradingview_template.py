"""Rendered TradingView alert text must be valid JSON."""

import ast
import json
from pathlib import Path
import unittest


class TemplateTests(unittest.TestCase):
    def test_tradingview_template(self):
        source = (Path(__file__).resolve().parents[1] / "texts.py").read_text(encoding="utf-8")
        assignment = next(node for node in ast.parse(source).body
            if isinstance(node, ast.Assign)
            and any(isinstance(target, ast.Name) and target.id == "TRADINGVIEWALERT_FA"
                    for target in node.targets))
        raw = ast.literal_eval(assignment.value).strip(chr(96))
        value = raw.format(42, "abc")
        value = (value.replace("{{ticker}}", "BTCUSDT")
            .replace("{{strategy.order.action}}", "buy")
            .replace("{{strategy.position_size}}", "2"))
        parsed = json.loads(value)
        self.assertEqual(parsed["id"], 42)
        self.assertEqual(parsed["secret"], "abc")
        self.assertEqual(parsed["strategy"]["position_size"], 2)


if __name__ == "__main__":
    unittest.main()
