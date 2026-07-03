# POS data generator

Generates synthetic grocery **point-of-sale** transactions as newline-delimited JSON
(one JSON object per line), sharded across files, for the retail-sales medallion demo.
Standard library only — no installs needed.

## In-workspace (primary) — `generate_pos_data_notebook.py`

For the all-in-workspace demo, run the **notebook** — it seeds the landing UC Volume
directly, no local CLI. Clone this repo as a Git folder, open
`data_generator/generate_pos_data_notebook.py`, set the widgets, and **Run All** — or just
ask **Genie Code** to run it. It:

- creates the landing schema + volume if missing (`CREATE SCHEMA/VOLUME IF NOT EXISTS`),
- reuses the exact logic in `generate_pos_data.py` (imports its functions — no duplication),
- writes the shards straight into `/Volumes/<catalog>/<landing_schema>/<volume>/`.

| Widget | Default | Meaning |
|--------|---------|---------|
| `catalog` | `sobeys_dev` | Target catalog |
| `landing_schema` | `landing` | Schema that holds the landing volume |
| `volume` | `pos` | Landing volume name |
| `rows` | `50000` | Total records to generate |
| `files` | `4` | Number of shard files |
| `seed` | `42` | RNG seed — same seed produces identical output |

Then point the pipeline's `source_path` (Lakeflow pipeline settings, or the DAB
`source_path` variable) at the same `/Volumes/<catalog>/<landing_schema>/<volume>/` path.

## Local CLI (optional) — `generate_pos_data.py`

The same generator also runs as a standalone script (e.g. for local testing):

```bash
# Defaults: 10,000 rows, 4 shard files, seed 42, into ./sample_data
python data_generator/generate_pos_data.py

# Custom run
python data_generator/generate_pos_data.py --rows 50000 --files 8 --out ./sample_data --seed 7
```

| Flag | Default | Meaning |
|------|---------|---------|
| `--rows` | `10000` | Total records to generate |
| `--out` | `./sample_data` | Output directory |
| `--files` | `4` | Number of shard files (`part-0001.json`, `part-0002.json`, …) |
| `--seed` | `42` | RNG seed — same seed produces identical output |

Output files are `part-0001.json`, `part-0002.json`, … Each line is one record:

```json
{"transaction_id": "…", "store_id": 1007, "store_province": "NS", "transaction_ts": "2026-06-14T09:12:03", "product_id": "SKU-DRY-001", "product_name": "2% Milk 4L", "product_category": "Dairy", "quantity": 2, "unit_price": 5.79, "amount": 11.58, "loyalty_id": "SCENE4820193756", "payment_method": "debit"}
```

## Malformed rows (on purpose)

About **2–3%** of rows are corrupted so the pipeline has real data-quality problems to
catch. The failure modes map directly to the Silver Expectations and Auto Loader's
`_rescued_data`:

| Corruption | Caught by |
|------------|-----------|
| `store_id` = null | `valid_store_id` — dropped |
| zero / negative `quantity` & `amount` | `positive_quantity`, `positive_amount` — warn |
| unparseable `transaction_ts` | casts to `NULL` → `valid_transaction_ts` — dropped |
| `product_category` = null | `known_category` — warn |
| string in a numeric field (`quantity`/`unit_price`/`store_id`) | Auto Loader `_rescued_data` |

## Getting data into the landing Volume

The Bronze table ingests from the UC Volume named by the pipeline's `source_path`
(default `/Volumes/sobeys_dev/landing/pos/`).

- **In-workspace (recommended):** the **notebook above** writes straight into the Volume and
  creates it if needed — nothing else to do.
- **From local CLI output:** if you generated files locally with `generate_pos_data.py`, copy
  them up (the `dbfs:` prefix is required even for UC Volume paths; create the Volume first):
  ```bash
  databricks fs cp -r ./sample_data dbfs:/Volumes/<catalog>/landing/pos/
  ```

Point the pipeline's `source_path` (Lakeflow pipeline settings, or the DAB `source_path`
variable) at the same location.
