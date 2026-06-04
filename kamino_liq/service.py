"""Orchestration: turn a wallet into typed Position objects from the Kamino REST
API. The portfolio endpoint lists a wallet's loans across every market in one
call; each loan's fully-priced per-asset detail then comes from the loan
endpoint, and the market endpoint supplies its human-readable name."""

from __future__ import annotations

from collections.abc import Iterator

from .api import KaminoClient
from .models import Borrow, Collateral, Position


def load_positions(client: KaminoClient, wallet: str) -> Iterator[Position]:
    """Yield a Position for each of ``wallet``'s Kamino Lend loans."""
    names: dict[str, str] = {}
    for loan in client.portfolio(wallet):
        market = loan["marketAddress"]
        if market not in names:
            names[market] = client.market(market)["name"]
        detail = client.loan(loan["address"])
        yield _build_position(names[market], loan["address"], detail)


def _build_position(market_name: str, address: str, detail: dict) -> Position:
    info = detail["loanInfo"]
    borrows = info["debt"]["borrows"]
    collateral = tuple(_collateral(d) for d in info["collateral"]["deposits"])
    debt = tuple(_borrow(b) for b in borrows)
    debt_value = sum(float(b["tokenValue"]) * float(b["borrowFactor"]) for b in borrows)
    return Position(market_name, address, collateral, debt, debt_value)


def _collateral(deposit: dict) -> Collateral:
    return Collateral(
        symbol=deposit["tokenName"],
        amount=float(deposit["tokenAmount"]),
        price=float(deposit["tokenPrice"]),
        liquidation_threshold=float(deposit["liquidationLtv"]),
    )


def _borrow(borrow: dict) -> Borrow:
    return Borrow(
        symbol=borrow["tokenName"],
        amount=float(borrow["tokenAmount"]),
        price=float(borrow["tokenPrice"]),
    )
