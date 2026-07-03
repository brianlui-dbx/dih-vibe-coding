# Databricks notebook source
# MAGIC %md
# MAGIC # POS data generator (in-workspace)
# MAGIC
# MAGIC Seeds the retail-sales demo's **landing UC Volume** with synthetic grocery POS
# MAGIC transactions as newline-delimited JSON — everything in the workspace, no local CLI.
# MAGIC
# MAGIC It reuses the exact generator logic in `generate_pos_data.py` (same folder) and writes
# MAGIC the shards **directly** into `/Volumes/<catalog>/<landing_schema>/<volume>/`, creating
# MAGIC the schema and volume if they don't exist. About 2–3% of rows are malformed on purpose
# MAGIC so Silver Expectations and Auto Loader's `_rescued_data` have something real to catch.
# MAGIC
# MAGIC **How to run:** clone this repo as a Git folder, open this notebook, set the widgets,
# MAGIC and Run All — or just ask **Genie Code** to run it. Governed by your Unity Catalog
# MAGIC permissions.

# COMMAND ----------

dbutils.widgets.text("catalog", "sobeys_dev", "Target catalog")
dbutils.widgets.text("landing_schema", "landing", "Landing schema")
dbutils.widgets.text("volume", "pos", "Landing volume")
dbutils.widgets.text("rows", "50000", "Rows to generate")
dbutils.widgets.text("files", "4", "Shard files")
dbutils.widgets.text("seed", "42", "RNG seed")

catalog = dbutils.widgets.get("catalog")
landing_schema = dbutils.widgets.get("landing_schema")
volume = dbutils.widgets.get("volume")
rows = int(dbutils.widgets.get("rows"))
files = int(dbutils.widgets.get("files"))
seed = int(dbutils.widgets.get("seed"))

volume_path = f"/Volumes/{catalog}/{landing_schema}/{volume}"
print(f"Target Volume: {volume_path}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Create the landing schema + volume (idempotent)
# MAGIC The landing Volume lives in its own `landing` schema — separate from the `retail`
# MAGIC output schema the pipeline publishes into.

# COMMAND ----------

spark.sql(f"CREATE SCHEMA IF NOT EXISTS `{catalog}`.`{landing_schema}`")
spark.sql(f"CREATE VOLUME IF NOT EXISTS `{catalog}`.`{landing_schema}`.`{volume}`")
print(f"Ready: `{catalog}`.`{landing_schema}`.`{volume}`")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Generate and write NDJSON shards into the Volume
# MAGIC Reuses `build_catalog`, `assign_store_provinces`, `make_record`, `corrupt`, and
# MAGIC `shard_sizes` from `generate_pos_data.py` — no logic is duplicated here.

# COMMAND ----------

import os
import sys
import json
import random

# The notebook's own directory is on sys.path in a Git folder, so the sibling module
# imports directly; add it explicitly as a fallback for other layouts.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)) if "__file__" in dir() else os.getcwd())
import generate_pos_data as g

if rows < 1 or files < 1:
    raise ValueError("rows and files must both be >= 1")

rng = random.Random(seed)
product_catalog = g.build_catalog()
store_provinces = g.assign_store_provinces(rng)

sizes = g.shard_sizes(rows, files)
malformed = 0
files_written = 0

for shard_no, size in enumerate(sizes, start=1):
    if size == 0:
        continue  # more files than rows: skip empty shards
    path = f"{volume_path}/part-{shard_no:04d}.json"
    with open(path, "w", encoding="utf-8") as fh:
        for _ in range(size):
            rec = g.make_record(rng, product_catalog, store_provinces)
            if rng.random() < g.MALFORMED_RATE:
                g.corrupt(rng, rec)
                malformed += 1
            fh.write(json.dumps(rec) + "\n")
    files_written += 1

pct = (malformed / rows) * 100 if rows else 0.0
print("POS data generation complete.")
print(f"  rows written : {rows}")
print(f"  files        : {files_written} (part-0001.json .. part-{files_written:04d}.json)")
print(f"  malformed    : {malformed} ({pct:.2f}%)")
print(f"  volume       : {volume_path}")
print(f"  seed         : {seed}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Verify what landed
# MAGIC Point the pipeline's `source_path` (Lakeflow pipeline settings, or the DAB
# MAGIC `source_path` variable) at this same Volume path, then run the pipeline.

# COMMAND ----------

display(dbutils.fs.ls(volume_path))
