"""REST endpoints, timeout, supported Aave chains, and the stablecoin symbol set."""

API_BASE = "https://api.kamino.finance"
AAVE_API = "https://api.v3.aave.com/graphql"
USER_AGENT = "kamino-liq/0.1"

HTTP_TIMEOUT = 30

# Aave V3 deployments, keyed by the name accepted on the CLI's --chain option.
AAVE_CHAINS = {
    "ethereum": 1,
    "optimism": 10,
    "bsc": 56,
    "gnosis": 100,
    "polygon": 137,
    "sonic": 146,
    "zksync": 324,
    "metis": 1088,
    "base": 8453,
    "arbitrum": 42161,
    "avalanche": 43114,
    "celo": 42220,
    "linea": 59144,
    "scroll": 534352,
}

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
        "GHO",
    }
)
