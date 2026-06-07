# lend-liq

[![CI](https://github.com/luizender/lend-liq/actions/workflows/ci.yml/badge.svg)](https://github.com/luizender/lend-liq/actions/workflows/ci.yml)

A small, **read-only** command-line tool that reads a wallet's live
[Kamino Lend](https://app.kamino.finance) (Solana) or [Aave V3](https://aave.com)
(EVM) position and tells you **at what prices it gets liquidated** — pulling the
position, prices, and liquidation thresholds straight from each protocol's public
API.

> 🔒 It only ever needs a wallet **public key**. It never asks for, needs, or
> touches a private key or seed phrase, and it never sends a transaction.

```
$ lend-liq report <YOUR_WALLET_PUBKEY>

───────────────── Main Market  ·  obligation 3ssjMRz3… ─────────────────
  Asset            Amount        Price            Value   Liq. LTV
  JupSOL      57,543.3696       $80.71    $4,644,272.32        60%
  PYUSD (debt) 2,042,156.91      $1.00   -$2,041,983.60

  Net account value                                    $2,571,246.73
  Current LTV                                                 44.58%
  Liquidation LTV                                             60.00%
  Health factor                       1.35  (liquidated below 1.00)
  Collateral drop to liquidation   25.80%  (if all collateral falls together)

  Liquidation price — single asset drops (others held constant)
  Asset     Current   Liq. price       Buffer
  JupSOL     $80.71       $59.92   25.8% drop
```

## Features

- **Two protocols** — Kamino Lend on Solana and Aave V3 across its EVM chains
  (`--chain`), behind one interface; the protocol is auto-detected from the address
  (`--protocol` overrides detection).
- **Live position** — fetches your actual deposits/borrows; no manual data entry.
- **Accurate liquidation math** — uses each protocol's own per-asset prices and
  liquidation thresholds (and, for Kamino, borrow-factor-adjusted debt), so the
  health figures match the protocol's UI.
- **Two liquidation views** — the price of each collateral if *only that asset
  drops*, plus a *global market-crash* scenario where volatile assets fall
  together while stablecoins hold.
- **What-if simulation** — override any asset's price (`simulate -p SOL=120`),
  collateral amount (`-a SOL=+10`), or borrow amount (`-b USDC=-5000`), and recompute
  health, liquidation prices, and crash scenario at those hypothetical values. Supports
  adding assets not currently in the position using the protocol's live reserve catalog.
- **Multi-market** — finds your loans across every Kamino market (Main, JLP,
  Jito, …) in a single call; for Aave, scans all 14 supported EVM chains by default.
- **Watch mode** — refresh continuously until you stop it.
- **No API key** — every data source is public.

## Install

Requires Python 3.10+.

```bash
python -m venv .venv && source .venv/bin/activate

# Option A — install as a command (`lend-liq`)
pip install -e .

# Option B — just the runtime deps, run via `python -m lend_liq`
pip install -r requirements.txt
```

## Usage

After `pip install -e .` the entry point is `lend-liq`; otherwise use
`python -m lend_liq`. The two are interchangeable.

```bash
# Liquidation report for a wallet (all your loans, every market)
lend-liq report <WALLET>

# Aave: pass an EVM address; scans all chains by default, or pin one with --chain
lend-liq report 0x<EVM_ADDRESS>
lend-liq report 0x<EVM_ADDRESS> --chain arbitrum

# Skip the crash scenario
lend-liq report <WALLET> --no-crash

# What-if: override prices (-p), collateral amounts (-a), or borrow amounts (-b)
# All flags are repeatable; mix and match freely
lend-liq simulate <WALLET> -p SOL=120 -p JupSOL=110
lend-liq simulate <WALLET> -a JupSOL=+5000        # add 5000 JupSOL to collateral
lend-liq simulate <WALLET> -b USDC=+500000        # add 500k USDC to borrows
lend-liq simulate <WALLET> -p SOL=80 -a SOL=-10000 -b USDT=+100000

# Simulate an asset not yet in the position (resolved from the live reserve catalog)
lend-liq simulate <WALLET> -a USDC=1000000

# Force a specific protocol (auto-detected from address shape by default)
lend-liq report <WALLET> --protocol kamino
lend-liq report 0x<EVM_ADDRESS> --protocol aave

# Watch mode: refresh every 15s until Ctrl+C
lend-liq report <WALLET> --watch --interval 15
```

Run `lend-liq --help` or `lend-liq <command> --help` for all options.

## How it works

Everything needed is public and keyless.

**Kamino (Solana, REST)** — a wallet's whole position comes from REST calls:

| Data | Source |
|------|--------|
| Your loans across all markets | `/portfolio/{wallet}` |
| Market names | `/v2/kamino-market/{pubkey}` |
| Per-asset amounts, live prices, liquidation thresholds, borrow factors | `/klend/loans/{pubkey}` |

`/portfolio/{wallet}` lists the loans, `/v2/kamino-market/{pubkey}` names each
market, and `/klend/loans/{pubkey}` returns each one's underlying deposit amounts,
live prices, per-asset liquidation thresholds, and borrow-factor-adjusted debt —
already computed the way the Kamino app shows them.

**Aave V3 (EVM, GraphQL)** — two POSTs to the AaveKit API (`api.v3.aave.com/graphql`)
per chain; by default all 14 supported chains are swept in parallel, matching Kamino's
all-markets behaviour. Pass `--chain` to pin a single deployment:

| Data | Source |
|------|--------|
| Per-reserve liquidation thresholds, eMode override, health factor | `markets` query |
| Priced supplies & borrows (amount, USD price, `isCollateral`) | `userSupplies` / `userBorrows` |

The `markets` query supplies each reserve's liquidation threshold (and the user's
eMode override); `userSupplies`/`userBorrows` supply the actual priced positions.
Aave has no borrow factor, so a position's debt is simply the USD sum of its borrows.

### The liquidation views

A position with several collateral assets has no single liquidation price — it has
a *surface* in price space, and any tool has to pick a path through it:

- **Single asset drops** — for each collateral, the price at which the position
  becomes liquidatable assuming that asset alone falls and the rest hold value.
- **Global crash** — every *volatile* collateral falls together while stablecoins
  keep their peg; reports the common drop % (and per-asset price) that triggers
  liquidation. This model holds the debt fixed, so it is suppressed when the debt
  itself is volatile (a real crash would move it too) — use `simulate` there.
- **Simulation** (`simulate`) — override prices (`-p`), collateral amounts (`-a`),
  or borrow amounts (`-b`) for any assets and recompute everything at once, for
  scenarios that aren't uniform. Amount flags accept `+`/`-` prefixes for relative
  adjustments or a bare number to set an absolute value. Assets not currently held
  can be added; their live price and liquidation threshold are fetched from the
  protocol's reserve catalog. The simulation view renders a side-by-side comparison
  (real vs. simulated liquidation prices and crash thresholds) so the impact is
  immediately visible. Repricing a borrowed asset rescales Kamino's
  borrow-factor-adjusted debt by its current aggregate factor.

## Project structure

```
lend_liq/
  config.py       endpoints, timeouts, supported chains, and stable pegs
  models.py       typed dataclasses; health metrics are derived properties
  sources.py      address -> protocol loader (the protocol seam)
  kamino/
    api.py        KaminoClient — the Kamino REST API
    service.py    orchestration: wallet -> Position objects
  aave/
    api.py        AaveClient — the Aave GraphQL API
    service.py    orchestration: address -> Position objects
  liquidation.py  pure liquidation-price math (no I/O)
  render.py       Rich rendering
  cli.py          Typer app: report / simulate
tests/            unit tests for the loaders and liquidation math
```

## Development

```bash
pip install -e ".[dev]"          # or: pip install -r requirements-dev.txt

ruff format lend_liq tests       # format (line length 100)
ruff check lend_liq tests        # lint (E/F/I/B/ANN/C4/UP/SIM)
pytest                           # run the unit tests
pytest --cov=lend_liq            # with coverage (enforced at 100%)
pylint lend_liq                  # static analysis (expects a clean 10.00/10)
```

The suite mocks all HTTP calls, so it runs offline and deterministically.
Ruff settings live in `ruff.toml`; coverage and pylint settings in `pyproject.toml`.
If you use Claude Code, `.claude/` ships hooks that run ruff on each edit and the
full gate (ruff + pytest + pylint) when a turn ends.

## Disclaimer

This is an informational tool, not financial advice. Prices and on-chain state
change continuously and liquidation depends on the protocol's live oracle at the
moment of liquidation. Always verify against the official Kamino or Aave app.
