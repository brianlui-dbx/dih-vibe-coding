# Genie Code agent skills

These are **agent skills** for **Databricks Genie Code** — the workspace-native AI coding
agent. They follow the open [Agent Skills](https://agentskills.io) standard: each skill is a
folder with a `SKILL.md` (`name` + `description` frontmatter) and may bundle reference docs,
templates, and scripts.

| Skill | What it does |
|-------|--------------|
| `sdp-bronze-ingest/` | Scaffold a Sobeys-standard Bronze ingestion table (Auto Loader Streaming Table) from a template. |
| `legacy-dlt-migrate/` | Convert legacy DLT code to the modern Spark Declarative Pipelines (SDP) API. |

## Make them discoverable (one-time setup)

Genie Code only discovers skills under an `.assistant/skills/` folder in the workspace:

- **Org-wide (all users):** `/Workspace/.assistant/skills/`
- **Just you:** `/Workspace/Users/<you>/.assistant/skills/`

Copy these skill folders into one of those locations. Fastest path: clone this repo as a
**Git folder** in the workspace, then ask Genie Code to copy `.assistant/skills/*` into your
`/Workspace/Users/<you>/.assistant/skills/` (or have an admin place them under
`/Workspace/.assistant/skills/` for the whole team).

## Use them

- **Automatic** — Genie Code loads a skill when your request matches its `description`.
- **Manual** — invoke by name: `@sdp-bronze-ingest` or `@legacy-dlt-migrate`.

> These skills are the *on-demand* half of the standards. The *always-on* half — the Sobeys
> golden rules — lives in **Settings → Workspace instructions** (see `CLAUDE.md` at the repo
> root, which is the canonical text to paste there).
