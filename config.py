"""Public, nonsecret configuration reconstructed from the existing code.

Unknown historical values deliberately default to disabled or zero. Set
credentials and actual commercial terms through environment variables only.
Do not treat this compatibility module as verified production configuration.
"""

import os


def _text(name, default=""):
    return os.environ.get(name, default).strip()


def _integer(name, default):
    value = _text(name)
    return int(value) if value else default


def _number(name, default):
    value = _text(name)
    return float(value) if value else default


def _enabled(name, default=False):
    value = _text(name)
    return value.lower() in ("1", "yes", "true", "on") if value else default


def _admin_ids():
    ids = _text("TELEGRAM_ADMIN_IDS")
    return [int(item.strip()) for item in ids.split(",") if item.strip()] if ids else [0]


# Application credentials and external endpoints
MAIN_BOT_TOKEN = _text("MAIN_BOT_TOKEN")
FORWARDER_BOT_TOKEN = _text("FORWARDER_BOT_TOKEN")
BOT_USERNAME = _text("BOT_USERNAME", "your_bot_username")
TRADINGVIEW_ALERTS_CHANNEL_ID = _integer("TRADINGVIEW_ALERTS_CHANNEL_ID", 0)
TRADINGVIEW_WEBHOOK_URL = _text("TRADINGVIEW_WEBHOOK_URL")
TRONSCAN_APIKEY = _text("TRONSCAN_APIKEY")
TRONSCAN_API_BASE = _text("TRONSCAN_API_BASE", "https://apilist.tronscanapi.com/api")
USDT_TRC20_WALLET_ADDRESS = _text("USDT_TRC20_WALLET_ADDRESS")
BINGX_APIKEY = _text("BINGX_APIKEY")
BINGX_APISECRET = _text("BINGX_APISECRET")
BYBIT_APIKEY = _text("BYBIT_APIKEY")
BYBIT_APISECRET = _text("BYBIT_APISECRET")
COINEX_APIKEY = _text("COINEX_APIKEY")
COINEX_APISECRET = _text("COINEX_APISECRET")
BINANCE_APIKEY = _text("BINANCE_APIKEY")
BINANCE_APISECRET = _text("BINANCE_APISECRET")
SQL_DATABASE_URL = _text("SQL_DATABASE_URL", "sqlite:///./telegrambot.db")
SECRET_KEY_LENGTH = _integer("SECRET_KEY_LENGTH", 32)
ADMINS_ID = _admin_ids()
OFFLINE = _enabled("BOT_OFFLINE", True)
OPERATIONS_CHAT_ID = _integer("OPERATIONS_CHAT_ID", 0)
PAYMENTS_ENABLED = _enabled("PAYMENTS_ENABLED", False)
REFERRALS_ENABLED = _enabled("REFERRALS_ENABLED", False)

# Exchange and trade labels used in the existing Telegram state machine.
BINANCE, BYBIT, COINEX, BINGX = "Binance", "ByBit", "CoinEx", "BingX"
EXCHANGE_NAMES = [BINANCE, BYBIT, COINEX, BINGX]
SPOT, FUTURES = "Spot", "Futures"
MARKET_TYPES = [SPOT, FUTURES]
BUY, SELL = "Buy", "Sell"
TRADE_SIDES = [BUY, SELL]
MARKET = "Market"
NO_SL = "No Stop Loss"
NO_TP = "No Take Profit"
REST = "Remaining"
SUBMIT = "Submit"
BACK, HOME = "Back", "Home"
ACTIVATE, DEACTIVATE = "Activate", "Deactivate"

# Navigation labels. Keep these as single stable values so filter matching
# and button construction share the same source of truth.
AUTOMATION = "Trade automation"
STATEMENT = "Statement"
MANAGEMENT = "Management"
ACCOUNT_STATUS = "Account status"
COPYTRADE_ADMINS = "Copy-trading"
CONTACT_US = "Contact support"
INSTRUCTION = "Instructions"
ADMIN = "Admin"
TRADINGVIEW = "TradingView"
TELEGRAM_GROUP = "Telegram group"
TELEGRAM_CHANNEL = "Telegram channel"
SEND_SIGNAL_DIRECTLY = "Place direct signal"
CREATE_NEW_SIGNAL = "Create new signal"
MY_FOLLOWERS = "My followers"
GETSTATEMENT = "Get statement"
CHANGESTATEMENTSYMBOLS = "Change statement symbols"
API_MANAGEMENT = "Exchange API settings"
TRADING_CONSTANTS = "Trading settings"
SUBSCRIBE = "Subscribe"
REFERRAL = "Referral"
VOLUME = "Volume"
LEVERAGE = "Leverage"
STOPLOSS = "Stop loss"
TAKEPROFIT = "Take profit"
MONTH1, MONTH3, MONTH6, MONTH12 = "1 month", "3 months", "6 months", "12 months"
ENTER_REFERRAL_CODE = "Enter referral code"
WITHDRAW_CASHBACK = "Withdraw referral credit"
DISCOUNTED_SUB = "Subscription with referral credit"
SEND_MESSAGE_TO_ALL = "Message all users"

# Financial terms are unknown from checked-in source. Zero is a disabled
# placeholder, never an inferred historical price or approved live value.
MONTH1PRICEDOLLAR = _number("MONTH1PRICEDOLLAR", 0.0)
MONTH3PRICEDOLLAR = _number("MONTH3PRICEDOLLAR", 0.0)
MONTH6PRICEDOLLAR = _number("MONTH6PRICEDOLLAR", 0.0)
MONTH12PRICEDOLLAR = _number("MONTH12PRICEDOLLAR", 0.0)
MONTH3DISCOUNTPERCENTAGE = _number("MONTH3DISCOUNTPERCENTAGE", 0.0)
MONTH6DISCOUNTPERCENTAGE = _number("MONTH6DISCOUNTPERCENTAGE", 0.0)
MONTH12DISCOUNTPERCENTAGE = _number("MONTH12DISCOUNTPERCENTAGE", 0.0)
REFERRAL_CASHBACK_PERCENTAGE = _number("REFERRAL_CASHBACK_PERCENTAGE", 0.0)
REFERRAL_DISCOUNTED_SUB_PERCENTAGE = _number("REFERRAL_DISCOUNTED_SUB_PERCENTAGE", 0.0)
REFERRAL_ENTER_GIFT_DAYS = _integer("REFERRAL_ENTER_GIFT_DAYS", 0)
MIN_REFERRAL_BALANCE_SUBSCRIBE = _number("MIN_REFERRAL_BALANCE_SUBSCRIBE", 0.0)
MIN_REFERRAL_BALANCE_WITHDRAW = _number("MIN_REFERRAL_BALANCE_WITHDRAW", 0.0)
MIN_REFERRAL_SUBSCRIBE = _number("MIN_REFERRAL_SUBSCRIBE", 0.0)
MIN_REFERRAL_WITHDRAW = _number("MIN_REFERRAL_WITHDRAW", 0.0)
USDT_DECIMAL_POINTS = 6
TRC20_TRANSACTION_ID_LENGTH = 64

MAX_ENTRY_EXIT = _integer("MAX_ENTRY_EXIT", 10)
MIN_VOLUME_PERCENTAGE_PUBLIC = _number("MIN_VOLUME_PERCENTAGE_PUBLIC", 1.0)
MAX_VOLUME_PERCENTAGE_PUBLIC = _number("MAX_VOLUME_PERCENTAGE_PUBLIC", 100.0)
SUGGESTED_VOLUME_PERCENTAGE = ["10%", "25%", "50%", "100%"]

# The legacy UI expects keyboard rows: a list of lists of button labels.
Back_Menu = [[BACK]]
BackHome_Menu = [[BACK, HOME]]
Main_Menu = [[AUTOMATION], [STATEMENT], [MANAGEMENT], [ACCOUNT_STATUS],
             [COPYTRADE_ADMINS], [CONTACT_US], [INSTRUCTION]]
Automation_Menu = [[SEND_SIGNAL_DIRECTLY], [TELEGRAM_GROUP],
                   [TELEGRAM_CHANNEL], [TRADINGVIEW], *BackHome_Menu]
Statement_Menu = [[CHANGESTATEMENTSYMBOLS], [GETSTATEMENT], *BackHome_Menu]
Management_Menu = [[API_MANAGEMENT], [TRADING_CONSTANTS], *BackHome_Menu]
Management_ApiManagement_Menu = [[BINANCE, BYBIT], [BINGX, COINEX], *BackHome_Menu]
Management_TradingConstants_Menu = [[VOLUME, LEVERAGE],
                                    [STOPLOSS, TAKEPROFIT], *BackHome_Menu]
AccountStatus_Menu = [[SUBSCRIBE], [REFERRAL], *BackHome_Menu]
AccountStatus_Subscribe_Menu = [[MONTH1, MONTH3], [MONTH6, MONTH12], *BackHome_Menu]
AccountStatus_Referral_Menu = [[ENTER_REFERRAL_CODE],
                               [WITHDRAW_CASHBACK], [DISCOUNTED_SUB], *BackHome_Menu]
CopyTradeAdmins_Menu = [[CREATE_NEW_SIGNAL], [MY_FOLLOWERS], *BackHome_Menu]
Admin_Menu = [[SEND_MESSAGE_TO_ALL], *BackHome_Menu]

def payments_configured():
    """Return True only when a complete, explicitly enabled payment setup exists."""
    return bool(
        PAYMENTS_ENABLED
        and TRONSCAN_APIKEY
        and len(USDT_TRC20_WALLET_ADDRESS) == 34
        and USDT_TRC20_WALLET_ADDRESS.startswith("T")
        and all(price > 0 for price in (
            MONTH1PRICEDOLLAR,
            MONTH3PRICEDOLLAR,
            MONTH6PRICEDOLLAR,
            MONTH12PRICEDOLLAR,
        ))
    )


def referrals_configured():
    """Avoid any money-like referral changes without reviewed settings."""
    return bool(
        REFERRALS_ENABLED
        and OPERATIONS_CHAT_ID
        and 0 < REFERRAL_CASHBACK_PERCENTAGE <= 100
        and MIN_REFERRAL_WITHDRAW > 0
        and MIN_REFERRAL_SUBSCRIBE > 0
    )
