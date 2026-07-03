---
name: sdp-bronze-ingest
description: Scaffold a Sobeys-standard Bronze ingestion table for Spark Declarative
  Pipelines — an Auto Loader streaming table from cloud files / a UC Volume with ingest
  metadata, rescued-data handling, and team naming/layout. Use when adding a new raw
  source to the medallion architecture.
---

# Bronze Ingestion Table (Sobeys standard)

## When to use

Adding a new raw source (POS extracts, inventory feeds, loyalty events) to the Bronze
layer of the medallion architecture.

## Steps

1. Ask for: source path (Volume / cloud), file format, target catalog/schema, dataset name.
2. Copy `templates/bronze_table.sql.tmpl` → `src/bronze/brz_<dataset>.sql`, fill placeholders.
3. Ingest with `STREAM read_files(...)`; keep `_rescued_data`; add `_ingest_ts` and `_source_file`.
4. Ensure the file lives under the pipeline's source folder (`src/bronze/`) so the Lakeflow
   Pipelines Editor picks it up via its `src/**` glob.
5. Verify in-workspace: run the pipeline in the Lakeflow Pipelines Editor (or ask Genie Code
   to run it) and confirm it completes green. Genie Code is governed by your Unity Catalog
   permissions — no CLI or profile needed.

## Rules (must follow — see `references/bronze-standards.md`)

- **Streaming Table + Auto Loader only** — raw is append-only.
- **No transforms** beyond typing + ingest metadata in Bronze. Cleaning happens in Silver.
- Names `brz_<domain_noun>`, snake_case, Unity Catalog only (never DBFS).
- Keep the `_rescued_data` column so malformed records are never silently lost.
- `CLUSTER BY AUTO` unless the predicate columns are already known.

See `references/bronze-standards.md` for the full ruleset and a filled example.
