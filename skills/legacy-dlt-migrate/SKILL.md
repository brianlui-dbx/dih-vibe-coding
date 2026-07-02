---
name: legacy-dlt-migrate
description: Convert legacy Databricks DLT pipeline code to the modern Spark Declarative
  Pipelines (SDP) API used at Sobeys. Use when you see `import dlt`, `@dlt.*`, `LIVE.`
  prefixes, `APPLY CHANGES`, `CREATE LIVE TABLE`, `apply_changes`, or `partition_cols`
  / ZORDER and need to upgrade it.
---

# Legacy DLT → Modern SDP migration (Sobeys standard)

## When to use

Upgrading any older pipeline written in the legacy DLT API to the modern Spark
Declarative Pipelines API mandated by `CLAUDE.md`.

## Steps

1. Read the source file and identify every legacy construct (see the mapping in
   `references/dlt-migration-map.md`).
2. Rewrite symbol-by-symbol to the modern API. Do **not** extend or "improve" the
   legacy syntax — replace it.
3. Preserve behavior: SCD type, sequencing columns, expectations, and clustering keys
   must be semantically equivalent after migration.
4. Re-check against `CLAUDE.md`: correct medallion layer, dataset type, naming.
5. Validate: `databricks bundle validate --strict --profile sobeys-dev`.

## Quick mapping (full table in `references/dlt-migration-map.md`)

| Legacy DLT | Modern SDP |
|------------|-----------|
| `import dlt` | `from pyspark import pipelines as dp` |
| `@dlt.table` | `@dp.table` |
| `@dlt.view` | `@dp.temporary_view` |
| `dlt.read("x")` / `dlt.read_stream("x")` | `spark.read.table("x")` / `spark.readStream.table("x")` |
| `dlt.apply_changes(...)` | `dp.create_auto_cdc_flow(...)` |
| `LIVE.x` | bare `x` |
| `CREATE LIVE TABLE` | `CREATE OR REFRESH MATERIALIZED VIEW` |
| `CREATE STREAMING LIVE TABLE` | `CREATE OR REFRESH STREAMING TABLE` |
| `APPLY CHANGES INTO` | `AUTO CDC INTO` |
| `partition_cols` / `PARTITIONED BY` + `ZORDER` | `cluster_by` / `CLUSTER BY` |
| `input_file_name()` | `_metadata.file_path` |

Try it on `legacy_example/daily_sales_dlt.py` in this repo.
