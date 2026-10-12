"""Safe parsing for legacy stored lists and incoming trade signals."""

import ast
import json
import math
from collections.abc import Mapping


class SignalFormatError(ValueError):
    """Raised for an invalid or untrusted trading signal."""


def parse_stored_list(value):
    """Read repr()-serialized lists without evaluating Python expressions."""
    if isinstance(value, (list, tuple)):
        return list(value)
    if not isinstance(value, str):
        raise ValueError("Expected a serialized list")
    try:
        result = ast.literal_eval(value)
    except (SyntaxError, ValueError, TypeError, MemoryError, RecursionError) as exc:
        raise ValueError("Invalid serialized list") from exc
    if not isinstance(result, (list, tuple)):
        raise ValueError("Serialized value must be a list or tuple")
    return list(result)


def parse_tradingview_payload(value):
    """Normalize JSON and legacy dict literals to validated trade fields."""
    if isinstance(value, Mapping):
        payload = dict(value)
    elif isinstance(value, str) and len(value) <= 64_000:
        try:
            payload = json.loads(value)
        except json.JSONDecodeError:
            try:
                payload = ast.literal_eval(value)
            except (SyntaxError, ValueError, TypeError, MemoryError, RecursionError) as exc:
                raise SignalFormatError("Malformed alert message") from exc
    else:
        raise SignalFormatError("Signal must be a reasonably sized object or string")
    if not isinstance(payload, dict):
        raise SignalFormatError("Signal must be an object")
    strategy = payload.get("strategy")
    if not isinstance(strategy, dict):
        raise SignalFormatError("Missing strategy object")
    try:
        user_id = int(payload["id"])
        action = strategy.get("order_action", strategy.get("oa"))
        amount = float(strategy.get("position_size", strategy.get("ps")))
        ticker = payload["ticker"]
        secret = payload["secret"]
    except (KeyError, ValueError, TypeError, OverflowError) as exc:
        raise SignalFormatError("Missing or invalid trade fields") from exc
    if (
        isinstance(payload["id"], bool)
        or user_id <= 0
        or not isinstance(action, str)
        or action.lower() not in ("buy", "sell")
        or not math.isfinite(amount)
        or amount <= 0
        or not isinstance(ticker, str)
        or not ticker.strip()
        or not isinstance(secret, str)
        or not secret
    ):
        raise SignalFormatError("Trade fields failed validation")
    payload["id"] = user_id
    payload["ticker"] = ticker.strip()
    payload["strategy"] = {**strategy, "order_action": action.lower(), "position_size": amount}
    return payload
