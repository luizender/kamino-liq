---
name: verify-onchain-layout
description: Re-derive and verify the KLend Reserve and SPL-mint byte offsets in config.py against a live on-chain account — use after a Kamino program upgrade makes the tool fail with "KLend reserve layout changed".
disable-model-invocation: true
---

# Verify on-chain layout

`kamino-liq` reads two values the REST API doesn't expose from on-chain accounts
at fixed byte offsets (`kamino_liq/config.py`):

- `RESERVE_LTV_OFFSET = 4872` — `ReserveConfig.loanToValuePct` (u8), read **only**
  to cross-check the layout against the API's `maxLtv`.
- `RESERVE_LIQ_THRESHOLD_OFFSET = 4873` — `ReserveConfig.liquidationThresholdPct` (u8).
- `MINT_DECIMALS_OFFSET = 44` — the SPL-mint `decimals` byte.

`chain.py::_check_layout` raises `KLend reserve layout changed …` when
`byte[4872] != round(maxLtv * 100)`. That means a program upgrade shifted the
struct. Use this procedure to find the new offsets.

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

5. Verify end-to-end: `kamino-liq reserves` must run **without** the layout error and
   the printed liquidation thresholds must match the Kamino app for both the primary
   market and at least one isolated market (so `_check_layout` passes for every
   active reserve). Then run `.venv/bin/pytest -q`.

The cross-check exists to fail loudly rather than silently return a wrong threshold —
do not weaken it; fix the offsets.
