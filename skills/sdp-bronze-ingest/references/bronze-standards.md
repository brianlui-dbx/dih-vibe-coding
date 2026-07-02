# Bronze layer standards (detail)

The Bronze layer is the **raw, append-only landing zone**. Its only job is to get
source data into Unity Catalog reliably, with enough lineage metadata to debug and
reprocess. All cleaning, typing, and business logic happen downstream in Silver/Gold.

## Hard rules

1. **Streaming Table + Auto Loader.** Bronze reads files incrementally with
   `FROM STREAM read_files(...)`. It is append-only — never an aggregate, never a
   Materialized View.
2. **Preserve everything.** Do `SELECT *` from the source plus metadata columns.
   Never drop or rename source columns in Bronze.
3. **Keep `_rescued_data`.** Auto Loader captures malformed / unexpected data here.
   Never discard it in Bronze — Silver decides what to do with it.
4. **Ingest metadata is mandatory:**
   - `_ingest_ts` = `current_timestamp()`
   - `_source_file` = `_metadata.file_path`  (NOT the legacy `input_file_name()`)
5. **Naming:** `brz_<domain_noun>` (snake_case, singular). Unity Catalog only.
6. **Layout:** `CLUSTER BY AUTO` (Liquid Clustering). Never `PARTITIONED BY` + `ZORDER`.

## Filled example

```sql
CREATE OR REFRESH STREAMING TABLE brz_pos_transaction
  COMMENT 'Bronze raw ingest of point-of-sale transaction extracts'
  CLUSTER BY AUTO
AS
SELECT
  *,
  current_timestamp()   AS _ingest_ts,
  _metadata.file_path   AS _source_file
FROM STREAM read_files(
  '/Volumes/sobeys_dev/landing/pos/',
  format => 'json'
);
```

## Common mistakes to avoid

- Using `read_files(...)` without `STREAM` → creates a batch query and errors
  ("Cannot create streaming table from batch query"). Always `FROM STREAM read_files(...)`.
- Adding filtering / joins in Bronze → push that to Silver.
- Forgetting `_rescued_data` handling → malformed rows silently lost.
- Hardcoding a catalog in the dataset name → let the pipeline's default catalog/schema
  (set via DAB variables) place the table.

## Validate

```bash
databricks bundle validate --strict --profile sobeys-dev
```
