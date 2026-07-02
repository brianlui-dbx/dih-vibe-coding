# DLT → SDP migration map (detail)

Every legacy construct and its modern replacement. **Always migrate — never extend
legacy syntax.**

## Imports & decorators

| If you see… | …it's legacy DLT. Migrate to |
|-------------|------------------------------|
| `import dlt` | `from pyspark import pipelines as dp` |
| `@dlt.table(...)` | `@dp.table(...)` |
| `@dlt.view(...)` | `@dp.temporary_view(...)` (modern API has no `view` decorator) |
| `@dlt.expect*` | Same names on `dp.*` (`@dp.expect`, `@dp.expect_or_drop`, `@dp.expect_or_fail`, `@dp.expect_all*`) |

## Reads

| Legacy | Modern |
|--------|--------|
| `dlt.read("name")` | `spark.read.table("name")` |
| `dlt.read_stream("name")` | `spark.readStream.table("name")` |
| `LIVE.name` (SQL) | bare `name` — `SELECT FROM name` (batch) / `SELECT FROM STREAM(name)` (streaming) |
| `input_file_name()` | `_metadata.file_path` (SQL) / `F.col("_metadata.file_path")` (Python) |

## CDC

| Legacy | Modern |
|--------|--------|
| `dlt.apply_changes(...)` | `dp.create_auto_cdc_flow(...)` |
| `dlt.apply_changes_from_snapshot(...)` | `dp.create_auto_cdc_from_snapshot_flow(...)` |
| `APPLY CHANGES INTO ... FROM STREAM ...` (SQL) | `AUTO CDC INTO ... FROM STREAM ...` |

Notes: in `create_auto_cdc_flow`, `sequence_by` accepts a column name (string) or
`col(...)`; `stored_as_scd_type` is integer `2` for Type 2 or string `"1"` for Type 1.
SCD Type 2 history columns are `__START_AT` / `__END_AT` (double underscore); current
rows are `WHERE __END_AT IS NULL`.

## Table definitions (SQL)

| Legacy | Modern |
|--------|--------|
| `CREATE LIVE TABLE` | `CREATE OR REFRESH MATERIALIZED VIEW` |
| `CREATE STREAMING LIVE TABLE` | `CREATE OR REFRESH STREAMING TABLE` |
| `CREATE TEMPORARY LIVE VIEW` | `CREATE TEMPORARY VIEW` |
| `CREATE OR REPLACE STREAMING TABLE` | `CREATE OR REFRESH STREAMING TABLE` (REPLACE is not SDP) |

## Layout

| Legacy | Modern |
|--------|--------|
| `partition_cols=[...]` / `PARTITIONED BY (...)` + `ZORDER` | `cluster_by=[...]` / `CLUSTER BY (...)` (Liquid Clustering) |

## Before / after example

**Before (legacy DLT):**
```python
import dlt

@dlt.table(name="daily_sales", partition_cols=["sale_date"])
def daily_sales():
    return (
        dlt.read("silver_sales")
           .groupBy("store_id", "sale_date")
           .sum("amount")
    )
```

**After (modern SDP):**
```python
from pyspark import pipelines as dp

@dp.materialized_view(name="gld_daily_sales", cluster_by=["sale_date"])
def gld_daily_sales():
    return (
        spark.read.table("slv_sales")
             .groupBy("store_id", "sale_date")
             .sum("amount")
    )
```
