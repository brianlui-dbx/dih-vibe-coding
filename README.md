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

## Run it (rehearsal)

> **Profiles:** this repo uses the placeholder profile name **`sobeys-dev`** to model
> Sobeys' own setup. When *you* rehearse, substitute your own profile (e.g.
> `dbw-brlui-sandbox`) and point the `catalog` variable at a catalog you can write to.

```bash
# 1. Generate sample data (newline-delimited JSON into ./sample_data/)
python data_generator/generate_pos_data.py --rows 50000 --out ./sample_data

# 2. Upload it to your landing Volume
databricks fs cp -r ./sample_data dbfs:/Volumes/<catalog>/landing/pos/ --profile <your-profile>

# 3. Validate + deploy the bundle to dev, then run the pipeline
databricks bundle validate --strict -t dev --profile <your-profile>
databricks bundle deploy -t dev --profile <your-profile>
databricks bundle run retail_sales_pipeline -t dev --profile <your-profile>
```

## Demo assets

- **Talk track & facilitator guide:** `docs/facilitator-guide.md` (also delivered as a PDF).
- **Slides:** Databricks-branded Google Slides deck (link shared separately).
