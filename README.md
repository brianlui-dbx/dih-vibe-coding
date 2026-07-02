# Sobeys Data Engineering — Coding-Agent Demo (`dih-vibe-coding`)

A hands-on demo repo showing how to make coding agents (Claude Code + the
Databricks Assistant) produce **Sobeys-standard** data-engineering code — modern
Spark Declarative Pipelines (SDP), a medallion architecture, and a Databricks
Asset Bundle (DAB) — by teaching the agent your standards with **instructions**
(`CLAUDE.md`) and **skills** (`skills/`).

## The story this repo tells

1. **Naked agent** — ask for a pipeline with no context → generic, maybe-legacy code.
2. **+ Instructions** (`CLAUDE.md`) — same prompt → Sobeys-standard code; the agent
   even refuses banned legacy-DLT syntax.
3. **+ Skills** (`skills/`) — `/sdp-bronze-ingest` scaffolds a compliant table in
   seconds; `/legacy-dlt-migrate` upgrades old DLT. Repeatable, shareable.
4. **Agent runs the loop** — it writes the DAB, `bundle validate`s, deploys to
   **dev**, reads pipeline events, and fixes its own bugs.
5. **Team scale** — instructions + skills live in Git; every engineer inherits them.

## What's in here

| Path | What it is |
|------|-----------|
| `CLAUDE.md` | The always-on Sobeys DE standards the agent follows every session. |
| `skills/sdp-bronze-ingest/` | Skill: scaffold a standards-compliant Bronze ingestion table. |
| `skills/legacy-dlt-migrate/` | Skill: convert legacy DLT to modern SDP. |
| `src/{bronze,silver,gold}/` | The medallion pipeline (SDP SQL). |
| `resources/*.pipeline.yml` | DAB pipeline resource definition. |
| `databricks.yml` | DAB root: variables + `dev`/`prod` targets. |
| `data_generator/` | Synthetic grocery POS + loyalty data generator. |
| `legacy_example/` | An intentionally-legacy DLT file — the "before" for the migrate demo. |
| `docs/` | Talk track + facilitator guide. |

## The running example

A retail sales medallion pipeline (grocery-relevant for Sobeys):

- **Bronze** `brz_pos_transaction` — raw POS JSON ingested from a UC Volume via Auto Loader.
- **Silver** `slv_pos_transaction` — cleaned, typed, deduped, with data-quality Expectations.
- **Gold** `gld_daily_sales_by_store_category` — daily sales aggregated by store & product
  category (Materialized View, preserves slice dimensions).

## Deploy in your own environment

Everything is parameterized — **nothing about the workspace is hardcoded** (auth comes from
`--profile`). To run this in *your* environment, change **three DAB variables**, defined in
`databricks.yml`:

| Variable | Default | What it is |
|----------|---------|-----------|
| `catalog` | `sobeys_dev` | Unity Catalog the medallion pipeline publishes into. |
| `schema` | `retail` | Domain schema for the tables (layers via `brz_/slv_/gld_` prefixes). |
| `source_path` | `/Volumes/sobeys_dev/landing/pos/` | UC Volume where raw POS JSON lands for Auto Loader. |

> The **landing Volume** (`source_path`) lives in its own `landing` schema — separate from the
> `retail` output schema. Create it once:
> `databricks schemas create landing <catalog> --profile <your-profile>` then
> `databricks volumes create <catalog> landing pos MANAGED --profile <your-profile>`.

Set the variables **either** per-command with `--var` (below) **or** by editing the `default:`
values in `databricks.yml`.

> **Profiles:** this repo uses the placeholder profile **`sobeys-dev`**. Substitute your own
> (e.g. `dbw-brlui-sandbox`) via `--profile`. Never use the `DEFAULT` profile (see `CLAUDE.md`).

```bash
CATALOG=<your_catalog>; SCHEMA=retail; PROFILE=<your-profile>
VOL=/Volumes/$CATALOG/landing/pos/

# 1. Generate sample data (newline-delimited JSON into ./sample_data/)
python data_generator/generate_pos_data.py --rows 50000 --out ./sample_data

# 2. Upload it to your landing Volume
databricks fs cp -r ./sample_data "dbfs:$VOL" --profile $PROFILE

# 3. Validate + deploy to dev, then run the pipeline (override all three vars)
databricks bundle validate --strict -t dev --profile $PROFILE \
  --var catalog=$CATALOG --var schema=$SCHEMA --var source_path=$VOL
databricks bundle deploy   -t dev --profile $PROFILE \
  --var catalog=$CATALOG --var schema=$SCHEMA --var source_path=$VOL
databricks bundle run retail_sales_pipeline -t dev --profile $PROFILE
```

## Reset to a clean slate (rerun the demo)

SDP streaming tables keep **Auto Loader checkpoint state** — stale checkpoints are the #1 cause
of a "dirty" rerun (new sample data silently not re-ingested). Pick one path:

**Quick rerun (keep the pipeline)** — a full refresh resets + recomputes every table from scratch:
```bash
# Optional: replace the landing data first
databricks fs rm -r "dbfs:$VOL" --profile $PROFILE
python data_generator/generate_pos_data.py --rows 50000 --out ./sample_data
databricks fs cp -r ./sample_data "dbfs:$VOL" --profile $PROFILE
# Reset + recompute all tables (clears streaming / Auto Loader state)
databricks bundle run retail_sales_pipeline -t dev --profile $PROFILE --full-refresh-all
```

**Full teardown (cleanest — nothing left behind)**:
```bash
databricks bundle destroy -t dev --profile $PROFILE      # remove the pipeline + deployment
databricks fs rm -r "dbfs:$VOL" --profile $PROFILE        # empty the landing Volume
# Drop the medallion tables so no stale data remains (run in a SQL editor / warehouse):
#   DROP SCHEMA IF EXISTS <catalog>.retail CASCADE;
# Then re-run the Deploy steps above for a pristine environment.
```

## Demo assets

- **Talk track & facilitator guide:** `docs/facilitator-guide.md` (also delivered as a PDF).
- **Slides:** Databricks-branded Google Slides deck (link shared separately).
