# Telegram Trading Bot

A **historical Python project** for routing Telegram and TradingView trading signals to cryptocurrency exchanges. Originally developed in 2022–2023, it demonstrates Telegram bot workflows, exchange API integrations, trade signal parsing, SQLite/SQLAlchemy persistence, and webhook forwarding.

> **Portfolio / educational project, not a production trading service.** The exchange integrations and pinned dependencies are old, and real-world trading functionality has **not** been validated on current APIs.

## What the project includes

- Interactive Telegram bot with conversation-based navigation, account settings, and exchange management.
- Integration code for **BingX, Bybit, and CoinEx**.
- Telegram group/channel and TradingView signal processing.
- Direct signal-entry workflows, performance statements, and historical subscription/referral flows.
- A Flask webhook relay for TradingView alerts, with shared-secret authentication.
- Security regression tests, architecture notes, and configuration examples.

## Safety and project status

Live orders are blocked in the known signal execution paths unless **both** `ENABLE_LIVE_TRADING=true` and `TRADING_MODE=live` are set. The default `paper` mode **does not execute simulated orders**. Payments and referrals are also disabled by default.

Do **not** enable live trading or billing until exchange API behavior, order sizing, idempotency, API permissions, data protection, and payment verification have been reviewed and tested against sandbox systems. The legacy code still has known security and reliability limitations; see [Security](docs/security.md).

The original private configuration file is no longer available. `config.py` was **reconstructed from application references**, without restoring any historic credentials, wallet addresses, administrator IDs, or subscription prices. Configuration now reads environment variables. `.env.example` documents relevant settings.

## Repository layout

| Path | Responsibility |
| --- | --- |
| `Main.py` | Legacy Telegram bot handlers and polling entry point |
| `ExchangeClients.py` | Exchange API client implementations |
| `exchanges.py` | Signal interpretation and exchange-order orchestration |
| `app.py` | Authenticated Flask webhook relay |
| `database.py`, `models.py` | SQLAlchemy persistence |
| `config.py` | Environment-based compatibility configuration |
| `trading_bot/` | Signal parsing and live-order safety controls |
| `tests/` | Offline security and behavior regression tests |
| `docs/` | Architecture and security guidance |

## Safe local testing

On Python 3.11, run the isolated offline checks without connecting to a Telegram account or exchange:

```sh
python -m venv .venv
. .venv/bin/activate
python -m pip install "Flask>=2.2,<4" "requests>=2.28,<3"
python -m unittest discover -s tests -v
```

The CI workflow also checks Python compilation. **Passing these tests does not establish that the complete bot runs with modern Telegram or exchange APIs.** `requirements.txt` is preserved as the original 2022-era dependency snapshot, not a supported or reproducible modern install.

## Webhook relay

The webhook lives at `POST /forward` in `app.py` (`app:app` for WSGI). Configure `FORWARDER_BOT_TOKEN`, `TRADINGVIEW_ALERTS_CHANNEL_ID`, and `FORWARDER_WEBHOOK_SECRET` using environment variables. Requests can authenticate through `X-Webhook-Token`, a Bearer token, or a JSON `relay_secret` field. The relay strips `relay_secret` before forwarding messages. Deploy only behind HTTPS with ingress rate limiting.

See [Architecture](docs/architecture.md) and [Security](docs/security.md).

## Repository provenance

This public repository was created with **fresh Git history** from an audited, sanitized working tree. The original development history, databases, generated caches, and private configuration artifacts were **not imported**. No production credentials or user datasets are included. Historical credentials should not be reused.

## License

No license has been granted for reuse at this time. The repository is public for viewing and learning; contact the repository owner before redistributing or adapting the source.
