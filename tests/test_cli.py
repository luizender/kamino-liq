"""Tests for the Typer CLI, with all I/O monkeypatched."""

from typer.testing import CliRunner

from kamino_liq import cli

runner = CliRunner()
WALLET = "11111111111111111111111111111111"  # valid base58 (system program)


def patch_clients(monkeypatch, kamino):
    monkeypatch.setattr(cli, "KaminoClient", lambda *a, **k: kamino)


def test_version() -> None:
    result = runner.invoke(cli.app, ["--version"])
    assert result.exit_code == 0
    assert "kamino-liq" in result.output


def test_report_found(monkeypatch, fake_kamino, sample_position) -> None:
    patch_clients(monkeypatch, fake_kamino())
    # Two positions exercise the rendering loop.
    monkeypatch.setattr(
        cli,
        "load_positions",
        lambda c, w: [sample_position, sample_position],
    )
    result = runner.invoke(cli.app, ["report", WALLET])
    assert result.exit_code == 0
    assert "Health factor" in result.output


def test_report_not_found(monkeypatch, fake_kamino) -> None:
    patch_clients(monkeypatch, fake_kamino())
    monkeypatch.setattr(cli, "load_positions", lambda c, w: [])
    result = runner.invoke(cli.app, ["report", WALLET])
    assert "No Kamino Lend positions" in result.output


def test_report_invalid_wallet() -> None:
    result = runner.invoke(cli.app, ["report", "not-a-key!"])
    assert result.exit_code != 0


def test_report_no_crash(monkeypatch, fake_kamino, sample_position) -> None:
    patch_clients(monkeypatch, fake_kamino())
    monkeypatch.setattr(cli, "load_positions", lambda c, w: [sample_position])
    result = runner.invoke(cli.app, ["report", WALLET, "--no-crash"])
    assert result.exit_code == 0


def test_report_watch_invokes_watch(monkeypatch, fake_kamino) -> None:
    patch_clients(monkeypatch, fake_kamino())
    called = {}
    monkeypatch.setattr(cli, "_watch", lambda *a: called.setdefault("watched", True))
    result = runner.invoke(cli.app, ["report", WALLET, "--watch"])
    assert result.exit_code == 0
    assert called.get("watched") is True


def test_simulate_command(monkeypatch, fake_kamino, sample_position) -> None:
    patch_clients(monkeypatch, fake_kamino())
    monkeypatch.setattr(cli, "load_positions", lambda c, w: [sample_position])
    result = runner.invoke(cli.app, ["simulate", WALLET, "-p", "SOL=50"])
    assert result.exit_code == 0
    assert "Simulation" in result.output
    assert "Simulated price changes" in result.output


def test_simulate_warns_on_unheld_symbol(monkeypatch, fake_kamino, sample_position) -> None:
    patch_clients(monkeypatch, fake_kamino())
    monkeypatch.setattr(cli, "load_positions", lambda c, w: [sample_position])
    result = runner.invoke(cli.app, ["simulate", WALLET, "-p", "SOL=50", "-p", "BONK=1"])
    assert result.exit_code == 0
    assert "No position holds: BONK" in result.output


def test_simulate_not_found(monkeypatch, fake_kamino) -> None:
    patch_clients(monkeypatch, fake_kamino())
    monkeypatch.setattr(cli, "load_positions", lambda c, w: [])
    result = runner.invoke(cli.app, ["simulate", WALLET, "-p", "SOL=50"])
    assert "No Kamino Lend positions" in result.output


def test_simulate_requires_a_price() -> None:
    result = runner.invoke(cli.app, ["simulate", WALLET])
    assert result.exit_code != 0


def test_simulate_rejects_bad_price_format() -> None:
    result = runner.invoke(cli.app, ["simulate", WALLET, "-p", "SOL"])
    assert result.exit_code != 0


def test_simulate_rejects_non_numeric_price() -> None:
    result = runner.invoke(cli.app, ["simulate", WALLET, "-p", "SOL=cheap"])
    assert result.exit_code != 0


def test_watch_survives_errors(monkeypatch) -> None:
    calls = {"n": 0}

    def report_once(wallet, client, crash):
        calls["n"] += 1
        if calls["n"] == 1:
            raise RuntimeError("transient")  # exercises the except branch

    def sleep(_seconds):
        if calls["n"] >= 2:
            raise KeyboardInterrupt  # exercises the second (clean) pass, then stops

    monkeypatch.setattr(cli, "_report_once", report_once)
    monkeypatch.setattr(cli.time, "sleep", sleep)
    cli._watch("W", object(), crash=True, interval=1)
    assert calls["n"] == 2
