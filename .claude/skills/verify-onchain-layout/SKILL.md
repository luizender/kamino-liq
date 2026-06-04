---
name: verify-onchain-layout
description: Re-derive and verify the KLend Reserve and SPL-mint byte offsets in config.py against a live on-chain account — use after a Kamino program upgrade makes the tool fail with "KLend reserve layout changed".
disable-model-invocation: true
---

# Verify on-chain layout

`kamino-liq` reads several values the REST API doesn't expose from on-chain
accounts at fixed byte offsets (`kamino_liq/config.py`):

- `RESERVE_LTV_OFFSET = 4872` — `ReserveConfig.loanToValuePct` (u8), read **only**
  to cross-check the layout against the API's `maxLtv`.
- `RESERVE_LIQ_THRESHOLD_OFFSET = 4873` — `ReserveConfig.liquidationThresholdPct` (u8).
- `MINT_DECIMALS_OFFSET = 44` — the SPL-mint `decimals` byte.
- `RESERVE_AVAILABLE_AMOUNT_OFFSET = 224` — `ReserveLiquidity.availableAmount` (u64).
- `RESERVE_BORROWED_AMOUNT_SF_OFFSET = 232` — `ReserveLiquidity.borrowedAmountSf`
  (u128, `Sf`-scaled by `FRACTION_SCALE`).
- `RESERVE_COLLATERAL_MINT_SUPPLY_OFFSET = 2592` — `ReserveCollateral.mintTotalSupply` (u64).

The last three give each reserve's collateral exchange rate
(`(available + borrowed) / mint_total_supply`), which converts an obligation's
cToken `depositedAmount` to the underlying amount the Kamino app shows
(`chain.py::_collateral_exchange_rate`).

Two guards fail loudly if a program upgrade shifts the struct rather than letting
the tool return wrong numbers:

- `chain.py::_check_layout` raises `KLend reserve layout changed …` when
  `byte[4872] != round(maxLtv * 100)`.
- `chain.py::_collateral_exchange_rate` raises when the computed rate falls outside
  `[1, MAX_COLLATERAL_EXCHANGE_RATE]` (the rate is ≥ 1.0 by construction).

Use this procedure to find the new offsets.

## Steps

1. Pick a known reserve and its API `maxLtv`. `kamino-liq reserves` prints each
   asset's Max LTV and Mint; get the reserve **address** from the same metrics
   endpoint (`kamino-market/<market>/reserves/metrics`, field `reserve`).

2. Fetch and scan the raw reserve account:
   ```bash
   .venv/bin/python - <<'PY'
   import base64, requests
   ADDR = "<reserve address>"
   MAXLTV = 70   # this reserve's API maxLtv as a percent (e.g. 0.70 -> 70)
   r = requests.post("https://api.mainnet-beta.solana.com", json={
       "jsonrpc": "2.0", "id": 1, "method": "getAccountInfo",
       "params": [ADDR, {"encoding": "base64"}]})
   data = base64.b64decode(r.json()["result"]["value"]["data"][0])
   hits = [i for i, b in enumerate(data) if b == MAXLTV]
   print("account length:", len(data))
   print("candidate loanToValuePct offsets:", hits)
   PY
   ```

3. KLend stores `loanToValuePct` immediately followed by `liquidationThresholdPct`,
   so the correct `RESERVE_LTV_OFFSET` is the candidate whose **next** byte equals
   that reserve's liquidation-threshold percent. Disambiguate with a second reserve
   that has a different LTV — only the true offset matches both.

4. Update `config.py`: set `RESERVE_LTV_OFFSET` to that index and
   `RESERVE_LIQ_THRESHOLD_OFFSET` to index + 1. The mint `decimals` byte (offset 44,
   after COption mint_authority(36) + supply(8)) only moves if the SPL Token program
   layout changes.

5. Re-derive the exchange-rate offsets the same way — scan the raw account for the
   little-endian integer matching a value you know from the API's `reserves/metrics`,
   and disambiguate with a second reserve:
   - `RESERVE_AVAILABLE_AMOUNT_OFFSET` — a u64 ≈ `(totalSupply - totalBorrow) * 10**decimals`.
   - `RESERVE_BORROWED_AMOUNT_SF_OFFSET` — a u128 that, divided by `FRACTION_SCALE`,
     ≈ `totalBorrow * 10**decimals`.
   - `RESERVE_COLLATERAL_MINT_SUPPLY_OFFSET` — a u64; the cToken supply, slightly
     **below** `totalSupply * 10**decimals` (their ratio is the exchange rate ≥ 1.0).
   The true offsets are the candidates that hold for two different reserves. Sanity
   check: `(available + borrowed) / mint_total_supply` should land just above 1.0
   (e.g. ~1.13 for a long-lived SOL reserve, ~1.00 for a young one).

6. Verify end-to-end: `kamino-liq reserves` must run **without** the layout error and
   the printed liquidation thresholds must match the Kamino app for both the primary
   market and at least one isolated market (so `_check_layout` passes for every
   active reserve). `kamino-liq report <wallet>`'s deposit **amounts** must match the
   Kamino app (so the exchange-rate offsets are right). Then run `.venv/bin/pytest -q`.

Both guards exist to fail loudly rather than silently return wrong numbers — do not
weaken them; fix the offsets.
