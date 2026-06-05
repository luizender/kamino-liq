---
name: project-conventions
description: Architecture, layering, and quality bar for the lend-liq codebase. Load before adding or modifying code in this repository.
user-invocable: false
---

# lend-liq conventions

A small, **read-only** CLI that reads a wallet's Kamino Lend or Aave V3 position and
computes its liquidation prices. It never needs or touches a private key and never
sends a transaction — preserve that invariant in every change.

## Layering (do not cross)

Per-protocol I/O lives in a client: `kamino/api.py` (`KaminoClient`, Kamino REST) and
`aave/api.py` (`AaveClient`, Aave GraphQL) are the **only** I/O. A loader turns a
wallet into `Position` objects: `kamino/service.py` (`portfolio` lists the loans,
`loan` prices each, `market` names it) and `aave/service.py` (markets + supplies /
borrows). `sources.py` resolves an address to the right protocol loader, keeping the
CLI protocol-agnostic. Then `liquidation.py` is **pure math over the models: no I/O,
no rendering** → `render.py` (Rich) → `cli.py` (Typer). Keeping `liquidation.py` free
of I/O is what makes the math trivially unit-testable; don't import network/render
code into it. No on-chain RPC: Kamino is REST, Aave is HTTP GraphQL, no private key.

## Models

`models.py` holds frozen dataclasses shared by both protocols; health metrics are
**derived properties**, not stored fields. A `Position` is fully described by its
collateral, borrows, and `debt_value` — for Kamino the borrow-factor-**adjusted**
figure, which is *not* `Σ borrow value` (see `kamino/service.py::_build_position`);
for Aave (no borrow factor) the plain USD sum (`aave/service.py`). Anything that
reprices debt must respect that factor (`liquidation.py::apply_price_overrides`).

## Quality bar (enforced — keep it green)

- `ruff format` and `ruff check` clean (config in `ruff.toml`, line length 100).
- `pytest` passes at **100% coverage** (`fail_under = 100`).
- `pylint lend_liq` stays **10.00/10**.

Run all three:
`.venv/bin/ruff check lend_liq tests && .venv/bin/ruff format --check lend_liq tests && .venv/bin/pytest -q --cov --cov-report=term-missing && .venv/bin/pylint lend_liq`

A `Stop` hook runs this gate automatically; a `PostToolUse` hook applies `ruff` on
each edit. Every new function needs a test in the matching `tests/test_*.py`.

## Style

- Match surrounding code. Reuse the `render.py` helpers (`_table`, `_usd`,
  `_health_color`) instead of building ad-hoc Rich tables.
- New CLI commands follow the existing pattern: `sources.resolve` (the protocol
  seam) → the returned loader → a `render.py` function.
- Every endpoint is wrapped by one client method (`KaminoClient` in `kamino/api.py`,
  `AaveClient` in `aave/api.py`); keep HTTP there and out of the service loaders.
