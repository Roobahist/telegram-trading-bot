import ast
from pathlib import Path
import unittest

from trading_bot.parsing import SignalFormatError, parse_stored_list, parse_tradingview_payload
from trading_bot.runtime import ExecutionSettings, LiveTradingDisabled, require_live_trading


class SafetyTests(unittest.TestCase):
    def test_stored_lists(self):
        self.assertEqual(parse_stored_list("['BTC','ETH']"), ["BTC", "ETH"])
        with self.assertRaises(ValueError):
            parse_stored_list("__import__('os').system('true')")

    def test_tradingview_formats(self):
        examples = (
            '{"id":12,"secret":"s","ticker":"BTCUSDT","strategy":{"order_action":"buy","position_size":2}}',
            "{'id': 12, 'secret': 's', 'ticker': 'BTCUSDT', 'strategy': {'oa': 'BUY', 'ps': 2}}",
        )
        for value in examples:
            with self.subTest(value=value):
                result = parse_tradingview_payload(value)
                self.assertEqual(result["strategy"]["order_action"], "buy")
                self.assertEqual(result["strategy"]["position_size"], 2.0)

    def test_malformed_signals(self):
        valid = {"id": 12, "secret": "s", "ticker": "BTCUSDT", "strategy": {"oa": "buy", "ps": 2}}
        for invalid in (
            {"id": True},
            {"strategy": {"oa": "invalid", "ps": 1}},
            {"strategy": {"oa": "buy", "ps": -1}},
            {"strategy": {"oa": "buy", "ps": float("nan")}},
        ):
            with self.subTest(invalid=invalid), self.assertRaises(SignalFormatError):
                parse_tradingview_payload({**valid, **invalid})
        with self.assertRaises(SignalFormatError):
            parse_tradingview_payload("__import__('os').system('true')")

    def test_live_orders_require_two_flags(self):
        for env in ({}, {"TRADING_MODE": "live"}, {"ENABLE_LIVE_TRADING": "true"}):
            with self.subTest(env=env), self.assertRaises(LiveTradingDisabled):
                require_live_trading(ExecutionSettings.from_environment(env))
        require_live_trading(ExecutionSettings.from_environment({
            "ENABLE_LIVE_TRADING": "true", "TRADING_MODE": "live"
        }))

    def test_no_eval_in_sensitive_modules(self):
        root = Path(__file__).resolve().parents[1]
        for path in ("Main.py", "exchanges.py", "ExchangeClients.py", "texts.py", "app.py"):
            with self.subTest(path=path):
                tree = ast.parse((root / path).read_text(encoding="utf-8"))
                offenders = [n for n in ast.walk(tree) if isinstance(n, ast.Call)
                    and isinstance(n.func, ast.Name) and n.func.id == "eval"]
                self.assertEqual(offenders, [])


if __name__ == "__main__":
    unittest.main()
