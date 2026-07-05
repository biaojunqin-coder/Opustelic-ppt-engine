# PPT Engine

[![License](https://img.shields.io/badge/license-Apache--2.0-blue.svg)](LICENSE)

English | [中文](README.md)

> **AI shouldn't just fill in a template — it should think the deck through.** PPT Engine splits "AI generates it in one shot" into three controllable stages — **strategy first, then a hard gate per slide, then a natively editable export** — built for consulting-grade / investor-grade decks with waterfall / Mekko / Gantt-style structured charts, numbers that must trace to a source, and zero tolerance for rasterized output.

## Sound familiar?

- You ask an AI to generate a deck, and get back a stack of rasterized images — you can't open PowerPoint and edit a single word or move a single box.
- You let the AI make up its own numbers, and get asked "where does this figure come from" in the room — and you can't answer.
- Structured charts like waterfalls, Gantt charts, or BCG matrices come out with bars that don't line up and shares that don't sum to 100% — it falls apart the moment anyone looks closely.
- The AI dumps 40 slides in one shot, all in its own narrative logic — not the story you actually wanted to tell — and fixing it takes longer than writing it yourself.

PPT Engine exists to fix exactly these problems: natively editable output, numbers that must have a traceable source, structured charts computed by code instead of AI eyeballing them, and a process that aligns with you slide by slide instead of dumping the whole thing at once.

## Core highlights

- **Natively editable, not a picture** — every element (text box, shape, chart) can be individually selected and edited in PowerPoint — color, text, position — not a flattened raster image.
- **Structured charts computed by code, not eyeballed by AI** — waterfall bars must connect mathematically, Gantt bars must align to real dates, shares must sum to 100%. Geometry and data come from a deterministic engine, not a model improvising on the fly.
- **A hard number-traceability gate** — every number that appears on a slide must trace back to a source; if it can't, it's blocked and reworked — not waved through because it's "probably fine."
- **Aligns with you round by round, never batches** — from reading the brief to finalizing each slide, it checks in with you the whole way, instead of dumping a finished deck for you to comb through for errors.
- **The chaideck self-growing flywheel** — continuously tears down real, finished decks to grow its methodology; the more it's used, the sharper the pattern library and phrasing library get — not a template frozen in time.

## Six demos, see for yourself

Three scenarios × bilingual (CN/EN), fictional brands (no real client data). Download the `.pptx` and open it in PowerPoint — click any element and edit it. That's what "natively editable" actually means.

<table>
<tr>
<td align="center" width="33%" valign="top">
<a href="examples/01_fmcg_growth_strategy/"><img src="examples/01_fmcg_growth_strategy/preview/cover.png" alt="YuanQiJiang 2027 National Growth Strategy" width="100%"/></a>
<br/>
<sub><b>FMCG Growth Strategy</b> — YuanQiJiang 2027 National Growth Strategy · 39 slides<br/>
<a href="examples/01_fmcg_growth_strategy/YuanQiJiang_2027_National_Growth_Strategy.pptx">Download EN</a> · <a href="examples/01_fmcg_growth_strategy/元气浆_2027全国化增长战略.pptx">下载中文版</a></sub>
</td>
<td align="center" width="33%" valign="top">
<a href="examples/02_enterprise_ai_roadmap/"><img src="examples/02_enterprise_ai_roadmap/preview/cover.png" alt="Yunshu Heavy Industries AI Transformation Roadmap 2027-2029" width="100%"/></a>
<br/>
<sub><b>Industrial AI Transformation Roadmap</b> — Yunshu Heavy Industries 2027-2029 · 39 slides<br/>
<a href="examples/02_enterprise_ai_roadmap/Yunshu_Heavy_Industries_AI_Transformation_Roadmap_2027-2029.pptx">Download EN</a> · <a href="examples/02_enterprise_ai_roadmap/云枢重工_AI转型路线图2027-2029.pptx">下载中文版</a></sub>
</td>
<td align="center" width="33%" valign="top">
<a href="examples/03_hospitality_brand_launch/"><img src="examples/03_hospitality_brand_launch/preview/cover.png" alt="YINSHAN Brand Launch and Operations Strategy" width="100%"/></a>
<br/>
<sub><b>Hospitality Brand Launch Strategy</b> — YINSHAN Brand Launch and Operations Strategy · 38 slides<br/>
<a href="examples/03_hospitality_brand_launch/YINSHAN_Brand_Launch_and_Operations_Strategy.pptx">Download EN</a> · <a href="examples/03_hospitality_brand_launch/隐山_品牌启动与运营战略.pptx">下载中文版</a></sub>
</td>
</tr>
</table>

Every deck leans on the structured charts generic tools can't do well — 2×2 matrices and Gantt charts among them:

<table>
<tr>
<td align="center" width="50%" valign="top">
<img src="examples/02_enterprise_ai_roadmap/preview/matrix.png" alt="Core pain-point diagnosis 2x2 matrix" width="100%"/>
<br/>
<sub>2×2 positioning matrix — Yunshu Heavy Industries pain-point diagnosis</sub>
</td>
<td align="center" width="50%" valign="top">
<img src="examples/03_hospitality_brand_launch/preview/gantt.png" alt="Execution roadmap Gantt chart" width="100%"/>
<br/>
<sub>Gantt chart — YINSHAN's 3-year store rollout cadence</sub>
</td>
</tr>
</table>

## Acknowledgment: iterating on top of ppt-master

PPT Engine's production workflow didn't reinvent the wheel — it's built by referencing and iterating on [ppt-master](https://github.com/hugohe3/ppt-master) (34k★), the project that first proved "AI generates SVG → translate it into native DrawingML `.pptx`" at real-world scale. PPT Engine's production-layer SVG→pptx export engine is vendored directly from it (MIT, see [engine/ppt_master/LICENSE.ppt-master](engine/ppt_master/LICENSE.ppt-master)). Thank you to Hugo He and the ppt-master community for that work.

ppt-master itself is positioned as a general-purpose aesthetic deck engine — 19 visual styles (magazine, data-journalism, Swiss grid, glassmorphism, Memphis…) — and it does "a deck that looks good" thoroughly well. PPT Engine builds on top of that engine and pushes further into a narrower, deeper direction: consulting-grade / investor-grade high-stakes decks. A few layers we added:

1. **Deterministic chart geometry engine** — ppt-master's 71 chart templates already cover consulting-grade weapons like waterfall/Gantt/Mekko-precursor charts; we added a data-fidelity layer on top — bridges must mathematically close, shares must sum to 100%. Charts aren't eyeballed by AI, they're computed by code.
2. **Hard number-traceability gate** — every number on every slide must trace back to a source, or it's hard-blocked. This sits on top of ppt-master's softer "diverge, don't invent facts" rule, adding a stricter, hard-enforced check.
3. **Two-layer quality gate** — on top of ppt-master's existing SVG syntax-level checks (forbidden-element blocklist / spec_lock drift detection), we added a content-level layer (meta-narration / client-facing tone) — syntax *and* content, both fail-closed.
4. **Five-stage guided alignment in the strategy workflow** — we extended ppt-master's "eight confirmations" human-in-the-loop UX skeleton into a full strategy workflow built for consulting narratives: issue tree / hypothesis tree (MECE), a storyline structure of claims + evidence, and three review quality gates.
5. **chaideck self-growing flywheel** — continuously tears down real, finished decks into six asset libraries + blind-teardown evolution, so the methodology gets sharper the more it's used. This is a capability ppt-master doesn't have — one we grew on our own.

## How the workflows actually work

PPT Engine isn't a "brief in, pptx out" black box — it's two fail-closed workflows running in relay, with the chaideck flywheel standing between them.

### Strategy workflow: five stages, a gate at every one

```
A rough brief
   │
   ▼
① Define purpose ──────── set delivery_purpose (presented / read / pre-briefed-then-presented)
   │                       + argument mode + aesthetic leaning
   │   Confirms with you item by item — doesn't move on until aligned
   ▼
② Issue tree / hypothesis tree (MECE) ──────── break the problem into
   │                                            mutually exclusive, collectively exhaustive sub-questions
   │   Confirms the shape of the tree with you
   ▼
③ Research ──────── source-traced, sources classified (client-provided / web-researched /
   │                 industry common knowledge), reports progress issue by issue
   │   Confirms key findings with you
   ▼
④ Storyline ──────── claims + a set of evidence + framing + pacing + Part structure
   │   Written Part by Part — each finished Part is laid out for you to confirm,
   │   never the whole thing dumped on you at once
   ▼
⑤ Three review quality gates ──────── rule checks + human review; failing any gate
   │                                   sends it back to that stage — never proceeds while broken
   ▼
Finalized storyline → handed off to the production workflow
```

### Production workflow: finalized outline → natively editable pptx

```
Finalized storyline (outline)
   │
   ▼
① Build outline ──────── break it down into a per-slide structure
   ▼
② Finalize design ──────── pick a point on the style spectrum + spec_lock design contract
   │                        (palette / typography / icons / images, all locked)
   │   Confirms the design direction with you
   ▼
③ Per-slide production (one slide per round, never batched)
      template mapping → generate SVG → render preview → hard quality gate
      fails the gate ──→ sent back to redo that slide, never carries a broken slide forward
   ▼
④ Vendor engine export ──────── SVG → DrawingML, zero-rasterization verified
   ▼
Delivered: a natively editable .pptx
```

### chaideck: tear down real decks, let the methodology get smarter on its own

```
A real, finished deck (investor deck, consulting deck, etc.)
   │
   ▼
Torn down into six asset libraries (page-type cards / expression-technique cards /
analysis-framework cards / data palettes / real samples / industry knowledge)
   │
   ▼
Blind-teardown evolution ──────── periodically re-tears-down already-archived examples
   │                                with zero prior framework, compares old vs. new conclusions
   ▼
Methodology confidence ledger upgraded ──────── the pattern / phrasing libraries
                                                  accumulate and sharpen with use
```

## What's in the built-in libraries

What ships out of the box is a **methodology skeleton** — the structure is built and seeded with starting content; the fact/brand libraries fill in as you use the project.

| Directory | Contents | Size |
|---|---|---|
| [`exemplars/页型卡库.json`](exemplars/页型卡库.json) (page-type cards) | Each card records `page_function` / `technique` / `mechanism` (why it works) / `pick_when` / `skip_when` / `rating` | 101 cards |
| [`exemplars/表达手法卡.json`](exemplars/表达手法卡.json) (expression-technique cards) | Copywriting technique cards, including a six-slot structural-copy paradigm (chapter bridges / chapter summaries / diagnosis wrap-ups / ask closings / closing slides / TOC naming) + anti-patterns (`anti_pattern`) | 142 cards |
| [`exemplars/分析框架库.json`](exemplars/分析框架库.json) (analysis-framework cards) | Structured encodings of established frameworks like AIPL, Porter's Five Forces, SWOT (`structure` / `pick_when` / `skip_when` / `mechanism`) | 88 frameworks |
| [`exemplars/数据色板.json`](exemplars/数据色板.json) (data palettes) | Data-visualization color palette families | 11 families |
| [`specs/PPT方法论/`](specs/PPT方法论) (PPT methodology) | 9 methodology documents (00 overview / 01 what top decks have in common & failure modes / 02 page-technique essentials / 03 scenario narrative structures / 04 example checklist by scenario / 05 quality gates & evaluation / 06 implementing high-stakes hard charts / 07 presented vs. read versions / 08 deck-mode narrative-skeleton system) — each tagged with a confidence level (strong candidate from methodology encoding vs. backed by real samples), so it doesn't pretend to be as certain as conclusions verified against real decks | 9 docs + revision log |
| [`reinforce/deck_rules/`](reinforce/deck_rules) (rule checks) | 6 rule-check modules: `rules.py` (numbers must carry a source / no bare assertive titles), `client_tone.py` (catches internal working language like "brief P3-4" leaking onto client-facing slides), `storyline.py` (storyline's six forbidden patterns: topic-only / missing so-what / vague wording / too fragmented / no ending / logical jumps), `svg_compat.py` (SVG→PPTX export compatibility blocklist), `visual_review.py` (structured visual-defect checks), `font_embed.py` (font-embedding license checks) | 6 rule modules |
| [`research_lib/真实样本/`](research_lib/真实样本) (real samples) | Teardowns of real, finished decks (e.g. a page-by-page teardown of Airbnb's 2009 seed deck) + an industry-knowledge-base skeleton | — |
| [`research_lib/开源拆解/`](research_lib/开源拆解) (open-source teardowns) | ~30 in-depth teardown notes on comparable open-source projects (AI PPT generators, chart libraries, document parsers, etc.) — the raw evidence base behind the methodology research | ~30 notes |

## Architecture

**Code layout**:

- `engine/` — deterministic engines: chart geometry (`chart_shapes.py`), financial models (DCF/LBO/comparables, `financial_models.py`), the vendored SVG→pptx export engine (`svg2pptx/`), and the image/icon/speaker-notes generation pipeline.
- `reinforce/` — rule-based checks and state: number traceability / meta-narration / client-facing tone checks (`deck_rules/`), the design-contract lock (`spec_lock.py`), deck workspace and state, the multi-role planning team, retrieval, and the chaideck self-growing flywheel (`evolution/`).
- `skills/` — the SKILL.md files for the three workflows above, designed to be loaded by coding assistants that support Agent Skills (e.g. Claude Code).
- `specs/PPT方法论/` — accumulated PPT methodology (see table above).
- `exemplars/` `research_lib/` — the card-library skeletons and methodology research (see table above).

## Which agent platforms this works with

The SKILL.md files under `skills/` follow the Agent Skills format — plain Markdown with a YAML frontmatter — which fundamentally only requires the host agent to do three things: **read/write files, execute commands, and hold a multi-turn conversation**. Any coding agent that meets those three requirements should work in principle, including but not limited to Claude Code, Codex CLI, Cursor, VS Code + Copilot, and Windsurf.

**Claude Code (native support)**: Claude Code automatically discovers project-level `.claude/skills/<name>/SKILL.md`. Symlink (or copy) this repo's three skills into your working project:

```bash
mkdir -p /path/to/your-project/.claude/skills
ln -s /path/to/PPT-oss/skills/策略工作流   /path/to/your-project/.claude/skills/策略工作流
ln -s /path/to/PPT-oss/skills/制作工作流   /path/to/your-project/.claude/skills/制作工作流
ln -s /path/to/PPT-oss/skills/chaideck    /path/to/your-project/.claude/skills/chaideck
```

Restart Claude Code, then type `/策略工作流` (or just describe what you need in natural language — the trigger conditions are written into each SKILL.md's `description`) to load the corresponding workflow.

**Other agents (Codex CLI / Cursor / etc., manual reference)**: these tools don't currently have a Skill auto-discovery mechanism identical to Claude Code's, but a SKILL.md is just a readable instruction document — manual reference works just as well. Either tell the agent directly, "read `skills/策略工作流/SKILL.md` and walk me through its process," or fold the content into that tool's own custom-instruction mechanism (e.g. Codex CLI's `AGENTS.md`, Cursor's `.cursor/rules/`).

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
