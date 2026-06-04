"""Endpoints, timeouts, and KLend on-chain layout constants."""

API_BASE = "https://api.kamino.finance"
DEFAULT_RPC = "https://api.mainnet-beta.solana.com"
USER_AGENT = "kamino-liq/0.1"

# Kamino Scope oracle — the same prices the protocol liquidates on.
PRICE_ENV = "mainnet-beta"
PRICE_SOURCE = "scope"

HTTP_TIMEOUT = 30
RPC_TIMEOUT = 40
RPC_MAX_ACCOUNTS = 100  # getMultipleAccounts caps at 100 keys per request

# A wallet's obligations are scanned one REST call per market and there is no
# cross-market endpoint, so the lookups are fanned out concurrently. Capped at
# the default requests connection-pool size to avoid churning connections.
MARKET_SCAN_WORKERS = 8

# KLend "scaled fraction" (Sf) fixed-point factor.
FRACTION_SCALE = 2**60

# Byte offsets inside the KLend Reserve account. RESERVE_LTV_OFFSET is read only
# to cross-check the layout against the API's maxLtv, so a program upgrade that
# shifts the struct fails loudly instead of returning a wrong threshold.
RESERVE_LTV_OFFSET = 4872  # ReserveConfig.loanToValuePct (u8) == API maxLtv
RESERVE_LIQ_THRESHOLD_OFFSET = 4873  # ReserveConfig.liquidationThresholdPct (u8)
MINT_DECIMALS_OFFSET = 44  # SPL mint account: decimals byte

# An obligation's depositedAmount is denominated in collateral tokens (cTokens),
# not the underlying. These three fields give each reserve's collateral exchange
# rate (underlying per cToken) = total_liquidity / collateral mint supply, which
# grows above 1.0 as the reserve accrues interest. Without it, deposits read as
# cTokens — understating collateral and every metric derived from it.
RESERVE_AVAILABLE_AMOUNT_OFFSET = 224  # ReserveLiquidity.availableAmount (u64)
RESERVE_BORROWED_AMOUNT_SF_OFFSET = 232  # ReserveLiquidity.borrowedAmountSf (u128, Sf-scaled)
RESERVE_COLLATERAL_MINT_SUPPLY_OFFSET = 2592  # ReserveCollateral.mintTotalSupply (u64)

# The exchange rate is >= 1.0 by construction and only creeps up with interest; a
# value outside this range means the on-chain layout shifted (fail loudly instead
# of silently returning wrong amounts).
MAX_COLLATERAL_EXCHANGE_RATE = 1000.0

# Sentinel marking an unused deposit/borrow slot in an obligation.
EMPTY_PUBKEY = "11111111111111111111111111111111"

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
