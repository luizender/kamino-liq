"""Tests for the orchestration layer (wallet -> Position objects)."""

from kamino_liq import service


def _deposit(name, amount, price, liq):
    return {
        "tokenName": name,
        "tokenAmount": str(amount),
        "tokenPrice": price,
        "liquidationLtv": liq,
    }


def _borrow(name, amount, price, borrow_factor):
    return {
        "tokenName": name,
        "tokenAmount": str(amount),
        "tokenPrice": price,
        "tokenValue": amount * price,
        "borrowFactor": borrow_factor,
    }


def test_load_positions_builds_from_loan_detail(fake_kamino, loan_detail):
    detail = loan_detail(
        deposits=[_deposit("SOL", 10, 100.0, 0.75)],
        borrows=[_borrow("USDC", 500, 1.0, 1)],
    )
    client = fake_kamino(
        portfolio=[{"address": "OB", "marketAddress": "MKT"}], loans={"OB": detail}
    )

    (position,) = list(service.load_positions(client, "W"))
    assert position.market_name == "Main Market"
    assert position.address == "OB"
    sol = position.collateral[0]
    assert (sol.symbol, sol.amount, sol.price, sol.liquidation_threshold) == (
        "SOL",
        10.0,
        100.0,
        0.75,
    )
    assert position.borrows[0].amount == 500.0
    assert position.debt_value == 500.0  # 500 value * borrowFactor 1


def test_debt_value_applies_borrow_factor(fake_kamino, loan_detail):
    detail = loan_detail(
        deposits=[_deposit("SOL", 10, 100.0, 0.75)],
        borrows=[_borrow("ETH", 1, 2000.0, 1.5)],
    )
    client = fake_kamino(
        portfolio=[{"address": "OB", "marketAddress": "MKT"}], loans={"OB": detail}
    )

    (position,) = list(service.load_positions(client, "W"))
    assert position.debt_value == 3000.0  # value 2000 * borrowFactor 1.5


def test_empty_portfolio(fake_kamino):
    client = fake_kamino(portfolio=[], loans={})
    assert list(service.load_positions(client, "W")) == []


def test_market_name_cached(fake_kamino, loan_detail):
    """Two loans in the same market should only call market() once."""
    detail = loan_detail(deposits=[_deposit("SOL", 1, 10.0, 0.8)])
    client = fake_kamino(
        portfolio=[
            {"address": "OB1", "marketAddress": "MKT"},
            {"address": "OB2", "marketAddress": "MKT"},
        ],
        loans={"OB1": detail, "OB2": detail},
    )

    calls = {"n": 0}
    orig_market = client.market

    def counting_market(pubkey):
        calls["n"] += 1
        return orig_market(pubkey)

    client.market = counting_market
    positions = list(service.load_positions(client, "W"))
    assert len(positions) == 2
    assert calls["n"] == 1  # cached
