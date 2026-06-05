"""Orchestration: turn an Aave user address into typed Position objects from the
AaveKit GraphQL API. The markets query supplies each reserve's liquidation
threshold (and the user's eMode override); userSupplies/userBorrows supply the
actual priced positions. Aave has no borrow factor, so a position's debt_value is
simply the USD sum of its borrows."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterator

from ..models import Borrow, Collateral, Position
from .api import AaveClient


def load_positions(client: AaveClient, user: str, chain_id: int) -> Iterator[Position]:
    """Yield a Position for each Aave market on ``chain_id`` where ``user`` holds
    collateral or debt."""
    markets = client.markets(chain_id, user)
    thresholds = _threshold_map(markets)
    names = {market["address"]: market["name"] for market in markets}
    inputs = [{"address": market["address"], "chainId": chain_id} for market in markets]
    positions = client.user_positions(inputs, user)
    supplies = _by_market(positions["supplies"])
    borrows = _by_market(positions["borrows"])
    for address, name in names.items():
        collateral = _collateral(supplies[address], thresholds)
        debt = tuple(_borrow(b) for b in borrows[address])
        if not collateral and not debt:
            continue
        debt_value = sum(float(b["debt"]["usd"]) for b in borrows[address])
        yield Position(name, address, collateral, debt, debt_value)


def _threshold_map(markets: list[dict]) -> dict[tuple[str, str], float]:
    thresholds: dict[tuple[str, str], float] = {}
    for market in markets:
        for reserve in market["reserves"]:
            key = (market["address"], reserve["underlyingToken"]["address"].lower())
            thresholds[key] = _effective_lt(reserve)
    return thresholds


def _effective_lt(reserve: dict) -> float:
    """The liquidation threshold that applies to the user: the eMode category's when
    the user has eMode enabled for this reserve, otherwise the reserve's own."""
    emode = (reserve.get("userState") or {}).get("emode")
    info = emode or reserve["supplyInfo"]
    return float(info["liquidationThreshold"]["value"])


def _by_market(rows: list[dict]) -> dict[str, list[dict]]:
    grouped: dict[str, list[dict]] = defaultdict(list)
    for row in rows:
        grouped[row["market"]["address"]].append(row)
    return grouped


def _collateral(
    supplies: list[dict], thresholds: dict[tuple[str, str], float]
) -> tuple[Collateral, ...]:
    return tuple(
        Collateral(
            supply["currency"]["symbol"],
            float(supply["balance"]["amount"]["value"]),
            float(supply["balance"]["usdPerToken"]),
            thresholds[(supply["market"]["address"], supply["currency"]["address"].lower())],
        )
        for supply in supplies
        if supply["isCollateral"]
    )


def _borrow(borrow: dict) -> Borrow:
    debt = borrow["debt"]
    return Borrow(
        borrow["currency"]["symbol"], float(debt["amount"]["value"]), float(debt["usdPerToken"])
    )
