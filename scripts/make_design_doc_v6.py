import sys
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import mm
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, KeepTogether
from reportlab.graphics.shapes import Drawing, Rect, String, Line, Polygon, PolyLine

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
h2.spaceBefore, h2.fontSize, h2.leading = 3.5, 9.8, 12

s += [P("AdsKG-Agent: an AI Assistant That Finds the Right Ad Data", h1),
      P("Capstone design doc &middot; AI Engineering Cohort &middot; Anshika Chaurasia (solo) &middot; October 2026", sub),
      P("<b>In one sentence:</b> an AI assistant that answers ad-performance questions by first <i>finding</i> the right table "
        "(search), then <i>connecting</i> it to related tables (knowledge graph), then writing and running the database query "
        "&mdash; and remembering what worked. This capstone builds the <b>\"What happened?\"</b> stage; \"Why\", \"What next\" "
        "and \"Act\" are planned future versions (Section 8).")]

# 1. Problem
s += [P("1. Problem Statement", h2),
      P("Ad teams ask questions like <i>\"What was the click-through rate (CTR) for brand 95471 yesterday?\"</i> or "
        "<i>\"How many unique people saw campaign 83237 in the last 6 hours?\"</i> The data sits in many tables that look almost "
        "the same: hourly vs. daily vs. weekly totals, all traffic vs. suspicious clicks removed, total views vs. unique people, "
        "live-but-incomplete vs. final. Pick the wrong one and the number <i>looks</i> right but is wrong, and nobody notices."),
      P("<b>The narrow challenge:</b> given one plain-English question about ad performance (plus the earlier chat), "
        "<b>choose the correct table(s) among look-alikes and the joins between them</b>, write one read-only SQL query, run "
        "it, and answer with warnings (e.g. \"today's data is incomplete\"). <b>Input:</b> a question. <b>Output:</b> a "
        "number or small table + the SQL + caveats. <b>Scope:</b> one dataset (Taobao ads, ~28 tables), \"what happened\" "
        "questions only. <b>Out of scope:</b> explaining <i>why</i> numbers changed, recommendations, actions, or changing any data."),
      P("<b>My hypothesis:</b> the hard part is not that the AI can't <i>see</i> all the tables, but that it can't <i>tell "
        "look-alike tables apart</i> or misses the tables needed to connect them. Search plus a table map should fix that."),
      P("<b>Why it matters:</b> my company's ads assistant answers \"what\" questions today; this project tries out the search, "
        "knowledge-graph, memory and MCP techniques it doesn't have yet, built from scratch on public data.")]

# 2. Data
s += [P("2. Data", h2),
      B("<b>Source:</b> Taobao (Alibaba) ad dataset, public on Kaggle: 26.6M ad views and 1.37M clicks (CTR 5.14%) from 1.14M "
        "users over 8 days in May 2017; ad details for 847k ads (423k campaigns, 256k advertisers, 99.8k brands, 6.8k "
        "categories, price) and 1.06M user profiles (gender, age group, spending level, city size)."),
      B("<b>Prep (DuckDB):</b> fix problems found on load (29% of ads have no brand; 1.5M views have no user profile), then "
        "build ~28 tables in standard warehouse style, including the look-alike families above. Every rule (e.g. what counts "
        "as a suspicious click) is fixed and written down <i>before</i> any test question is written. \"Value\" = clicks "
        "&times; item price, clearly labelled an estimate (the data has no spend or revenue). IDs stay as numbers; no made-up names."),
      B("<b>Fixed \"now\":</b> the data is from 2017, so \"now\" = the last hour of the data (13 May 2017, 23:59 China time). "
        "\"Live\" tables hold the last 6 hours; \"final\" daily tables stop at yesterday, like a real 1-day delay."),
      B("<b>Table cards:</b> each table gets a short description (what it holds, time grain, freshness, 3 example values, how "
        "it joins), drafted by AI from the table itself, then checked and frozen by me. Cards go into Qdrant; the tables, "
        "columns, metrics, business terms and their connections go into Neo4j."),
      B("<b>Extra tables for the bigger-catalog test:</b> public TPC-DS and BIRD tables are added to the catalog only (never "
        "part of a correct answer) to grow it from ~28 to ~100 and ~250 tables.")]

# 3. Architecture
s += [P("3. Architecture", h2),
      P("<b>Design pattern:</b> <b>RAG</b> (hybrid search over table description cards) + <b>GraphRAG</b> (walk a Neo4j "
        "table map to find joins and look-alikes) feeding a single <b>ReAct</b> agent (reason &rarr; call a tool &rarr; "
        "observe &rarr; repeat), with all data tools behind one <b>MCP</b> server and short/long-term <b>memory</b>."),
      arch_diagram(),
      P("<i>Figure 1. Prep happens once. For each question the agent understands it, finds and connects tables through the "
        "MCP plug, runs the query and answers. Memory handles follow-ups like \"now split that by age\". The test harness "
        "sends every test question through this same flow.</i>", small),
      Spacer(1, 2),
      table([["Part", "What it does"],
             ["Agent type", "<b>Single agent.</b> One LangGraph ReAct agent with tools (version E); versions B&ndash;D are fixed "
              "pipelines with no agent. Multi-agent was considered and rejected for this stage: the task is one sequential "
              "chain with shared context, and extra agents add hand-off errors, cost and delay. A multi-agent design is "
              "planned for the later Why / What next / Act stages (Section 8)"],
             ["Table map (Neo4j)", "Things: tables, columns, metrics (CTR, reach), business words (\"views\" = impressions), "
              "advertiser &rarr; campaign &rarr; ad hierarchy, past correct queries. Links: \"joins with\", \"look-alike of "
              "(differs by grain / freshness / traffic filter)\", \"hourly rolls up to daily\", \"metric is computed from column\""],
             ["Map-walking rules", "Find the shortest route between the tables search found (&le; 3 steps) and add their "
              "look-alikes so the AI can choose; never more than 8 tables, to avoid flooding it"],
             ["MCP plug", "One small server (FastMCP) offering search_tables, get_join_path, list_lookalikes, describe_table, "
              "sample_rows, run_sql. Every version uses it, and other AI apps could plug into it too"],
             ["Safety", "Inside the MCP server, so nothing can bypass it: read-only database, one SELECT query only (checked "
              "with sqlglot), max 1,000 rows, 20-second timeout, every call logged"],
             ["Agent harness", "Rules around the agent: &le; 8 steps, &le; 3 retries, cost limit per question, only the top 8 "
              "table cards (~2k tokens) in its context, long chats summarised after 6 turns, says \"not sure\" instead of guessing"],
             ["Memory", "Short-term: remembers this chat. Long-term: saves questions it answered correctly and reuses them as "
              "examples, plus user preferences. During testing it learns only from practice questions"],
             ["Test harness", "One script runs any version on any question set (settings in a config file), saves every step "
              "(Langfuse), and produces all scores and charts, so every result can be re-run with one command"]],
            [W * 0.15, W * 0.85])]

# 4. Comparison
s += [P("4. What I Compare (start simple, add one idea at a time)", h2),
      table([["Version", "What it does", "What it shows"],
             ["A. No search", "Give the AI every table description at once, then write SQL", "The simple baseline"],
             ["B. Basic search", "Search the cards by meaning (Qdrant) and give the AI only the best few", "Does search help?"],
             ["C. Smart search", "B + keyword-and-meaning search, re-ranking, and rewriting the question first (each piece "
              "switched on and off to see what helps)", "Do advanced RAG tricks help?"],
             ["D. Search + map", "C, then follow the Neo4j map to add connecting tables and look-alikes", "Does the knowledge graph help?"],
             ["E. Agent + memory", "An agent that uses the MCP tools step by step and retries; run with and without memory",
              "Do the agent and memory help?"],
             ["E′. Stretch", "Same agent with ready-made generic MCP servers for Neo4j, Qdrant and DuckDB instead of my tools",
              "Custom vs. generic tools"]],
            [W * 0.15, W * 0.62, W * 0.23]),
      P("The final choice is the version with the most correct test answers; if two are statistically tied, the cheaper and "
        "faster one wins.", small)]

# 5. Evaluation
s += [P("5. Evaluation Criteria", h2),
      P("<b>Test set:</b> 120 questions with hand-checked correct SQL and answers, 40 per level: easy (one table), medium "
        "(joins), tricky (look-alike tables); 40 practice / 80 test, plus 20 follow-up conversations (5 / 15). Written and "
        "frozen <i>before</i> versions B&ndash;E exist; if possible a classmate writes 20 blind. All published."),
      P("<b>Quantitative (targets set before building):</b>", small),
      table([["Metric", "How it is measured", "Target"],
             ["Execution accuracy", "Result rows match the correct SQL's rows (order and tiny rounding ignored), 80 test Qs",
              "&ge; 75% (best version)"],
             ["Lift on hard questions", "Accuracy gain over B (basic search) on medium + tricky questions", "&ge; +10 points"],
             ["Table selection", "Precision / recall / F1 of tables used vs. correct tables; recall@k of search", "F1 &ge; 0.85"],
             ["Follow-up accuracy", "15 test conversations, memory on vs. off", "&ge; 80% with memory"],
             ["Latency / cost", "Median seconds and $ per question (Langfuse traces)", "&le; 10 s, &le; $0.02"],
             ["Scaling", "Accuracy of A&ndash;D as catalog grows 28 &rarr; ~100 &rarr; ~250 tables", "D drops &le; 10 points"],
             ["Reliability", "3 runs each; 95% bootstrap CIs; McNemar test for each step A&rarr;B&rarr;C&rarr;D&rarr;E",
              "p &lt; 0.05 to claim a gain"]],
            [W * 0.17, W * 0.63, W * 0.2]),
      B("<b>Qualitative:</b> a different, larger AI grader (blind to version) scores relevance, correct caveats and "
        "faithfulness to the query result (1&ndash;5); I grade 30 answers myself and report agreement (Cohen's kappa "
        "&ge; 0.6). Plus a review of &ge; 30 failures sorted by type (wrong look-alike, missing connecting table, wrong "
        "join, too many tables, made-up column, wrong time window) for the README.")]

# 6. Tools
s += [P("6. Framework Justification", h2),
      P("<b>Agent framework:</b> compared on what this agent needs most &mdash; a retry loop, memory across turns, step "
        "limits and MCP tools.", small),
      table([["Framework", "Strengths", "Gap for this project", "Decision"],
             ["<b>LangGraph</b>", "Explicit graph of steps; loops/retries, checkpointed memory, step limits built in; "
              "MCP adapters; Langfuse tracing", "More code to set up", "<b>Chosen</b>"],
             ["Pydantic AI", "Clean typed outputs and tool schemas; simple", "Multi-turn memory and retry loops must be "
              "hand-built", "Good fallback"],
             ["smolagents", "Very small; agent writes Python code", "Code-writing agent is harder to make read-only and safe; "
              "less control of steps", "Rejected"]],
            [W * 0.13, W * 0.4, W * 0.35, W * 0.12]),
      Spacer(1, 2),
      table([["Tool", "Job in this project", "Why this one (alternative considered)"],
             ["DuckDB", "Holds the ad data", "Fast on a laptop with 26M rows, no server (Postgres)"],
             ["Qdrant", "Vector database for the table cards", "Keyword + meaning search and filters built in (Chroma, pgvector)"],
             ["Neo4j", "Graph database for the table map", "Easy \"route from A to B\" queries; industry standard. At 28 tables a "
              "Python library (NetworkX) would do; Neo4j is chosen for the 100&ndash;250-table test and for use at work"],
             ["MCP (FastMCP)", "Standard plug for the data tools", "Same tools for every version and any AI app; safety in one place"],
             ["Langfuse", "Records every step of every run", "Open source; makes failures easy to inspect (LangSmith)"],
             ["OpenAI models", "Write SQL; a different model grades", "Course-provided key; embeddings text-embedding-3-small; "
              "open-source bge reranker"]],
            [W * 0.14, W * 0.3, W * 0.56])]

# 7. Risks
s += [P("7. Risks and What I'll Do", h2),
      B("<b>Version A wins at 28 tables</b> &rarr; a real finding; the bigger-catalog test shows where search becomes necessary. "
        "<b>I wrote the questions</b> &rarr; frozen first, classmate subset, per-level results, all published."),
      B("<b>Many new tools at once</b> &rarr; build A &rarr; B &rarr; D &rarr; E first (each working before the next), then "
        "C's on/off tests, E′ and the 250-table test. <b>Simulated \"now\" / estimated value</b> &rarr; clearly stated.")]

# 8. Roadmap
s += [P("8. Future Versions: from \"What\" to \"Act\"", h2),
      P("<b>1. What</b> (this capstone: finding tables, SQL, memory) &rarr; <b>2. Why</b> (\"why did CTR drop 18%?\": break "
        "changes down by campaign/audience, metric tree in the map) &rarr; <b>3. What next</b> (playbooks searched with RAG, "
        "ranked suggestions) &rarr; <b>4. Act</b> (propose budget moves; a person approves; audit log). From stage 2 the "
        "system becomes <b>multi-agent</b>: a supervisor routes each question to a specialist, all reusing the same MCP "
        "tools, map, memory and test harness.")]

doc = SimpleDocTemplate(OUT, pagesize=A4, leftMargin=15 * mm, rightMargin=15 * mm, topMargin=9 * mm, bottomMargin=9 * mm,
                        title="AdsKG-Agent Capstone Design Doc", author="Anshika Chaurasia")
doc.build(s)
