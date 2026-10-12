"""Validate the reconstructed public config against actual code usage."""

import ast
import importlib
import os
from pathlib import Path
import re
import unittest
from unittest.mock import patch

import config


ROOT = Path(__file__).resolve().parents[1]
USES_CONFIG = ("Main.py", "ExchangeClients.py", "exchanges.py", "database.py",
               "helperfunctions.py", "texts.py")


class ConfigurationTests(unittest.TestCase):
    def test_every_config_reference_is_defined(self):
        missing = {}
        for path in USES_CONFIG:
            source = (ROOT / path).read_text(encoding="utf-8")
            names = set(re.findall(r"\bconfig\.([A-Za-z_]\w*)", source))
            absent = sorted(name for name in names if not hasattr(config, name))
            if absent:
                missing[path] = absent
        self.assertEqual(missing, {})

    def test_default_runtime_is_safe(self):
        with patch.dict(os.environ, {}, clear=True):
            importlib.reload(config)
            self.assertTrue(config.OFFLINE)
            self.assertEqual(config.ADMINS_ID, [0])
            self.assertFalse(config.payments_configured())
            self.assertFalse(config.referrals_configured())
            self.assertEqual(config.MAIN_BOT_TOKEN, "")
            self.assertEqual(config.SQL_DATABASE_URL, "sqlite:///./telegrambot.db")

    def test_rejects_partial_financial_configuration(self):
        with patch.dict(os.environ, {"PAYMENTS_ENABLED": "true",
                                     "REFERRALS_ENABLED": "true"}, clear=True):
            importlib.reload(config)
            self.assertFalse(config.payments_configured())
            self.assertFalse(config.referrals_configured())
        importlib.reload(config)

    def test_no_legacy_exfiltration_or_payment_bypass(self):
        source = (ROOT / "Main.py").read_text(encoding="utf-8")
        self.assertNotIn("SECRET_TRANSACTION_ID", source)
        self.assertNotIn("config.PEEP", source)
        self.assertIn("config.payments_configured()", source)
        self.assertIn("config.referrals_configured()", source)

    def test_no_old_private_data_files_present(self):
        for path in ("DB/telegrambot.db", "test.py", "test.ipynb",
                     "nohup.out", "examples/.svn/wc.db", "telegrambot.db"):
            with self.subTest(path=path):
                self.assertFalse((ROOT / path).exists())


if __name__ == "__main__":
    unittest.main()
