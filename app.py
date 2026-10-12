"""Authenticated webhook relay from TradingView to a Telegram channel."""

import json
import os
import secrets
from collections.abc import Mapping
from dataclasses import dataclass

import requests
from flask import Flask, request


@dataclass(frozen=True)
class ForwarderSettings:
    telegram_token: str
    channel_id: str
    webhook_secret: str
    timeout_seconds: float = 10.0
    max_body_bytes: int = 8192

    @classmethod
    def from_environment(cls, environment: Mapping[str, str] | None = None):
        env = os.environ if environment is None else environment
        return cls(
            telegram_token=env.get("FORWARDER_BOT_TOKEN", ""),
            channel_id=env.get("TRADINGVIEW_ALERTS_CHANNEL_ID", ""),
            webhook_secret=env.get("FORWARDER_WEBHOOK_SECRET", ""),
            timeout_seconds=float(env.get("FORWARDER_TIMEOUT_SECONDS", "10")),
            max_body_bytes=int(env.get("FORWARDER_MAX_BODY_BYTES", "8192")),
        )

    def is_configured(self):
        return bool(
            self.telegram_token
            and self.channel_id
            and self.webhook_secret
            and self.timeout_seconds > 0
            and self.max_body_bytes > 0
        )


def create_app(settings: ForwarderSettings | None = None, http_post=None) -> Flask:
    """Assemble the relay with injected configuration and HTTP transport."""
    options = settings if settings is not None else ForwarderSettings.from_environment()
    send = http_post if http_post is not None else requests.post
    application = Flask(__name__)
    application.config["MAX_CONTENT_LENGTH"] = options.max_body_bytes

    @application.post("/forward")
    def forward():
        if not options.is_configured():
            return {"error": "Webhook relay is not configured"}, 503

        raw = request.get_data(cache=False)
        try:
            message = raw.decode("utf-8")
        except UnicodeDecodeError:
            return {"error": "Expected UTF-8 text"}, 400

        provided = request.headers.get("X-Webhook-Token", "")
        bearer = request.headers.get("Authorization", "")
        if not provided and bearer.startswith("Bearer "):
            provided = bearer.removeprefix("Bearer ")

        # TradingView alerts cannot send arbitrary headers. A separate relay
        # credential may be carried inside a JSON alert and removed before
        # the trading signal is delivered to Telegram.
        try:
            payload = json.loads(message)
        except json.JSONDecodeError:
            payload = None
        if isinstance(payload, dict) and "relay_secret" in payload:
            if not provided:
                provided = payload["relay_secret"]
            payload.pop("relay_secret")
            message = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))

        if not isinstance(provided, str) or not provided or not secrets.compare_digest(
            provided, options.webhook_secret
        ):
            return {"error": "Unauthorized"}, 401
        if not message.strip():
            return {"error": "Empty alert"}, 400

        try:
            response = send(
                f"https://api.telegram.org/bot{options.telegram_token}/sendMessage",
                json={"chat_id": options.channel_id, "text": message},
                timeout=options.timeout_seconds,
            )
            response.raise_for_status()
        except requests.RequestException:
            # Exception objects may contain the URL with the bot token.
            application.logger.error("Telegram rejected the alert relay request")
            return {"error": "Upstream delivery failed"}, 502
        return {"status": "sent"}, 200

    return application


app = create_app()
