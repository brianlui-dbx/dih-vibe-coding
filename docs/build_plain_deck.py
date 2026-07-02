#!/usr/bin/env python3
"""
Build a PLAIN (non-corporate-template) Databricks-colored Google Slides deck
for the Sobeys x Databricks "Coding Agents for Data Engineering" demo.

Why this exists: the FE Slides skill's `create-from-spec` is hardwired to the
Databricks corporate template file, which 404s for this Google identity. This
script instead creates a genuinely blank presentation and renders every slide
with custom text boxes + shapes styled in the Databricks brand palette, reusing
the tested low-level helpers (auth, api_call, batch_update) from gslides_builder.

Run:  PYTHONPATH= python3 docs/build_plain_deck.py
"""
import sys, os, json

RES = "/Users/brian.lui/.vibe/marketplace/plugins/fe-google-tools/skills/google-slides/resources"
sys.path.insert(0, RES)
import gslides_builder as gb  # noqa: E402

C = gb.DATABRICKS_COLORS
FONT = "Arial"


def emu(i):  # inches -> EMU
    return gb.inches_to_emu(i)


def gid():
    return gb.generate_id()


def bg(page, color):
    return {"updatePageProperties": {
        "objectId": page,
        "pageProperties": {"pageBackgroundFill": {"solidFill": {"color": {"rgbColor": color}}}},
        "fields": "pageBackgroundFill"}}


def rect(page, x, y, w, h, color):
    oid = gid()
    reqs = [
        {"createShape": {"objectId": oid, "shapeType": "RECTANGLE",
                         "elementProperties": {"pageObjectId": page,
                                               "size": {"width": {"magnitude": emu(w), "unit": "EMU"},
                                                        "height": {"magnitude": emu(h), "unit": "EMU"}},
                                               "transform": {"scaleX": 1, "scaleY": 1,
                                                             "translateX": emu(x), "translateY": emu(y),
                                                             "unit": "EMU"}}}},
        {"updateShapeProperties": {"objectId": oid,
                                   "shapeProperties": {"shapeBackgroundFill": {"solidFill": {"color": {"rgbColor": color}}},
                                                       "outline": {"propertyState": "NOT_RENDERED"}},
                                   "fields": "shapeBackgroundFill,outline.propertyState"}},
    ]
    return reqs


def txt(page, text, x, y, w, h, size, color, bold=False, align=None,
        bullets=False, line_spacing=115, space_below=6, valign=None):
    oid = gid()
    ep = {"pageObjectId": page,
          "size": {"width": {"magnitude": emu(w), "unit": "EMU"},
                   "height": {"magnitude": emu(h), "unit": "EMU"}},
          "transform": {"scaleX": 1, "scaleY": 1,
                        "translateX": emu(x), "translateY": emu(y), "unit": "EMU"}}
    reqs = [{"createShape": {"objectId": oid, "shapeType": "TEXT_BOX", "elementProperties": ep}}]
    if valign:
        reqs.append({"updateShapeProperties": {"objectId": oid,
                     "shapeProperties": {"contentAlignment": valign},
                     "fields": "contentAlignment"}})
    reqs.append({"insertText": {"objectId": oid, "text": text}})
    reqs.append({"updateTextStyle": {"objectId": oid, "textRange": {"type": "ALL"},
                 "style": {"fontSize": {"magnitude": size, "unit": "PT"}, "bold": bold,
                           "fontFamily": FONT,
                           "foregroundColor": {"opaqueColor": {"rgbColor": color}}},
                 "fields": "fontSize,bold,fontFamily,foregroundColor"}})
    pstyle = {"lineSpacing": line_spacing,
              "spaceBelow": {"magnitude": space_below, "unit": "PT"}}
    pfields = ["lineSpacing", "spaceBelow"]
    if align:
        pstyle["alignment"] = align
        pfields.append("alignment")
    reqs.append({"updateParagraphStyle": {"objectId": oid, "textRange": {"type": "ALL"},
                 "style": pstyle, "fields": ",".join(pfields)}})
    if bullets:
        reqs.append({"createParagraphBullets": {"objectId": oid, "textRange": {"type": "ALL"},
                     "bulletPreset": "BULLET_DISC_CIRCLE_SQUARE"}})
    return reqs


def main():
    title = "Coding Agents for Data Engineering — Sobeys × Databricks (Demo)"
    pres = gb.create_presentation(title)
    info = gb.get_presentation(pres)
    ps = info["pageSize"]
    W = ps["width"]["magnitude"] / gb.EMU_PER_INCH
    H = ps["height"]["magnitude"] / gb.EMU_PER_INCH
    print(f"Created {pres}  |  page {W:.2f}in x {H:.2f}in")

    # Remove any auto-created slides so we start clean.
    del_reqs = [{"deleteObject": {"objectId": s["objectId"]}} for s in info.get("slides", [])]
    if del_reqs:
        gb.batch_update(pres, del_reqs)

    LM = 0.62
    CW = W - 2 * LM

    def new_page():
        r = gb.add_slide(pres, layout="BLANK")
        return r["pageId"]

    def footer(page, idx):
        reqs = txt(page, "Sobeys × Databricks · Coding Agents for Data Engineering",
                   LM, H - 0.42, CW - 0.8, 0.3, 9, C["gray"])
        reqs += txt(page, str(idx), W - 0.9, H - 0.42, 0.4, 0.3, 9, C["gray"], align="END")
        return reqs

    def dark_cover(title_txt, subtitle_txt, eyebrow=None, foot=None):
        page = new_page()
        reqs = [bg(page, C["dark_teal"])]
        y = 0.34 * H
        if eyebrow:
            reqs += txt(page, eyebrow, LM, y - 0.42, CW, 0.35, 13, C["light_teal"], bold=True)
        reqs += rect(page, LM, y, 1.4, 0.11, C["red"])
        reqs += txt(page, title_txt, LM, y + 0.22, CW, 0.30 * H, 40, C["white"], bold=True)
        if subtitle_txt:
            reqs += txt(page, subtitle_txt, LM, y + 0.22 + 0.24 * H, CW, 0.20 * H, 19, C["light_teal"])
        if foot:
            reqs += txt(page, foot, LM, H - 0.55, CW, 0.35, 11, C["muted_teal"])
        gb.batch_update(pres, reqs)
        return page

    def section(title_txt, eyebrow):
        page = new_page()
        reqs = [bg(page, C["dark_teal"])]
        y = 0.40 * H
        reqs += txt(page, eyebrow, LM, y - 0.44, CW, 0.35, 13, C["light_teal"], bold=True)
        reqs += rect(page, LM, y, 1.4, 0.11, C["red"])
        reqs += txt(page, title_txt, LM, y + 0.22, CW, 0.28 * H, 34, C["white"], bold=True)
        gb.batch_update(pres, reqs)
        return page

    def head(page, eyebrow, title_txt):
        reqs = txt(page, eyebrow, LM, 0.11 * H, CW, 0.30, 12, C["teal"], bold=True)
        reqs += txt(page, title_txt, LM, 0.11 * H + 0.30, CW, 0.15 * H, 27, C["dark_teal"], bold=True)
        reqs += rect(page, LM, 0.335 * H, 2.1, 0.05, C["red"])
        return reqs

    def content(eyebrow, title_txt, lines, idx):
        page = new_page()
        reqs = [bg(page, C["white"])]
        reqs += head(page, eyebrow, title_txt)
        by = 0.40 * H
        bh = 0.47 * H
        reqs += rect(page, LM, by + 0.02, 0.07, bh - 0.1, C["red"])  # vertical accent
        reqs += txt(page, "\n".join(lines), LM + 0.28, by, CW - 0.28, bh, 17,
                    C["dark_teal"], bullets=True, line_spacing=125, space_below=9)
        reqs += footer(page, idx)
        gb.batch_update(pres, reqs)
        return page

    def columns(eyebrow, title_txt, cols, idx):
        page = new_page()
        reqs = [bg(page, C["white"])]
        reqs += head(page, eyebrow, title_txt)
        n = len(cols)
        gap = 0.35
        y0 = 0.40 * H
        colH = 0.47 * H
        colW = (CW - (n - 1) * gap) / n
        for i, (hdr, body) in enumerate(cols):
            x = LM + i * (colW + gap)
            reqs += rect(page, x, y0, colW, colH, C["light_gray"])       # card
            reqs += rect(page, x, y0, colW, 0.07, C["red"])              # top accent
            reqs += txt(page, hdr, x + 0.22, y0 + 0.22, colW - 0.44, 0.9,
                        16, C["teal"], bold=True)
            reqs += txt(page, body, x + 0.22, y0 + 0.95, colW - 0.44, colH - 1.1,
                        13, C["dark_teal"], line_spacing=125, space_below=7)
        reqs += footer(page, idx)
        gb.batch_update(pres, reqs)
        return page

    # ---- Build the 15 slides -------------------------------------------------
    dark_cover("Coding Agents for Data Engineering",
               "Accelerating SDP, Medallion & DABs with Claude Code",
               eyebrow="SOBEYS × DATABRICKS",
               foot="Databricks Field Engineering · 60-minute hands-on demo")

    section("The problem", "WHY THIS MATTERS")

    content("THE PROBLEM", "One agent, twelve dialects", [
        "Generic code that ignores our conventions",
        "Sometimes legacy DLT we are retiring",
        "Inconsistent naming across engineers",
        "No shared data-quality policy",
        "Harder to review and onboard",
    ], 3)

    columns("THE LANDSCAPE", "Where each agent fits", [
        ("Claude Code", "Repo-scale work\nPipelines, DABs, refactors\nHolds instructions + skills"),
        ("Databricks Assistant", "In the workspace\nNotebooks, SQL, pipelines\nUnity Catalog-aware, inline"),
        ("AI/BI Genie", "Q&A over your data\nPlain-English questions\nNot code generation"),
    ], 4)

    section("Teach the agent your standards", "THE BIG IDEA")

    columns("TEACH YOUR STANDARDS", "Two ways to teach it", [
        ("Instructions — CLAUDE.md", "Always-on standards\nLoaded every session\nNaming, layers, guardrails\nOur house style, encoded"),
        ("Skills", "On-demand power tools\nInvoked by name\nBundle templates + docs\nRepeatable and shareable"),
    ], 6)

    content("INSTRUCTIONS", "Instructions: standards, always on", [
        "Modern SDP only — legacy DLT is banned",
        "Medallion Bronze / Silver / Gold rules",
        "Naming + Unity Catalog, never DBFS",
        "Data-quality Expectations on Silver",
        "DABs with dev & prod — dev-only from agents",
        "A definition-of-done self-check",
    ], 7)

    content("SKILLS", "Skills: repeatable tasks, on demand", [
        "/sdp-bronze-ingest scaffolds a compliant table",
        "/legacy-dlt-migrate upgrades old DLT",
        "Skills carry templates and reference docs",
        "Invoked by name when relevant",
        "Shared in Git across the whole team",
    ], 8)

    section("Live demo", "SEE IT WORK")

    content("LIVE DEMO", "Five beats", [
        "1  Naked agent — generic output",
        "2  + Instructions — on-standard, refuses legacy DLT",
        "3  + Skills — scaffold a compliant table in seconds",
        "4  Agent runs the loop — validate, deploy dev, self-fix",
        "5  Team scale — standards live in Git",
    ], 10)

    columns("THE RUNNING EXAMPLE", "What we build live", [
        ("Medallion pipeline (SDP)", "brz_pos_transaction — Auto Loader\nslv_pos_transaction — Expectations\ngld_daily_sales_by_store_category"),
        ("Packaged as a DAB", "dev & prod targets\nParameterized catalog + schema\nvalidate --strict before deploy"),
    ], 11)

    content("GUARDRAILS", "Guardrails for the enterprise", [
        "Agents deploy to dev only",
        "Prod is CI/CD plus human PR approval",
        "Secrets via secret scopes, never inline",
        "Every PR reviewed — ideally by a second agent first",
        "The agent accelerates; the human merges",
    ], 12)

    content("TEAM SCALE", "The flywheel: standards in Git", [
        "CLAUDE.md and skills committed next to code",
        "git clone — every engineer inherits them",
        "Change a standard once, open a PR",
        "The whole team levels up at once",
    ], 13)

    content("NEXT STEPS", "Call to action", [
        "Co-author the Sobeys CLAUDE.md",
        "Turn your top 3 patterns into skills",
        "Adopt the guardrails: dev-only, PR review, scopes",
        "Repo: github.com/brianlui-dbx/dih-vibe-coding",
    ], 14)

    dark_cover("Thank you",
               "Let's co-author your CLAUDE.md and turn your top patterns into skills.",
               eyebrow="LET'S BUILD",
               foot="github.com/brianlui-dbx/dih-vibe-coding · brian.lui@databricks.com")

    print(f"URL: https://docs.google.com/presentation/d/{pres}/edit")
    print(pres)


if __name__ == "__main__":
    main()
