"""Fail-closed permission control for exchange order placement."""

import os
from collections.abc import Mapping
from dataclasses import dataclass


class LiveTradingDisabled(RuntimeError):
    """Live orders are not explicitly authorized."""


@dataclass(frozen=True)
class ExecutionSettings:
    enabled: bool
    mode: str

    @classmethod
    def from_environment(cls, environment: Mapping[str, str] | None = None):
        env = os.environ if environment is None else environment
        return cls(
            enabled=env.get("ENABLE_LIVE_TRADING", "").strip().lower() == "true",
            mode=env.get("TRADING_MODE", "paper").strip().lower(),
        )


def require_live_trading(settings: ExecutionSettings | None = None):
    """Require both explicit controls before invoking a live exchange."""
    policy = settings if settings is not None else ExecutionSettings.from_environment()
    if not (policy.enabled and policy.mode == "live"):
        raise LiveTradingDisabled(
            "Live trading disabled. Set ENABLE_LIVE_TRADING=true and TRADING_MODE=live "
            "only after reviewing the exchange configuration."
        )
