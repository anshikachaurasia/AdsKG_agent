"""M10: the project report - what we built and how, milestone by milestone (for presenting / reading).

Run from the project folder:
    .venv/bin/python scripts/make_project_report.py docs/AdsKG_Agent_Project_Report.pdf

Styles and the architecture figure are copied from make_documentation.py.
"""
import sys
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import mm
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, KeepTogether
from reportlab.graphics.shapes import Drawing, Rect, String, Line, Polygon

OUT = sys.argv[1]
ACCENT = colors.HexColor("#1F4E79")
LIGHT = colors.HexColor("#EAF1F8")
GRID = colors.HexColor("#B7C9DB")

ss = getSampleStyleSheet()
body = ParagraphStyle("body", parent=ss["Normal"], fontName="Helvetica", fontSize=8.6, leading=11.2, spaceAfter=2.5)
small = ParagraphStyle("small", parent=body, fontSize=7.9, leading=9.8, spaceAfter=0)
bullet = ParagraphStyle("bullet", parent=body, leftIndent=9, bulletIndent=1, spaceAfter=1.2)
h1 = ParagraphStyle("h1", parent=body, fontName="Helvetica-Bold", fontSize=14.5, leading=17.5, textColor=ACCENT, spaceAfter=1)
sub = ParagraphStyle("sub", parent=body, fontSize=8.4, textColor=colors.HexColor("#555555"), spaceAfter=4)
h2 = ParagraphStyle("h2", parent=body, fontName="Helvetica-Bold", fontSize=10.3, leading=13, textColor=ACCENT,
                    spaceBefore=5, spaceAfter=2.5)
th = ParagraphStyle("th", parent=small, fontName="Helvetica-Bold", textColor=colors.white)


def P(t, s=body):
    return Paragraph(t, s)


def B(t):
    return Paragraph(t, bullet, bulletText="•")


def table(rows, widths, header=True):
    data = [[P(c, th if (header and i == 0) else small) for c in r] for i, r in enumerate(rows)]
    t = Table(data, colWidths=widths, repeatRows=1 if header else 0)
    style = [("GRID", (0, 0), (-1, -1), 0.4, GRID), ("VALIGN", (0, 0), (-1, -1), "TOP"),
             ("LEFTPADDING", (0, 0), (-1, -1), 3), ("RIGHTPADDING", (0, 0), (-1, -1), 3),
             ("TOPPADDING", (0, 0), (-1, -1), 1.3), ("BOTTOMPADDING", (0, 0), (-1, -1), 1.3)]
    if header:
        style += [("BACKGROUND", (0, 0), (-1, 0), ACCENT)]
        style += [("BACKGROUND", (0, r), (-1, r), LIGHT) for r in range(2, len(rows), 2)]
    t.setStyle(TableStyle(style))
    return t


W = A4[0] - 30 * mm
s = []




def arch_diagram():
    d = Drawing(510, 214)
    ink = colors.HexColor("#333333")
    fill = {"prep": colors.HexColor("#DCE6F2"), "store": colors.HexColor("#F7E3BC"), "mcp": colors.HexColor("#E2D4EE"),
            "on": colors.HexColor("#CFE8CF")}

    def box(x0, x1, y0, y1, key, lines):
        d.add(Rect(x0, y0, x1 - x0, y1 - y0, rx=3, ry=3, fillColor=fill[key], strokeColor=ink, strokeWidth=0.6))
        n, lh = len(lines), 8.2
        top = (y0 + y1) / 2 + (n - 1) * lh / 2 - 2.4
        for i, t in enumerate(lines):
            d.add(String((x0 + x1) / 2, top - i * lh, t, textAnchor="middle", fontSize=6.9,
                         fontName="Helvetica-Bold" if i == 0 else "Helvetica", fillColor=ink))

    def head(x, y, dx, dy):
        n = (dx * dx + dy * dy) ** 0.5
        ux, uy = dx / n, dy / n
        px, py = -uy, ux
        d.add(Polygon([x, y, x - 5 * ux + 2.3 * px, y - 5 * uy + 2.3 * py, x - 5 * ux - 2.3 * px, y - 5 * uy - 2.3 * py],
                      fillColor=ink, strokeColor=ink, strokeWidth=0.3))

    def arrow(x0, y0, x1, y1, both=False):
        d.add(Line(x0, y0, x1, y1, strokeColor=ink, strokeWidth=0.7))
        head(x1, y1, x1 - x0, y1 - y0)
        if both:
            head(x0, y0, x0 - x1, y0 - y1)

    def tag(y, t):
        d.add(String(5, y, t, fontName="Helvetica-Bold", fontSize=7, fillColor=ACCENT))

    # one-time prep
    tag(193, "1  ONE-TIME PREP")
    box(186, 505, 182, 208, "prep", ["Load the Taobao ad data → build ~28 tables → write a short description card per table",
                                     "→ put the cards in Qdrant (search) and the table map in Neo4j (graph)"])
    # stores
    tag(150, "2  STORES")
    box(80, 176, 128, 166, "store", ["Memory", "this chat + past", "correct answers"])
    box(186, 262, 128, 166, "store", ["Qdrant", "searchable table", "description cards"])
    box(272, 348, 128, 166, "store", ["Neo4j", "map of how", "tables connect"])
    box(358, 505, 128, 166, "store", ["DuckDB", "the actual data", "(~28 tables, read-only)"])
    for x in (224, 310, 431):
        arrow(x, 182, x, 166)
    # MCP plug
    tag(100, "3  MCP PLUG")
    box(186, 505, 87, 119, "mcp", ["MCP server: one standard plug for all data tools",
                                   "search_tables · get_join_path · list_lookalikes · describe_table · sample_rows · run_sql",
                                   "can only read data, never change it"])
    # agent flow
    tag(72, "4  AGENT (per question)")
    steps = [["1. Question", "typed in chat"], ["2. Understand", "metric, dates,", "filters"],
             ["3. Find tables", "search the", "description cards"], ["4. Connect tables", "walk the table map", "to find joins"],
             ["5. Write & run SQL", "retry if it fails", "(max 3 times)"], ["6. Answer", "with caveats; remember", "if confirmed correct"]]
    xs = [5 + i * 84.4 for i in range(6)]
    for x, st in zip(xs, steps):
        box(x, x + 78, 14, 56, "on", st)
    for x in xs[:-1]:
        arrow(x + 78, 35, x + 84.4, 35)
    cx = [x + 39 for x in xs]
    arrow(cx[1], 56, cx[1], 128, both=True)          # memory, read directly
    for i in (2, 3, 4):                              # data tools go through MCP
        arrow(cx[i], 56, cx[i], 87, both=True)
    for x in (224, 297.2, 381.6):
        arrow(x, 119, x, 128, both=True)
    d.add(String(255, 2, "Agent rules (the \"harness\"): at most 8 steps · at most 3 retries · cost limit per question · "
                         "says \"not sure\" instead of guessing", textAnchor="middle", fontSize=6.3,
                 fontName="Helvetica-Oblique", fillColor=colors.HexColor("#555555")))
    return d




body.fontSize, body.leading = 7.9, 9.9
bullet.fontSize, bullet.leading = 7.9, 9.9
small.fontSize, small.leading = 7.4, 9.0
th.fontSize, th.leading = 7.4, 9.0
h2.spaceBefore, h2.fontSize, h2.leading = 4, 9.8, 12

from reportlab.platypus import Image, PageBreak  # noqa: E402

# a report is read, not skimmed: slightly larger text than the 3-page documentation
body.fontSize, body.leading, body.spaceAfter = 9, 12, 3
bullet.fontSize, bullet.leading = 9, 12
small.fontSize, small.leading = 8, 10
th.fontSize, th.leading = 8, 10
h2.spaceBefore, h2.fontSize, h2.leading = 8, 12, 15
h3 = ParagraphStyle("h3", parent=body, fontName="Helvetica-Bold", fontSize=9.6, leading=12, textColor=ACCENT,
                    spaceBefore=5, spaceAfter=2)
big = ParagraphStyle("big", parent=body, fontName="Helvetica-Bold", fontSize=20, leading=22, textColor=ACCENT,
                     alignment=1, spaceAfter=0)
cap = ParagraphStyle("cap", parent=small, alignment=1, textColor=colors.HexColor("#555555"))

import json  # noqa: E402

S = json.load(open("results/final_summary.json"))
Q = S["questions"]


def stats_row(items):
    """Big numbers with a small label under each."""
    cells = [[P(v, big) for v, _ in items], [P(label, cap) for _, label in items]]
    t = Table(cells, colWidths=[W / len(items)] * len(items))
    t.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), LIGHT), ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                           ("TOPPADDING", (0, 0), (-1, 0), 8), ("BOTTOMPADDING", (0, 1), (-1, 1), 8),
                           ("LINEAFTER", (0, 0), (-2, -1), 0.6, colors.white)]))
    return t


def milestone(code, title, what, how, result, problem=None):
    rows = [["What we did", what], ["How", how], ["Result", result]]
    if problem:
        rows.append(["Problem &rarr; fix", problem])
    return KeepTogether([P(f"{code} &middot; {title}", h3), table(rows, [W * 0.15, W * 0.85], header=False)])


# ---------- page 1: summary ----------
s += [P("AdsKG-Agent: What We Built and How We Built It", h1),
      P("Project report &middot; AI Engineering Cohort capstone &middot; Anshika Chaurasia (solo) &middot; 25&ndash;30 October 2026", sub),
      P("<b>The goal.</b> Build an AI assistant that answers \"what happened\" questions about ad performance, like "
        "<i>\"What was campaign 143747's CTR yesterday, excluding suspicious clicks?\"</i>, by finding the right table "
        "among many look-alikes, joining it to the lookup tables it needs, running SQL and showing its work. Then "
        "<b>prove</b> which design works best with a fair, frozen test."),
      P("<b>The approach.</b> Start with the simplest possible version and add one idea at a time, measuring each step: "
        "(A) show the AI every table description &rarr; (B) basic search &rarr; (C) advanced search &rarr; (D) search + "
        "a map of how tables connect &rarr; (E) an agent that uses tools, with memory. Everything was built in 10 "
        "milestones (M1&ndash;M10), then reviewed and fixed (M11), each with a walkthrough notebook."),
      Spacer(1, 4),
      stats_row([("92.5%", "best accuracy on 80 unseen test<br/>questions (agent + memory)"),
                 ("90%", "follow-up questions answered<br/>(0% without chat memory)"),
                 ("7 / 7", "targets from the design doc met"),
                 ("$0.002", "cost per question<br/>(8.6 s median)")]),
      Spacer(1, 6),
      P("<b>The main findings in plain words</b>", h3),
      B("With only 28 tables, simply <b>showing the AI every table description (A) works very well</b> (90.4%). Search "
        "is only needed once the catalog is too big to show."),
      B("<b>\"Advanced\" search tricks made things worse</b> (C, 68.3%). Rewriting the question and re-ranking didn't help "
        "find the tables a join needs."),
      B("The <b>agent with memory of solved practice examples</b> scores highest (92.5%), but is <b>statistically tied "
        "with A</b> (p = 0.11). It's the only version that handles follow-ups, so it's the one we ship; A remains the "
        "simple choice for one-shot questions on a small catalog."),
      B("Every claim was checked: 3 runs per version, confidence intervals, significance tests (with a Bonferroni "
        "check), an AI grader and a human check (kappa 0.65), a sorted list of all 91 wrong answers, and an outside "
        "code review whose fixes are reported openly (M11)."),
      P("The big picture", h2),
      arch_diagram(),
      P("<i>Figure 1. One-time prep builds the tables and their descriptions. For each question, the agent finds and "
        "connects tables through one safe MCP server, runs SQL and answers.</i>", small),
      PageBreak()]

# ---------- the milestones ----------
s += [P("Step by step: the 10 milestones", h2),
      P("Each milestone had a clear \"done when\" test, a walkthrough notebook in <font face='Courier'>notebooks/</font>, "
        "and was finished before the next one started.")]

s += [milestone("M1", "Build the warehouse (28 tables)",
                "Loaded the public Taobao ad display/click data (26 million ad impressions, ad features, user profiles) "
                "and turned it into 28 tables that look alike on purpose: hourly / daily / weekly, all traffic vs valid "
                "traffic, impressions vs unique people, live (last 6 hours) vs final.",
                "Wrote 19 fixed rules first (<font face='Courier'>warehouse/rules.md</font>: time zone, \"now\" = 13 May 23:59, "
                "a suspicious click = a user with more than 5 clicks in one hour). Then one SQL file builds every table "
                "in DuckDB (<font face='Courier'>build_tables.sql</font>, run by <font face='Courier'>build.py</font>).",
                "28 tables in about 15 seconds; a 1.3 GB local database.",
                "The planned 4th data file (behaviour log) wasn't downloadable &rarr; built everything from the 3 available files."),
      milestone("M2", "Describe every table and make them searchable",
                "Wrote a short \"card\" per table: what it holds, its grain, freshness, traffic filter, columns, and "
                "which tables look like it and how they differ.",
                "Hand-written notes &rarr; YAML cards &rarr; each card turned into a vector (FastEmbed, free local model) "
                "&rarr; stored in Qdrant, a vector database running as local files.",
                "Search finds the right table in the top 5 for 10 of 10 checks, but ranks a look-alike first in 5 of 10. "
                "That's expected: the tables are near-duplicates by design. Deliberately not tuned."),
      milestone("M3", "Create and freeze the test (benchmark)",
                "120 questions (40 easy, 40 medium with joins, 40 tricky look-alike traps) and 20 three-turn "
                "conversations; 40 / 5 for practice, 80 / 15 kept for the final test.",
                "Generated from 30 question templates with real IDs (fixed random seed), each with a hand-checked "
                "correct SQL. Every answer was recomputed from the raw data a second way (28 of 28 agree). Then the "
                "benchmark was <b>frozen</b> (a fingerprint makes any later change visible).",
                "A fair exam that every version takes; nothing was changed after building started.",
                "Some generated questions had empty answers or awkward wording &rarr; replaced and fixed before freezing. "
                "All of this is disclosed in the README."),
      milestone("M4", "Versions A and B, plus the test harness",
                "A: give the AI all 28 cards. B: give it only the 5 cards found by search. One script runs any "
                "version on any questions and scores it.",
                "<font face='Courier'>harness/run.py configs/A.yaml --split practice</font>. Scoring = <b>execution "
                "accuracy</b>: run the AI's SQL and compare the rows with the correct answer. A safety layer (sqlglot) "
                "only allows one read-only SELECT.",
                "Practice: A 87.5%, B 70%. B mostly failed on joins: search found the main table but not the lookup table."),
      milestone("M5", "The table map (Neo4j) and version D",
                "Built a graph of tables, columns, metrics, business words (\"views\" = impressions) and links: "
                "\"joins with\", \"look-alike of\", \"rolls up to\".",
                "Neo4j graph database; one Cypher query finds the shortest join route. D = B's search hits + the "
                "tables on the join routes + their look-alikes (at most 8 cards).",
                "Join routes 10/10 correct; practice D 85%.",
                "First D started from 3 search hits and lost tables B had found (77.5%) &rarr; start from B's 5 hits."),
      milestone("M6", "One safe plug for all tools: the MCP server",
                "Put all data tools behind one MCP server: search_tables, get_join_path, list_lookalikes, "
                "describe_table, sample_rows, run_sql.",
                "FastMCP. Safety lives inside the server so nothing can bypass it: read-only database, one SELECT, "
                "1,000 rows, 20-second timeout; every call logged.",
                "6 of 6 tools work; 6 of 6 write attacks (DELETE, DROP, two statements...) blocked. Any MCP app "
                "(e.g. Claude Code) can use it. (A gap, file reads inside a SELECT, was found later in review: see M11.)"),
      milestone("M7", "Version E: the agent, with memory",
                "An agent that thinks, calls a tool, looks at the result and repeats until it can answer. Chat "
                "memory for follow-ups, plus example memory: practice questions it got right, recalled as examples.",
                "LangGraph loop with hard limits (8 steps, 3 failed SQL runs, a token budget). It discovers the 6 tools "
                "from the MCP server. Memory can only learn from practice questions; the harness refuses test questions.",
                "Practice E 85%; follow-up turns 60% with chat memory vs 0% without.",
                "At the step limit it wrote SQL it had never run &rarr; graded only on SQL that really ran. Then it "
                "wasted steps hunting for names &rarr; added data facts and habits to its instructions (75% &rarr; 85%)."),
      milestone("M8", "Version C (advanced search) and the bigger-catalog test",
                "C = B + three tricks: rewrite the question, hybrid search (meaning + keywords), re-rank the shortlist; "
                "each switched off one at a time (ablation). Also tested catalogs of 100 and 250 tables.",
                "222 extra \"distractor\" tables from public benchmarks (TPC-DS, TPC-H, BIRD), cards drafted by AI in "
                "the same style, added to search and the map only. <font face='Courier'>--catalog 250</font> switch.",
                "C was worse than B. A stayed accurate at 250 tables but cost 6&times; more; search versions cost the same at any size.")]

s += [milestone("M9", "Final exam: 80 test questions, 3 runs each",
                "Ran all 6 versions 3 times on the unseen test questions, plus 15 test conversations, ablations and "
                "bigger catalogs: 35 runs.",
                "5 runs in parallel, each with its own copy of the search index (local Qdrant allows one program at a "
                "time): about 2 hours instead of 3.5. Then: 95% confidence intervals (bootstrap), McNemar significance "
                "tests, an AI grader (gpt-5, blind to version and answer), 30 answers graded by hand, and every wrong "
                "answer sorted by type.",
                "E + memory 92.5%, A 90.4%, E 80.0%, D 76.7%, B 75.8%, C 68.3%. Follow-ups 90% vs 28%. All 7 targets met.",
                "First human-grading pass accepted all 30 (kappa 0.00) &rarr; re-checked 2 answers against the "
                "reference and changed them to \"no\" (kappa 0.65). Disclosed."),
      milestone("M10", "Package it",
                "A chat app, the documentation, this report, the slides and a video script.",
                "Streamlit app (<font face='Courier'>app/streamlit_app.py</font>) showing each answer's SQL, result and "
                "tool calls; PDFs generated from scripts so numbers come straight from the result files.",
                "Everything needed to submit, re-run or present the project."),
      milestone("M11", "Code review and fixes",
                "An outside review of the finished code found real problems and over-strong claims.",
                "Switched off DuckDB file access and allowed only the 28 warehouse tables (a SELECT could read "
                "<font face='Courier'>.env</font>); long results now drop rows instead of breaking JSON; the agent is sent "
                "back once to run SQL it only showed; a fairer scorer; 27 unit tests that run on GitHub; Bonferroni and "
                "\"chosen on test\" caveats added.",
                "No frozen number changed (re-checked 3,280 queries and 666 wrong answers). The fixed agent, re-run as a "
                "separate post-hoc result: E 80.0% &rarr; 84.2%, E + memory 92.5% &rarr; 95.0%, still tied with A.",
                "The bugs were found by reading test answers &rarr; the re-run is reported apart from the frozen results, "
                "not swapped in.")]

# ---------- results ----------
rows = [["Version", "What it is", "Accuracy [95% CI]", "Medium", "Tricky", "Time", "Cost"]]
what = {"A": "all 28 cards, no search", "B": "basic search, top 5", "C": "rewrite + hybrid + re-rank",
        "D": "search + table map", "E": "agent with MCP tools", "E_memory": "agent + example memory"}
for v, w in what.items():
    d = Q[v]
    rows.append([v.replace("_memory", " + memory"), w,
                 f"{d['accuracy'] * 100:.1f}% [{int(d['ci_low'] * 100 + 0.5)}&ndash;{int(d['ci_high'] * 100 + 0.5)}]",
                 f"{d['accuracy_medium'] * 100:.0f}%", f"{d['accuracy_tricky'] * 100:.0f}%",
                 f"{d['median_seconds']} s", f"${d['median_cost_usd']:.4f}"])
s += [P("Results", h2),
      table(rows, [W * 0.12, W * 0.28, W * 0.18, W * 0.1, W * 0.1, W * 0.1, W * 0.12]),
      Spacer(1, 4),
      Image("docs/accuracy_ci.png", width=W * 0.8, height=W * 0.8 * 3.4 / 7),
      P("<i>Figure 2. Dot = average of 3 runs on 80 test questions; line = 95% confidence interval (the range where "
        "the true accuracy probably lies).</i>", cap),
      B("<b>Real differences</b> (McNemar test): A beats D and memory makes the agent better (15 questions fixed, 0 "
        "broken), both even after a Bonferroni correction for 8 tests; A beats B at p = 0.0063, borderline after "
        "correction. B, C, D and the agent without memory are <b>not</b> clearly different, and <b>A vs agent + memory "
        "is a tie</b> (p = 0.11)."),
      B("<b>Memory honesty check:</b> 56 of 80 test questions share a template with a practice example in memory. On "
        "the 24 that don't, memory still lifts the agent from 72% to 85%, so it's not just copying."),
      B("<b>Why things fail</b> (91 wrong answers sorted): wrong calculation (26), search missed the lookup table "
        "(18), right value but strict format rule (17), wrong look-alike table (13), \"not sure\" (13)."),
      B("<b>AI grader vs me:</b> same verdict on 29 of 30 answers, Cohen's kappa 0.65 (target 0.6).")]

# ---------- lessons ----------
s += [P("What we learned", h2),
      table([["Lesson", "Evidence"],
             ["Build the simple baseline first", "A (no search) beat every search version at 28 tables; without it, C "
              "or D would have looked like progress"],
             ["\"Advanced\" isn't automatically better", "rewrite and re-rank each lowered accuracy, on practice and test"],
             ["The hard part is joins and look-alikes, not SQL", "most failures are a missing lookup table or a "
              "similar-looking wrong table"],
             ["Memory matters most for an agent", "example memory +12.5 points; chat memory turns follow-ups from 0% to 90%"],
             ["Never grade what didn't run", "the agent once \"answered\" with SQL it never executed; grading only "
              "executed SQL made it honest"],
             ["Let someone else review it", "a code review found a file-read hole and two agent bugs that all our "
              "own checks missed"],
             ["Freeze the test, report everything", "every change made on practice questions, and every pivot, is in "
              "the README, including negative results"]],
            [W * 0.33, W * 0.67])]

# ---------- glossary + reproduce ----------
s += [P("Words used in this project (for beginners)", h2),
      table([["Word", "Meaning"],
             ["RAG", "Retrieval-Augmented Generation: first <i>find</i> relevant information (here: table cards), then "
              "give it to the AI to write the answer"],
             ["Embedding / vector", "a list of numbers that captures a text's meaning; similar texts get similar numbers, "
              "so we can search by meaning"],
             ["GraphRAG", "retrieval that also walks a graph (our table map) to bring in connected items"],
             ["Agent / ReAct", "an AI that loops: think &rarr; use a tool &rarr; look at the result &rarr; repeat"],
             ["MCP", "Model Context Protocol: a standard plug so any AI app can use the same tools"],
             ["Execution accuracy", "run the AI's SQL and check that its rows match the correct answer's rows"],
             ["Confidence interval", "the range where the true score probably lies, given only 80 questions"],
             ["McNemar test", "checks whether two versions really differ, using only questions where they disagree"],
             ["Cohen's kappa", "agreement between two graders beyond luck (1 = perfect, 0 = chance)"],
             ["Ablation", "switch one feature off to see whether it was helping"]],
            [W * 0.2, W * 0.8]),
      P("How to re-run everything", h2),
      P("<font face='Courier' size='7.6'>"
        "python warehouse/build.py &middot; catalog/make_cards.py &middot; catalog/load_qdrant.py &middot; "
        "catalog/load_neo4j.py &middot; benchmark/check_gold.py<br/>"
        "python harness/run.py configs/&lt;A|B|C|D|E|E_memory&gt;.yaml --split test [--conversations] [--catalog 250]<br/>"
        "python harness/stats.py &middot; harness/chart.py &middot; harness/judge.py &middot; harness/failures.py<br/>"
        "streamlit run app/streamlit_app.py</font>"),
      P("Full commands, setup and every number are in the README; each milestone has a walkthrough notebook.", small)]

doc = SimpleDocTemplate(OUT, pagesize=A4, leftMargin=15 * mm, rightMargin=15 * mm, topMargin=12 * mm, bottomMargin=12 * mm,
                        title="AdsKG-Agent Project Report", author="Anshika Chaurasia")
doc.build(s)
print(f"{OUT}: {doc.page} pages")
