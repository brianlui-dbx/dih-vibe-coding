# Sobeys Data Engineering — Genie Code Demo (`dih-vibe-coding`)

A hands-on demo showing how to make **Databricks Genie Code** — the workspace-native AI
coding agent — produce **Sobeys-standard** data-engineering code: modern Spark Declarative
Pipelines (SDP), a medallion architecture, and a Databricks Asset Bundle (DAB) for prod. It
all runs **inside the Databricks workspace** — no laptop, no local CLI — by teaching the
agent your standards with **Workspace instructions** and **skills** (`.assistant/skills/`).

> Everything here runs in-workspace with Genie Code. (The same standards double as a
> `CLAUDE.md` for anyone doing local IDE/repo work in Claude Code, but that's not the demo.)

## The story this repo tells

1. **Naked agent** — ask Genie Code for a pipeline with no standards loaded → generic,
   maybe-legacy code.
2. **+ Workspace instructions** (`CLAUDE.md` pasted into Settings) — same prompt →
   Sobeys-standard code; the agent even **refuses** banned legacy-DLT syntax.
3. **+ Skills** (`.assistant/skills/`) — `@sdp-bronze-ingest` scaffolds a compliant table in
   seconds; `@legacy-dlt-migrate` upgrades old DLT. Repeatable, shareable.
4. **Agent runs the loop** — Genie Code writes the SDP SQL in the **Lakeflow Pipelines
   Editor**, runs the pipeline, reads the events, and fixes its own bug — governed by your
   Unity Catalog permissions.
5. **Team scale** — Workspace instructions (org-wide) + skills in Git; every engineer's
   in-workspace agent inherits them.

## What's in here

| Path | What it is |
|------|-----------|
| `CLAUDE.md` | The always-on Sobeys DE standards — paste into **Genie Code → Settings → Workspace instructions**. |
| `.assistant/skills/sdp-bronze-ingest/` | Skill: scaffold a standards-compliant Bronze ingestion table. |
| `.assistant/skills/legacy-dlt-migrate/` | Skill: convert legacy DLT to modern SDP. |
| `.assistant/skills/README.md` | How Genie Code discovers + invokes these skills. |
| `src/{bronze,silver,gold}/` | The medallion pipeline (SDP SQL) — the Lakeflow editor's source. |
| `resources/*.pipeline.yml` | DAB pipeline resource definition (prod promotion). |
| `databricks.yml` | DAB root: variables + `dev`/`prod` targets (prod CI/CD). |
| `data_generator/` | POS data generator — an in-workspace **notebook** + a local CLI script. |
| `legacy_example/` | An intentionally-legacy DLT file — the "before" for the migrate demo. |
| `docs/` | Talk track + facilitator guide (**local-only — not pushed to the remote**). |

## The running example

A retail sales medallion pipeline (grocery-relevant for Sobeys):

- **Bronze** `brz_pos_transaction` — raw POS JSON ingested from a UC Volume via Auto Loader.
- **Silver** `slv_pos_transaction` — cleaned, typed, deduped, with data-quality Expectations.
- **Gold** `gld_daily_sales_by_store_category` — daily sales aggregated by store & product
  category (Materialized View, preserves slice dimensions).

## Run it in your workspace

Everything runs in the Databricks workspace and is fully parameterized — nothing about the
environment is hardcoded, and Genie Code is governed by your own Unity Catalog permissions.

1. **Clone as a Git folder.** In your workspace: **Workspace → Repos/Git folders → Add** this
   repo. That brings `CLAUDE.md`, `.assistant/skills/`, `src/**`, the data generator, and the
   DAB into the workspace.

2. **Load the standards (once).** Copy `CLAUDE.md` into **Genie Code → Settings → Workspace
   instructions** (org-wide) — now every session codes to the Sobeys standards.

3. **Install the skills (once).** Copy the skill folders into a discovery path so Genie Code
   finds them — `/Workspace/.assistant/skills/` (org-wide) or
   `/Workspace/Users/<you>/.assistant/skills/` (just you). You can ask Genie Code to do the
   copy. See `.assistant/skills/README.md`. Invoke via `@sdp-bronze-ingest` /
   `@legacy-dlt-migrate`, or let Genie Code pick them automatically.

4. **Seed the landing Volume.** Open `data_generator/generate_pos_data_notebook.py`, set the
   widgets (`catalog`, `landing_schema`, `volume`, `rows`), and **Run All** — or ask Genie
   Code to run it. It creates the schema + volume and writes POS JSON into
   `/Volumes/<catalog>/<landing_schema>/<volume>/`.

5. **Build + run the pipeline (dev, in-workspace).** In the **Lakeflow Pipelines Editor**,
   create a pipeline over this repo's `src/**`, set its **catalog**, **schema** (`retail`),
   and **`source_path`** configuration to your landing Volume, then **Run**. Ask Genie Code to
   run it and read the events; iterate until it completes green. These three settings are the
   only per-environment values:

   | Setting | Default | What it is |
   |---------|---------|-----------|
   | `catalog` | `dbw_brlui_stable` | Unity Catalog the medallion pipeline publishes into. |
   | `schema` | `retail` | Domain schema for the tables (layers via `brz_/slv_/gld_` prefixes). |
   | `source_path` | `/Volumes/dbw_brlui_stable/landing/` | UC Volume where raw POS JSON lands for Auto Loader. |

   > The **landing Volume** (`source_path`) lives in its own `landing` schema — separate from
   > the `retail` output schema. The data-gen notebook creates it for you.

6. **Promote to prod via CI/CD (not from the agent).** The repo ships `databricks.yml` +
   `resources/*.pipeline.yml` as the prod promotion artifact. The same three values are DAB
   variables (defaults in `databricks.yml`); prod is deployed by CI/CD + human PR approval
   only — never from an agent session.

## Reset to a clean slate (rerun the demo)

SDP streaming tables keep **Auto Loader checkpoint state** — stale checkpoints are the #1
cause of a "dirty" rerun (new sample data silently not re-ingested). All in-workspace:

**Quick rerun (keep the pipeline)** — a full refresh resets + recomputes every table from
scratch (needs human approval; data-loss risk):
1. Optionally re-run the data-gen notebook to refresh the landing Volume (same widgets).
2. In the Lakeflow Pipelines Editor, choose **Full refresh** (all tables), then **Run**. This
   clears streaming / Auto Loader state and recomputes from the current landing data.

**Full teardown (cleanest — nothing left behind):**
1. Delete the pipeline in the Lakeflow Pipelines Editor.
2. Drop the medallion tables in the SQL editor: `DROP SCHEMA IF EXISTS <catalog>.retail CASCADE;`
3. Empty the landing Volume (delete files under `/Volumes/<catalog>/<schema>/landing/`), then
   re-run steps 4–5 above for a pristine environment.
