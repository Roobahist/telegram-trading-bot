# Security, modernization and remaining limitations

This is an **experimental, historical codebase** and should not be used for live trading, customer funds or subscription billing without a substantial new review. The original dependencies and exchange APIs date to 2022–2023.

## Changes in the public snapshot

- Replaced unsafe evaluation of untrusted and stored strings with explicit parsing and allowlisted navigation.
- Added two independent live-trading flags; real orders are disabled by default on the known signal execution paths.
- Authenticated the TradingView forwarding webhook and stripped its relay credential before forwarding.
- Introduced request-size bounds and HTTP timeouts in the forwarding flow.
- Removed a historical special-transaction subscription bypass and unsolicited mirroring of group/channel posts to an administrator.
- Disabled financial subscription/referral actions by default, including validation prerequisites.
- Reconstructed a **nonsecret** environment-based `config.py`, without guessing historical keys, prices or private identifiers.
- Added offline regression tests and CI syntax checks.

## Privacy and provenance

This **public repository starts with new Git history**. Historical SQLite databases, cached Python bytecode (including compiled private configuration), user datasets, notebooks, local logs and third-party SVN caches were **not included**. The earlier development repository remains separate and private. Never merge, fork or import that old history into this public repository.

No production credentials were intentionally copied into this snapshot. The absence of findings in a source-pattern audit does not guarantee that every secret or sensitive value has been ruled out. Credentials potentially exposed in historical private artifacts should be rotated or revoked.

## Important engineering risks still open

1. **Real orders**: The exchange integrations are stale; quantities, decimal precision, market modes, partial fills, idempotency, stop losses and retries require simulation and exchange testnet coverage.
2. **Credential handling**: The legacy database model stores per-user exchange keys and bot secrets as ordinary strings. A real deployment needs encryption, masked logs and least-privilege API keys.
3. **Payment verification**: The existing TronScan verification has not been validated against realistic transaction/reorg and duplicate-payment cases. Payments and referrals must stay off.
4. **Concurrency**: Global database session state and synchronous I/O exist in asynchronous Telegram handlers.
5. **Dependency age**: `requirements.txt` is a historical snapshot with old or prerelease packages. Avoid assuming a reproducible modern installation.
6. **Webhook ingress**: Use HTTPS, appropriate auth rotation, rate limiting and network protection.
7. **Observability**: Broad exception handlers and debug printing remain in legacy modules, and may inadvertently log request contents or account data.
8. **Testing gaps**: The 16 regression tests cover isolated safety behavior; bot startup, full workflows and exchange integrations remain unverified.

## Development and rollout

For safe local testing, follow [README](../README.md) and run only offline unit tests. Use disposable data and mocked exchange clients. Never treat `TRADING_MODE=paper` as a complete simulated execution system; it simply blocks the known live order paths.
