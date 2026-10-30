# AdsKG-Agent — Build Plan

*Capstone · AI Engineering Cohort (RAG & Agents) · Anshika Chaurasia (solo) · written 25 Oct 2026*

**In one sentence:** an AI assistant that answers "what happened?" questions about ad performance by
*finding* the right table (search), *connecting* it to related tables (knowledge graph), then writing and
running the SQL — and remembering what worked.

---

## 1. Deadlines

| What | Due | Status |
|---|---|---|
| Design doc (≤ 2 pages, ≤ 10 MB) | **Mon 26 Oct 2026, 11:59 PM IST** | v6 ready — `Capstone_Design_Doc_AdsKG_Agent_v6.pdf` (15 KB, 2 pages) |
| Project (repo, docs ≤ 5 pages, 3-min video) | **Fri 30 Oct 2026** | not started (M1 is next) |
| OpenAI key | arrives after design-doc approval | use local FastEmbed until then |

## 2. Where things stand today

- ✅ Kaggle data downloaded (`data/raw/`, 3 CSVs, ~1.2 GB) and loaded into `data/ads.duckdb` (~200 MB)
- ✅ Design doc v6 (2 pages) + full 7-page blueprint
- ✅ **M1 done (25 Oct):** 28 tables built by `warehouse/build.py` (~11 s), all checks pass; walkthrough in `notebooks/M1_build_tables.ipynb`
- ✅ **M2 done (25 Oct):** 28 cards (`catalog/cards/`), Qdrant local at `data/qdrant`, FastEmbed bge-small; 10/10 sample questions in top 5 (5/10 at rank 1 — look-alikes win); walkthrough `notebooks/M2_table_cards_and_search.ipynb`. **To do: review `catalog/table_notes.yaml`, then freeze cards before M3.**
- ✅ **M3 built (27 Oct):** 120 questions (40 easy / 40 medium / 40 tricky; 40 practice / 80 test) + 20 three-turn conversations (5 / 15); 180 gold SQLs all run, no NULL/empty/ties; 28 answers cross-checked against raw data (28/28 agree). Walkthrough `notebooks/M3_benchmark.ipynb`. **Frozen 27 Oct** (fingerprint 61e282210933c887); disclosed in `README.md`.
- ✅ **M4 done (27 Oct):** versions A + B, harness, safety; gpt-5-mini (low effort). Practice: A 87.5%, B 70% (B misses join tables). Walkthrough `notebooks/M4_versions_A_B_and_harness.ipynb`.
- ✅ **M5 done (28 Oct):** Neo4j via Homebrew (start: `/opt/homebrew/opt/neo4j/bin/neo4j start`; password in `.env`); map = 28 tables, 166 columns, 6 metrics, 8 entities, 57 terms; 10/10 join checks; D = B's 5 hits + map, max 8 → practice 85% (A 87.5%, B 70%). Walkthrough `notebooks/M5_table_map_and_version_D.ipynb`.
- ✅ **M6 done (30 Oct):** FastMCP server `adskg`, 6 tools, safety inside, calls logged to `logs/mcp_calls.jsonl`; check_mcp: 6/6 tools, 6/6 attacks blocked. Walkthrough `notebooks/M6_mcp_server.ipynb`.
- ✅ **M7 done (30 Oct):** agent E (LangGraph ReAct over MCP tools; ≤8 steps, ≤3 SQL errors, 60k-token budget), chat memory (checkpointer) + example memory (34 practice examples). Practice: E 85% (tricky 93%); follow-ups turn 2–3: 60% with memory vs 0% without. Walkthrough `notebooks/M7_agent_E_and_memory.ipynb`.
- ✅ **M8 done (30 Oct):** version C (rewrite / hybrid BM25+dense RRF / bge re-rank) + ablations; 100/250-table catalogs (TPC-DS, TPC-H, BIRD distractors, AI-drafted cards). Practice: C 67.5% (< B 70%; rewrite and re-rank hurt); A stays 90% at 250 but cost ×6; D 85→80%. Walkthrough `notebooks/M8_smart_search_and_big_catalog.ipynb`.
- ✅ **M9 done (30 Oct):** 80 test Qs × 3 runs (5 parallel chains, one Qdrant copy each via `QDRANT_PATH`). A 90.4%, B 75.8%, C 68.3%, D 76.7%, E 80.0%, **E+memory 92.5%**; follow-ups 90% vs 28%. McNemar: A>B, A>D, memory>none significant. 91 failures sorted (`harness/failures.py`), AI grader (`harness/judge.py`), chart `docs/accuracy_ci.png`. **Open: user grades 30 answers (`results/human_grading.csv`) → `judge.py --kappa`.** Walkthrough `notebooks/M9_final_results.ipynb`.
- ✅ **M10 (30 Oct):** Streamlit chat UI (`app/streamlit_app.py`), README final choice / pivots / deviations, `docs/AdsKG_Agent_Documentation.pdf` (3 pages, `scripts/make_documentation.py`), `docs/video_script.md`, PDFs moved to `docs/`. **Open (user): record video, grade 30 answers → kappa, put code in a repository and submit.**

## 3. Folder structure (as built)

```
capstone_project/
├── README.md                    the graded write-up: results, final choice, pivots, failure analysis
├── PLAN.md                      this file
├── requirements.txt             pinned Python packages
├── .env.example                 OPENAI_API_KEY=, NEO4J_* (the real .env is never committed)
├── Capstone Project Specification_ AI Engineering Cohort.pdf   (course brief; not in the repository)
│
├── data/                        (not committed: too big)
│   ├── raw/                     Kaggle CSVs (raw_sample, ad_feature, user_profile)
│   ├── ads.duckdb               the warehouse: 28 tables (M1)
│   ├── qdrant/                  search index, local mode (M2, M8)
│   └── distractors_raw/         BIRD schemas for the bigger-catalog test (M8)
│
├── warehouse/                   M1: rules.md, build_tables.sql, build.py
├── catalog/                     M2, M5, M8: table cards, search, table map, distractors
│   ├── table_notes.yaml, make_cards.py, cards/*.yaml        one card per table
│   ├── load_qdrant.py, search.py, check_search.py           search (dense + BM25)
│   ├── smart_search.py                                      version C: rewrite, hybrid, re-rank
│   ├── load_neo4j.py, graph.py, check_graph.py              the table map (Neo4j)
│   └── distractors.py, distractor_cards/                    222 extra tables (28 / 100 / 250)
├── benchmark/                   M3: questions.jsonl, conversations.jsonl, gold/*.sql, gold_results.jsonl,
│                                make_benchmark.py, check_gold.py, cross_check.py, FROZEN.txt
├── mcp_server/                  M6: server.py (6 tools), safety.py, check_mcp.py
├── agent/                       M4, M5, M7, M8: the five versions
│   ├── pipelines.py             versions A, B, C, D (+ E wrapper)
│   ├── agent_graph.py           version E: LangGraph ReAct agent
│   ├── mcp_tools.py             MCP client bridge → LangChain tools
│   ├── memory.py                example memory (solved practice questions)
│   └── llm.py                   one function to call the OpenAI model
├── harness/                     M4, M9: run.py, metrics.py, stats.py, chart.py, judge.py, failures.py
├── configs/                     one .yaml per experiment (A, B, C, C_no_*, D, E, E_memory, E_nochat)
├── memory/examples.jsonl        34 solved practice questions (M7)
├── results/                     every run (answers.jsonl + metrics.json), final_summary.json, judge/,
│                                failures.*, human_grading.csv
├── logs/                        MCP call log (not committed)
├── notebooks/                   one walkthrough notebook per milestone + M9_human_grading.ipynb
├── app/streamlit_app.py         M10: chat UI
├── scripts/                     generators for the design docs, documentation, report and slides
└── docs/                        design doc v6, documentation, project report, slides, charts,
                                 video script, old_versions/ (design doc v1–v5)
```

Not built (see README, "Differences from the design doc"): docker-compose and Langfuse (local Qdrant files and
JSON logs were enough), a `tests/` folder (each milestone has a `check_*.py` done-test instead), `agent/prompts/`
(prompts live next to the code that uses them).

## 4. Build order (each step must work before the next)

| # | Step | Files | Done when… | Needs OpenAI key? |
|---|---|---|---|---|
| **M1** | Build the ~28 tables + write the fixed rules | `warehouse/` | one command builds every table; row counts look right | No |
| **M2** | Table cards + Qdrant search (local embeddings) | `catalog/make_cards.py`, `cards/`, `load_qdrant.py` | search returns sensible cards for 10 sample questions | No (cards can be drafted by hand or later) |
| **M3** | 120 test questions + correct SQL | `benchmark/` | every gold SQL runs; practice/test split frozen | No |
| **M4** | Versions A + B + test harness | `agent/pipelines.py`, `harness/run.py`, `metrics.py` | harness prints accuracy for A and B on practice questions | **Yes** |
| **M5** | Neo4j table map + version D | `catalog/load_neo4j.py`, `pipelines.py` | `get_join_path` finds the right connecting tables on 10 checks | No (map); Yes (D) |
| **M6** | MCP server with safety | `mcp_server/` | all 6 tools work from LangGraph and from MCP Inspector; write attempts blocked | No |
| **M7** | Version E: agent + memory + agent rules | `agent/agent_graph.py`, `memory.py` | follow-ups work ("now split by age"); limits stop runaway loops | Yes |
| **M8** | Version C + on/off tests; 100 / 250-table test | `pipelines.py`, `catalog/smart_search.py`, `catalog/distractors.py` | results saved for both experiments | Yes |
| **M9** | Final 3× runs, AI grader, statistics | `harness/judge.py`, `stats.py`, `report.py` | every table and chart generated by `report.py` | Yes |
| **M10** | Stretch E′, UI, README, video | `app/`, `README.md`, `docs/` | submission package complete | Yes |

**Core path (must finish):** M1 → M2 → M3 → M4 → M5 → M6 → M7 → M9 → README.
**Stretch (do if time allows, report honestly if not):** M8's 250-table test, E′ (generic MCP servers), Streamlit UI polish.

## 5. Day-by-day schedule (25 → 30 Oct)

| Day | Focus | Goal by end of day |
|---|---|---|
| Sun 25 Oct | Submit-ready design doc; M1 | v6 checked; ~28 tables built; `rules.md` written |
| Mon 26 Oct | **Submit design doc**; M2 + M3 | cards in Qdrant; at least the 40 practice questions + gold SQL |
| Tue 27 Oct | Finish M3; M4; M5 | 120 questions frozen; A, B, D scored on practice |
| Wed 28 Oct | M6 + M7 | MCP server + agent E with memory working |
| Thu 29 Oct | M8 (core part) + M9 | final test runs, grader, statistics, charts |
| Fri 30 Oct | M10 | README with failure analysis, 3-min video, submit |

This is tight for one person. If you fall behind, cut from the **stretch** list first — never cut the test
questions, the honest scoring, or the failure analysis (those are graded hardest).

## 6. Ground rules (from the course brief)

- **No made-up evaluation data.** Every score comes from a real run saved in `results/`.
- **Freeze the questions before building B–E**, so the versions can't be tuned to pass.
- Memory learns **only from practice questions**, never from test questions.
- Commit often; don't commit `data/`, `.env` or API keys.
- Every number in the README must be reproducible with one command (`harness/run.py` + a config).

## 7. Next action

Start **M1**: write `warehouse/rules.md` (the fixed rules), then `warehouse/build_tables.sql` to turn the three
raw tables in `data/ads.duckdb` into the ~28 look-alike tables.
