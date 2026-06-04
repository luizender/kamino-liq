"""Typer command-line interface."""

from __future__ import annotations

import time
from datetime import datetime

import typer
from solders.pubkey import Pubkey

from . import __version__
from .api import KaminoClient
from .liquidation import apply_price_overrides
from .render import console, render_position, render_simulation
from .service import load_positions

app = typer.Typer(
    add_completion=False,
    no_args_is_help=True,
    help="Inspect Kamino Lend positions and their liquidation prices (read-only).",
)


def _version_callback(show: bool) -> None:
    if show:
        console.print(f"kamino-liq {__version__}")
        raise typer.Exit()


@app.callback()
def _root(
    _version: bool = typer.Option(
        False,
        "--version",
        callback=_version_callback,
        is_eager=True,
        help="Show the version and exit.",
    ),
) -> None:
    """Kamino liquidation-price toolkit."""


@app.command()
def report(
    wallet: str = typer.Argument(
        ..., help="Solana wallet public key (read-only — never a private key)."
    ),
    crash: bool = typer.Option(
        True, "--crash/--no-crash", help="Include the global market-crash scenario."
    ),
    watch: bool = typer.Option(False, "--watch", "-w", help="Refresh continuously until stopped."),
    interval: int = typer.Option(
        30, "--interval", min=1, help="Seconds between refreshes in watch mode."
    ),
) -> None:
    """Show the liquidation prices of WALLET's Kamino Lend positions."""
    _validate_wallet(wallet)
    client = KaminoClient()

    if watch:
        _watch(wallet, client, crash, interval)
    else:
        _report_once(wallet, client, crash)


@app.command("simulate")
def simulate_command(
    wallet: str = typer.Argument(
        ..., help="Solana wallet public key (read-only — never a private key)."
    ),
    price: list[str] = typer.Option(
        None, "--price", "-p", help="Override an asset price, e.g. -p SOL=120 (repeatable)."
    ),
    crash: bool = typer.Option(
        True, "--crash/--no-crash", help="Include the global market-crash scenario."
    ),
) -> None:
    """Recompute WALLET's liquidation health under hypothetical prices."""
    _validate_wallet(wallet)
    overrides = _parse_overrides(price or [])
    client = KaminoClient()

    found = list(load_positions(client, wallet))
    held: set[str] = set()
    for position in found:
        render_simulation(position, apply_price_overrides(position, overrides), show_crash=crash)
        held.update(c.symbol.upper() for c in position.collateral)
        held.update(b.symbol.upper() for b in position.borrows)

    if not held:
        console.print(f"[yellow]No Kamino Lend positions found for {wallet}.[/yellow]")
        return
    unknown = sorted(set(overrides) - held)
    if unknown:
        console.print(f"[yellow]No position holds: {', '.join(unknown)}.[/yellow]")


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #
def _validate_wallet(wallet: str) -> None:
    try:
        Pubkey.from_string(wallet)
    except Exception as exc:  # solders raises a bare ValueError-like error
        raise typer.BadParameter("not a valid Solana public key", param_hint="WALLET") from exc


def _parse_overrides(items: list[str]) -> dict[str, float]:
    if not items:
        raise typer.BadParameter("provide at least one SYMBOL=PRICE", param_hint="--price")
    overrides: dict[str, float] = {}
    for item in items:
        symbol, sep, value = item.partition("=")
        if not sep or not symbol.strip():
            raise typer.BadParameter(f"expected SYMBOL=PRICE, got {item!r}", param_hint="--price")
        try:
            overrides[symbol.strip().upper()] = float(value)
        except ValueError as exc:
            raise typer.BadParameter(f"{value!r} is not a number", param_hint="--price") from exc
    return overrides


def _report_once(wallet: str, client: KaminoClient, crash: bool) -> bool:
    """Render every position; return whether any were found."""
    found = list(load_positions(client, wallet))
    for position in found:
        render_position(position, show_crash=crash)
    if not found:
        console.print(f"[yellow]No Kamino Lend positions found for {wallet}.[/yellow]")
    return bool(found)


def _watch(
    wallet: str,
    client: KaminoClient,
    crash: bool,
    interval: int,
) -> None:
    try:
        while True:
            console.clear()
            console.print(
                f"[dim]Kamino liquidation watch · {wallet} · {datetime.now():%Y-%m-%d %H:%M:%S}"
                f" · every {interval}s · Ctrl+C to stop[/dim]\n"
            )
            try:
                _report_once(wallet, client, crash)
            except Exception as exc:  # pylint: disable=broad-exception-caught
                # keep watching through transient API errors
                console.print(f"[red]Refresh failed: {exc}[/red]")
            time.sleep(interval)
    except KeyboardInterrupt:
        console.print("\n[dim]stopped.[/dim]")
