# PPT Engine

[![License](https://img.shields.io/badge/license-Apache--2.0-blue.svg)](LICENSE)

English | [中文](README.md)

> **AI shouldn't just fill in a template — it should think the deck through.** PPT Engine splits "AI generates it in one shot" into three controllable stages — **strategy first, then a hard gate per slide, then a natively editable export** — built for consulting-grade / investor-grade decks with waterfall / Mekko / Gantt-style structured charts, numbers that must trace to a source, and zero tolerance for rasterized output.

## Six demos, see for yourself

Three scenarios × bilingual (CN/EN), fictional brands (no real client data). Download the `.pptx` and open it in PowerPoint — click any element and edit it. That's what "natively editable" actually means.

<table>
<tr>
<td align="center" width="33%">
<a href="examples/01_fmcg_growth_strategy/"><img src="examples/01_fmcg_growth_strategy/preview/cover.png" alt="YuanQiJiang 2027 National Growth Strategy"/></a><br/>
<sub><b>FMCG Growth Strategy</b> — YuanQiJiang 2027 National Growth Strategy · 39 slides<br/>
<a href="examples/01_fmcg_growth_strategy/YuanQiJiang_2027_National_Growth_Strategy.pptx">Download EN</a> · <a href="examples/01_fmcg_growth_strategy/元气浆_2027全国化增长战略.pptx">下载中文版</a></sub>
</td>
<td align="center" width="33%">
<a href="examples/02_enterprise_ai_roadmap/"><img src="examples/02_enterprise_ai_roadmap/preview/cover.png" alt="Yunshu Heavy Industries AI Transformation Roadmap 2027-2029"/></a><br/>
<sub><b>Industrial AI Transformation Roadmap</b> — Yunshu Heavy Industries 2027-2029 · 39 slides<br/>
<a href="examples/02_enterprise_ai_roadmap/Yunshu_Heavy_Industries_AI_Transformation_Roadmap_2027-2029.pptx">Download EN</a> · <a href="examples/02_enterprise_ai_roadmap/云枢重工_AI转型路线图2027-2029.pptx">下载中文版</a></sub>
</td>
<td align="center" width="33%">
<a href="examples/03_hospitality_brand_launch/"><img src="examples/03_hospitality_brand_launch/preview/cover.png" alt="YINSHAN Brand Launch and Operations Strategy"/></a><br/>
<sub><b>Hospitality Brand Launch Strategy</b> — YINSHAN Brand Launch and Operations Strategy · 38 slides<br/>
<a href="examples/03_hospitality_brand_launch/YINSHAN_Brand_Launch_and_Operations_Strategy.pptx">Download EN</a> · <a href="examples/03_hospitality_brand_launch/隐山_品牌启动与运营战略.pptx">下载中文版</a></sub>
</td>
</tr>
</table>

Every deck leans on the structured charts generic tools can't do well — 2×2 matrices and Gantt charts among them:

<table>
<tr>
<td align="center" width="50%"><img src="examples/02_enterprise_ai_roadmap/preview/matrix.png" alt="Core pain-point diagnosis 2x2 matrix"/><br/><sub>2×2 positioning matrix — Yunshu Heavy Industries pain-point diagnosis</sub></td>
<td align="center" width="50%"><img src="examples/03_hospitality_brand_launch/preview/gantt.png" alt="Execution roadmap Gantt chart"/><br/><sub>Gantt chart — YINSHAN's 3-year store rollout cadence</sub></td>
</tr>
</table>

## How it differs from similar open-source projects

The closest project in form is [ppt-master](https://github.com/hugohe3/ppt-master) (34k★) — it also runs inside agents like Claude Code, also exports native DrawingML `.pptx`, and is in fact the vendor source for PPT Engine's production-layer export engine (see licensing below). But the two have different positioning:

| Dimension | ppt-master | PPT Engine |
|---|---|---|
| Positioning | General-purpose aesthetic deck engine — 19 visual styles (magazine, data-journalism, Swiss grid, glassmorphism, Memphis…), built for "a deck that looks good" | Focused on consulting-grade / investor-grade high-stakes decks, built for "a deck that holds up under scrutiny" |
| Narrative gating | Strategist role + eight confirmations (canvas/audience/style/palette — implementation-layer anchors), leaning visual and experiential | Five-stage strategy workflow (define purpose → issue tree / hypothesis tree MECE → source-traced research → storyline with claims + evidence → three review gates), leaning logical and evidentiary |
| Charts | 71 general-purpose chart templates (waterfall/Gantt/Mekko-precursor etc. already included, used as generic assets) | Same chart family, plus a **deterministic geometry engine** doing the math (not AI eyeballing pixels), plus data-fidelity checks (bridges must close, shares must sum to 100%) |
| Quality gates | Syntax-level SVG checks (forbidden-element blocklist / spec_lock drift detection) | Syntax-level checks *plus* content-level rule checks (number traceability / meta-narration / client-facing tone) — two-layer fail-closed |
| Numbers & facts | Soft rule of "diverge but don't invent facts," validation leans formal | Every number must be hard-traceable to a source — a hard gate, not a soft rule |
| Generation pace | Generates the whole deck in one pass (no pausing to report mid-way) | Confirms with the human round by round, from reading the brief to finalizing each slide — no batching, no one-shot output |
| Methodology accumulation | No continuous-learning mechanism; styles/chart templates maintained by hand | **chaideck self-growing flywheel**: continuously tears down real-world decks into six asset libraries + blind-teardown evolution, so the methodology gets sharper with use |

These two aren't competitors — PPT Engine's production-workflow SVG→DrawingML export layer is vendored directly from ppt-master (MIT, see [engine/ppt_master/LICENSE.ppt-master](engine/ppt_master/LICENSE.ppt-master)). PPT Engine stands on top of that engine and goes deeper into the consulting-grade high-stakes segment: deterministic chart geometry + financial models, a hard number-traceability gate, two-layer quality checks, and a strategy workflow that aligns with the human round by round.

## Architecture

**Two workflows + one flywheel**:

- **Strategy workflow** — turns a rough brief into a finalized storyline. Five fail-closed stages: define purpose (presented / read / pre-briefed-then-presented) → issue tree / hypothesis tree (MECE) → research (source-traced, sources classified) → storyline (claims + evidence + framing + pacing + Part structure) → three review quality gates.
- **Production workflow** — turns a finalized outline into a natively editable `.pptx`. Build outline → finalize design (style spectrum + spec_lock design contract) → per-slide (template mapping → generate SVG → render → hard gate, write-render-check one slide at a time) → vendor engine export (zero-rasterization verified) → deliver.
- **chaideck** — tears down real, finished decks into six asset libraries + blind-teardown evolution, so the pattern library / phrasing library gets more accurate the more it's used.

**Code layout**:

- `engine/` — deterministic engines: chart geometry (`chart_shapes.py`), financial models (DCF/LBO/comparables, `financial_models.py`), the vendored SVG→pptx export engine (`svg2pptx/`), and the image/icon/speaker-notes generation pipeline.
- `reinforce/` — rule-based checks and state: number traceability / meta-narration / client-facing tone checks (`deck_rules/`), the design-contract lock (`spec_lock.py`), deck workspace and state, the multi-role planning team, retrieval, and the chaideck self-growing flywheel (`evolution/`).
- `skills/` — the SKILL.md files for the three workflows above, designed to be loaded by coding assistants that support Agent Skills (e.g. Claude Code).
- `specs/PPT方法论/` — accumulated PPT methodology: what top decks have in common, page-level techniques, scenario narratives, quality-gate standards, presented vs. read versions, etc.
- `exemplars/` `research_lib/` — the card-library skeletons (page-type cards / expression-technique cards / analysis-framework cards) and methodology research — ready to use out of the box; the fact/brand libraries fill in as you use it.

## Skills

- **Strategy workflow**: brief → finalized storyline. Five guided stages: define purpose → issue tree / hypothesis tree → source-traced research → storyline (claims + evidence) → three quality gates.
- **Production workflow**: finalized outline → natively editable `.pptx`. Per-slide generate → render → hard gate, zero-rasterization export via the vendor engine.
- **chaideck**: tears down real, finished decks into six asset libraries + blind-teardown evolution — a self-growing methodology flywheel.

## Quick Start

```bash
python3 -m venv .venv
.venv/bin/pip install -e .            # install the engine + reinforce packages
.venv/bin/pip install -e ".[preview]" # optional: render self-check (also needs playwright install chromium)
.venv/bin/pip install -e ".[docling]" # optional: enhanced PDF layout analysis
.venv/bin/python -m pytest            # run tests
```

The skills (SKILL.md files under `skills/`) are designed to be loaded by coding assistants that support Agent Skills.

## Dependencies & License

- Bundles a vendored SVG→pptx export engine (from [ppt-master](https://github.com/hugohe3/ppt-master), MIT) and the [simple-icons](https://simpleicons.org) icon set (CC0) — see each directory for its own license.
- This project is licensed under **Apache-2.0** — see [LICENSE](LICENSE) and [NOTICE](NOTICE).
