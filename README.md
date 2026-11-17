# convertingToCfd

Converts Gamma Engine [IB15] levels quoted on the **NQ** futures contract (`NQ1!`) into the matching **US100** CFD levels.

The two instruments track the same index but trade at different prices. The tool measures the gap (the *basis*) and shifts every price level by it:

```text
basis       = NQ price - US100 price
US100 level = NQ level - basis
```

It is a converter only. It never places trades or talks to a broker.

## Install

```bash
pip install -r requirements.txt
```

## Run

```bash
python converter.py             # live prices from your market data API
python converter.py --manual    # type the NQ and US100 prices yourself
python converter.py --save      # also save the result in output/
python converter.py --no-copy   # skip the copy-to-clipboard prompt
```

Paste the Gamma Engine block when asked, then press Enter on an empty line.

### Example

With NQ at 21000 and US100 at 20950 (basis 50):

Input:

```text
B, 21500
E, 21100, 20900
R, 1.25
```

Output:

```text
B, 21450
E, 21050, 20850
R, 1.25
```

Only the fields that are prices for each label are converted (see `LABEL_PRICE_INDICES` in `parser.py`). Everything else, and any line that cannot be parsed, is passed through unchanged, with a warning for lines it could not read.

## Live prices

Live mode reads its settings from environment variables or a `.env` file. Copy `.env.example` to `.env` and fill in:

| Variable | Meaning |
|---|---|
| `MARKET_DATA_API_URL` | Endpoint that returns a price for `?symbol=...` |
| `MARKET_DATA_API_KEY` | Sent as `Authorization: Bearer <key>` (optional for public endpoints) |
| `NQ_SYMBOL` | Your provider's symbol for the NQ contract |
| `US100_SYMBOL` | Your provider's symbol for US100 |

If live data is not configured or the request fails, use `--manual`.

## Tests

```bash
pytest
```
