# Contributor guidance

This is a public, educational snapshot of an older Python cryptocurrency-trading bot. It is **not a production-ready order execution system**. Maintain its fail-closed behavior.

## Components

- `Main.py`: Telegram conversation handlers and polling.
- `ExchangeClients.py` and `exchanges.py`: old exchange API adapters and signal/order orchestration.
- `app.py`: authenticated webhook relay.
- `database.py` and `models.py`: SQLAlchemy persistence.
- `config.py`: reconstructed configuration backed by environment variables.
- `trading_bot/parsing.py`: untrusted signal parsing.
- `trading_bot/runtime.py`: live-trading authorization guard.

## Security requirements

- Never commit production databases, compiled settings, real user data, personal logs, credentials, tokens, or wallet secrets.
- Do not use live Telegram or exchange accounts during tests.
- Do not weaken the double opt-in for live trading or enable billing/referrals without independent validation.
- Preserve legacy persisted column names, state values and exchange call signatures until characterization tests establish compatibility.
- Prefer injected HTTP clients and settings over hard-coded services.

## Validation

Use `python -m unittest discover -s tests -v`. GitHub Actions runs isolated offline tests and Python syntax checks, not real exchange integration tests.

The published Git history was initialized from sanitized source only. **Do not import the original private development history, databases or compiled configuration.**

Avoid live trades and automated production deployments.
