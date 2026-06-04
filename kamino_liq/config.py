"""REST endpoint, timeout, and the stablecoin symbol set."""

API_BASE = "https://api.kamino.finance"
USER_AGENT = "kamino-liq/0.1"

HTTP_TIMEOUT = 30

# Symbols treated as price-stable in the market-crash scenario.
STABLE_SYMBOLS = frozenset(
    {
        "USDC",
        "USDT",
        "PYUSD",
        "USDG",
        "USDH",
        "FDUSD",
        "DAI",
        "USDS",
        "USDE",
        "SUSDE",
        "USDY",
        "EURC",
        "USDR",
        "USD*",
    }
)
