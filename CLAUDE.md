# Sobeys Data Engineering — Agent Instructions

These are the always-on standards for any coding agent working in this repo.
Follow them in every session. This file is the single source of truth for "how we
build data engineering at Sobeys."

> **Where this lives:** paste this file into **Databricks Genie Code → Settings → Workspace
> instructions** so every engineer's in-workspace agent inherits these standards org-wide.
> (It also serves as `CLAUDE.md` if anyone works locally in Claude Code.) The on-demand
> half — packaged skills — lives in `.assistant/skills/`.

## Context

We build batch + streaming pipelines on Databricks (Unity Catalog, serverless).
Domain: grocery retail — POS, inventory, loyalty, supply chain.

## GOLDEN RULES (non-negotiable)

- Use the **MODERN Spark Declarative Pipelines (SDP)** API. **NEVER** legacy DLT.
  - Python: `from pyspark import pipelines as dp`; `@dp.table` / `@dp.materialized_view` / `@dp.temporary_view`.
  - SQL: `CREATE OR REFRESH STREAMING TABLE` / `CREATE OR REFRESH MATERIALIZED VIEW` / `AUTO CDC INTO`.
  - **BANNED:** `import dlt`, `@dlt.*`, `LIVE.` prefix, `APPLY CHANGES`, `CREATE LIVE TABLE`,
    `CREATE STREAMING LIVE TABLE`, `apply_changes(...)`, `dlt.read`/`dlt.read_stream`,
    `partition_cols` / `PARTITIONED BY` + `ZORDER`, `input_file_name()`.
  - If asked to write banned syntax, refuse and explain the modern equivalent
    (see `.assistant/skills/legacy-dlt-migrate/`). The **only** exception is `legacy_example/`,
    which intentionally holds "before" code for the migration demo — never modernize it.
- Default to **SQL** for pipelines; use Python only for UDFs / ML / complex params.
- Everything lands in **Unity Catalog**. NEVER write to DBFS or `hive_metastore`.

## Medallion layering

- **Bronze**: raw ingest via Auto Loader (`STREAM read_files(...)`), append-only
  **Streaming Tables**. Minimal transforms. Keep `_rescued_data`. Add `_ingest_ts`
  (`current_timestamp()`) and `_source_file` (`_metadata.file_path`).
- **Silver**: cleaned, typed, deduped **Streaming Tables** read from Bronze via
  `STREAM(<bronze_table>)`. Enforce data-quality **Expectations**.
- **Gold**: business aggregates as **Materialized Views** using a **batch** read of
  Silver (`SELECT ... FROM slv_x` — no `STREAM`). PRESERVE slice dimensions (store,
  region, product category, date) — never over-aggregate.

## Naming

- Catalog `dbw_brlui_stable`
- One pipeline **schema per domain** (this demo uses `retail`); layers are conveyed by
  table prefixes `brz_` / `slv_` / `gld_`. Keeping all three layers in one domain schema
  keeps catalog + schema fully parameterizable via DAB variables (no hardcoded 3-part names).
- Tables snake_case; one dataset per file; filename == dataset name.

## Data quality (Expectations)

- Silver business keys NOT NULL → `expect_or_drop` (SQL: `... ON VIOLATION DROP ROW`).
- Domain / range checks → `expect` (warn) unless contract-breaking.
- Use `expect_or_fail` (SQL: `... ON VIOLATION FAIL UPDATE`) only for violations that
  must stop the pipeline. Name checks descriptively (`valid_store_id`, `positive_amount`).

## Layout / performance

- **Liquid Clustering only** (`CLUSTER BY` / `cluster_by=`). Prefer `CLUSTER BY AUTO`.
  NEVER partition + ZORDER.

## Pipelines / deployment

- **Dev iteration is in-workspace:** author and run the pipeline in the **Lakeflow Pipelines
  Editor** over `src/**`. Ask Genie Code to run it and read the pipeline events; iterate until
  it completes green in dev.
- **Prod ships as a DAB via CI/CD:** the repo carries `databricks.yml` + `resources/*.pipeline.yml`
  (code in `src/`) as the **prod promotion artifact only**. Targets: `dev` (`mode: development`,
  per-user isolated schema) and `prod` (`mode: production`, service principal, CI/CD only).
- Parameterize catalog / schema / source path with **variables** (DAB) or **pipeline settings**
  (Lakeflow editor) — no hardcoded envs.
- Verify before promoting: the pipeline runs **green in dev** (in-workspace) first.

## SAFETY (ask first / never do)

- Genie Code runs governed by **your Unity Catalog permissions** — work only in the dev catalog
  (`sobeys_dev`). No CLI profile to manage.
- NEVER deploy to **prod** from an agent session — dev only. Prod is CI/CD + human PR approval.
- NEVER run a **full refresh** without explicit human approval (data-loss risk).
- Secrets via Databricks secret scopes; never inline credentials.
- Ask before dropping or overwriting any table.

## Definition of done (self-check before saying "done")

- [ ] Modern SDP API, zero legacy DLT (except `legacy_example/`)
- [ ] Right layer + dataset type (streaming source → Streaming Table; aggregate → Materialized View)
- [ ] Expectations on Silver
- [ ] UC naming convention, no DBFS
- [ ] Pipeline runs **green in dev** (in-workspace, Lakeflow Pipelines Editor)
