# INTENTIONALLY LEGACY DLT - do NOT modernize. This is the 'before' example for the /legacy-dlt-migrate skill demo.
#
# This is a plausible "old" Sobeys daily-sales pipeline written in the LEGACY
# Databricks DLT API. It intentionally uses banned constructs (import dlt, @dlt.*,
# partition_cols, dlt.read/dlt.read_stream, LIVE. prefixes, input_file_name(), and
# dlt.apply_changes) so the /legacy-dlt-migrate skill has a realistic artifact to
# convert into the modern SDP medallion pipeline under src/.
#
# It lives OUTSIDE src/ on purpose, so the Spark Declarative Pipeline never loads it.
# Do NOT deploy or run this file. See skills/legacy-dlt-migrate/ for the mapping to
# the modern equivalents (brz_/slv_/gld_ tables in src/).

import dlt
from pyspark.sql.functions import col, current_timestamp, input_file_name, to_date

# --- Bronze: raw POS ingest -------------------------------------------------------
# LEGACY: @dlt.table + input_file_name(). Modern: CREATE OR REFRESH STREAMING TABLE
# with _metadata.file_path (see src/bronze/brz_pos_transaction.sql).
@dlt.table(
    name="bronze_pos_transaction",
    comment="Raw POS ingest (LEGACY DLT).",
)
def bronze_pos_transaction():
    return (
        spark.readStream.format("cloudFiles")  # noqa: F821 (spark provided at runtime)
        .option("cloudFiles.format", "json")
        .load("/Volumes/sobeys_dev/landing/pos/")
        .withColumn("_ingest_ts", current_timestamp())
        .withColumn("_source_file", input_file_name())  # LEGACY: -> _metadata.file_path
    )


# --- Silver: dedup to latest row per transaction via APPLY CHANGES ----------------
# LEGACY: dlt.create_streaming_table + dlt.apply_changes (SCD 1).
# Modern: dp.create_streaming_table + dp.create_auto_cdc_flow / AUTO CDC INTO.
dlt.create_streaming_table("silver_pos_transaction")

dlt.apply_changes(
    target="silver_pos_transaction",
    source="bronze_pos_transaction",
    keys=["transaction_id"],
    sequence_by=col("_ingest_ts"),
    stored_as_scd_type=1,
)


# --- Silver clean: typed + quality-checked ----------------------------------------
# LEGACY: @dlt.expect* + @dlt.view + dlt.read_stream. Modern: CONSTRAINT ... EXPECT
# on a CREATE OR REFRESH STREAMING TABLE reading FROM STREAM(...).
@dlt.expect_or_drop("valid_store_id", "store_id IS NOT NULL")
@dlt.expect("positive_amount", "amount > 0")
@dlt.view(name="silver_pos_clean")
def silver_pos_clean():
    return (
        dlt.read_stream("silver_pos_transaction")  # LEGACY: -> spark.readStream.table(...)
        .withColumn("sale_date", to_date(col("transaction_ts")))
    )


# --- Gold: daily sales rollup by store & category ---------------------------------
# LEGACY: @dlt.table(partition_cols=...) + dlt.read + a LIVE. reference.
# Modern: CREATE OR REFRESH MATERIALIZED VIEW ... CLUSTER BY (...) with a batch read
# (see src/gold/gld_daily_sales_by_store_category.sql).
@dlt.table(
    name="daily_sales_by_store_category",
    comment="Daily sales rollup (LEGACY DLT).",
    partition_cols=["sale_date"],  # LEGACY: -> CLUSTER BY (sale_date, store_id)
)
def daily_sales_by_store_category():
    silver = spark.read.table("LIVE.silver_pos_clean")  # noqa: F821  LEGACY LIVE. prefix
    return (
        silver.groupBy("store_id", "store_province", "product_category", "sale_date")
        .sum("amount")
        .withColumnRenamed("sum(amount)", "total_sales")
    )
