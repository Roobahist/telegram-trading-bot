# Architecture

The diagram reflects inspected source modules, not a proposed deployment.

```mermaid
flowchart TD
    TV[TradingView webhook] --> Relay[app.py: authenticated HTTP relay]
    Relay --> TG[Telegram channel]
    TG --> Main[Main.py: Telegram handlers]
    Groups[Telegram groups and channels] --> Main
    Main --> Signals[exchanges.py: signal processing]
    Main --> DB[database.py + models.py: SQLAlchemy]
    Signals --> Parse[trading_bot/parsing.py]
    Signals --> Guard[trading_bot/runtime.py]
    Signals --> DB
    Guard --> Clients[ExchangeClients.py: exchange adapters]
    Clients --> BingX[BingX]
    Clients --> Bybit[Bybit]
    Clients --> CoinEx[CoinEx]
```

The existing bot also provides management, subscription, referral, and report
flows. Main.py has a large state machine and writes to the database at module
import time. The database contents and schema have not been migrated.

## Critical boundaries

1. External TradingView payloads are parsed into validated mappings without
   calling `eval()`. Each user signal still requires its own stored secret.
2. `exchanges.py` explicitly checks the live-trading guard before activating
   an exchange adapter for order placement.
3. `app.py` validates an independent relay secret before forwarding alerts.
4. Tests can substitute a network sender and policy settings without making
   production calls.

## Next structural step

After regression coverage of the conversation state machine and persisted
database models exists, move the legacy handlers and exchange clients into
cohesive modules, keeping compatibility shims for the existing entry points.
A blanket directory move today would risk breaking runtime imports and data.
