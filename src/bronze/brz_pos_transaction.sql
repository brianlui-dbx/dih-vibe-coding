-- Bronze: raw POS transaction ingest via Auto Loader (append-only Streaming Table).
-- Minimal transforms — SELECT * plus ingest metadata. Cleaning/typing happens in Silver.
-- Keeps Auto Loader's _rescued_data column so malformed values are never silently lost.
-- Source path is injected from the pipeline configuration value ${source_path} (set in the DAB).
CREATE OR REFRESH STREAMING TABLE brz_pos_transaction
  COMMENT 'Bronze raw ingest of point-of-sale transaction extracts (Auto Loader, append-only).'
  CLUSTER BY AUTO
AS SELECT
  *,
  current_timestamp()   AS _ingest_ts,
  _metadata.file_path   AS _source_file
FROM STREAM read_files(
  '${source_path}',
  format => 'json'
);
