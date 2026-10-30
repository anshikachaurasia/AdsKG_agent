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


W = A4[0] - 36 * mm
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


from reportlab.platypus import Preformatted, PageBreak

W = A4[0] - 30 * mm
body.fontSize, body.leading, body.spaceAfter = 8.9, 11.6, 3.5
bullet.fontSize, bullet.leading = 8.9, 11.6
small.fontSize, small.leading = 8.0, 10.0
th.fontSize, th.leading = 8.0, 10.0
h2.fontSize, h2.leading, h2.spaceBefore, h2.spaceAfter = 12, 15, 9, 4
h3 = ParagraphStyle("h3", parent=body, fontName="Helvetica-Bold", fontSize=9.6, leading=12.5, textColor=ACCENT,
                    spaceBefore=5, spaceAfter=2.5)
code = ParagraphStyle("code", parent=body, fontName="Courier", fontSize=7.6, leading=9.4, backColor=colors.HexColor("#F4F6F8"),
                      borderPadding=4, leftIndent=4, rightIndent=4, spaceBefore=3, spaceAfter=6)
h2.keepWithNext = 1
h3.keepWithNext = 1
cap = ParagraphStyle("cap", parent=small, fontName="Helvetica-Oblique", spaceBefore=2, spaceAfter=6)


def H3(t):
    return P(t, h3)


def C(t):
    return Preformatted(t.strip("\n"), code)


# ---------- extra diagrams ----------
def _kit(d):
    ink = colors.HexColor("#333333")

    def box(x0, x1, y0, y1, color, lines, dash=None):
        d.add(Rect(x0, y0, x1 - x0, y1 - y0, rx=3, ry=3, fillColor=colors.HexColor(color), strokeColor=ink,
                   strokeWidth=0.6, strokeDashArray=dash))
        n, lh = len(lines), 8.4
        top = (y0 + y1) / 2 + (n - 1) * lh / 2 - 2.4
        for i, t in enumerate(lines):
            d.add(String((x0 + x1) / 2, top - i * lh, t, textAnchor="middle", fontSize=7,
                         fontName="Helvetica-Bold" if i == 0 else "Helvetica", fillColor=ink))

    def head(x, y, dx, dy, c=ink):
        n = (dx * dx + dy * dy) ** 0.5
        ux, uy = dx / n, dy / n
        px, py = -uy, ux
        d.add(Polygon([x, y, x - 5 * ux + 2.3 * px, y - 5 * uy + 2.3 * py, x - 5 * ux - 2.3 * px, y - 5 * uy - 2.3 * py],
                      fillColor=c, strokeColor=c, strokeWidth=0.3))

    def arrow(x0, y0, x1, y1, both=False, c=ink):
        d.add(Line(x0, y0, x1, y1, strokeColor=c, strokeWidth=0.7))
        head(x1, y1, x1 - x0, y1 - y0, c)
        if both:
            head(x0, y0, x0 - x1, y0 - y1, c)

    def path(pts, c=ink):
        d.add(PolyLine(pts, strokeColor=c, strokeWidth=0.8))
        head(pts[-2], pts[-1], pts[-2] - pts[-4], pts[-1] - pts[-3], c)

    def note(x, y, t, c="#555555", anchor="middle"):
        d.add(String(x, y, t, fontSize=6.4, fontName="Helvetica-Oblique", fillColor=colors.HexColor(c), textAnchor=anchor))

    return box, arrow, path, note


def agent_graph():
    d = Drawing(510, 168)
    box, arrow, path, note = _kit(d)
    G, Y, B, R = "#CFE8CF", "#F7E3BC", "#E2D4EE", "#B03A2E"
    box(5, 85, 92, 132, G, ["load_context", "chat history +", "3 similar verified", "Q→SQL (memory)"])
    box(100, 180, 92, 132, G, ["rewrite", "question → intent:", "metric, entities,", "grain, time window"])
    box(195, 315, 92, 132, G, ["agent (LLM, ReAct)", "thinks, picks next tool,", "writes SQL"])
    box(330, 410, 92, 132, G, ["validate", "SQL parses? result", "non-empty & sane?"])
    box(425, 505, 92, 132, G, ["answer", "result + caveats", "+ tables used"])
    box(195, 315, 20, 58, B, ["MCP tools", "search_tables · get_join_path", "list_lookalikes · describe_table",
                              "sample_rows · run_sql"])
    box(425, 505, 20, 58, Y, ["save_memory", "only if user-verified", "(or dev-gold match)"])
    for x0, x1 in ((85, 100), (180, 195), (315, 330), (410, 425)):
        arrow(x0, 112, x1, 112)
    arrow(255, 92, 255, 58, both=True)
    note(262, 72, "tool call / result", anchor="start")
    arrow(465, 92, 465, 58)
    path([370, 132, 370, 152, 255, 152, 255, 137], c=R)
    note(312, 156, "failed or empty → retry (max 3)", c=R)
    note(255, 5, "Harness stops the loop at 8 steps, 3 retries or the cost cap → answers \"not sure\" instead of guessing")
    return d


def future_graph():
    d = Drawing(510, 150)
    box, arrow, path, note = _kit(d)
    box(5, 85, 92, 120, "#DCE6F2", ["User question"])
    box(110, 200, 86, 126, "#DCE6F2", ["Supervisor agent", "classifies the question,", "routes, combines answers"])
    specs = [("What agent", "this capstone", "#CFE8CF"), ("Why agent", "metric breakdown", "#F7E3BC"),
             ("What-next agent", "playbook RAG", "#F7E3BC"), ("Act agent", "optimiser + approval", "#F7E3BC")]
    ys = [128, 96, 64, 32]
    for (n, sub, c), y in zip(specs, ys):
        box(240, 345, y - 12, y + 12, c, [n, sub])
        arrow(200, 106, 240, y)
    arrow(85, 106, 110, 106)
    box(380, 505, 20, 44, "#F2C4BE", ["Human approval gate", "nothing changes without a person"])
    arrow(345, 32, 380, 32)
    box(240, 505, 0, 12, "#E2D4EE", ["Shared: MCP tools · knowledge graph · memory · harness"])
    note(442, 130, "green = built in this capstone", c="#2E7D32")
    note(442, 120, "amber = future stages", c="#9A6B00")
    return d


# ---------- title ----------
s += [P("AdsKG-Agent &mdash; Full Design Document", h1),
      P("Companion to the 2-page submitted design doc (v5) &middot; AI Engineering Cohort capstone &middot; "
        "Anshika Chaurasia (solo) &middot; October 2026", sub),
      table([["Section", "Section", "Section"],
             ["1. Summary &amp; goals", "7. Agent design (single vs. multi-agent)", "13. Repository layout"],
             ["2. Problem &amp; users", "8. MCP server", "14. Build order &amp; done-criteria"],
             ["3. Requirements", "9. Agent harness", "15. Risks"],
             ["4. Data &amp; warehouse model", "10. Evaluation plan &amp; harness", "16. Roadmap: What → Why → Next → Act"],
             ["5. Knowledge graph (Neo4j)", "11. User interface", "17. Course rubric mapping"],
             ["6. Vector store &amp; retrieval (Qdrant)", "12. Tech stack &amp; justification", "18. Glossary"]],
            [W / 3] * 3)]

# ---------- 1 ----------
s += [P("1. Summary &amp; Goals", h2),
      P("<b>In one sentence:</b> an AI assistant that answers ad-performance questions by first <i>finding</i> the right "
        "table (search), then <i>connecting</i> it to related tables (knowledge graph), then writing and running the database "
        "query &mdash; and remembering what worked."),
      P("<b>Goals:</b> (1) answer read-only \"what happened\" questions over a ~28-table ad warehouse correctly; (2) show, with "
        "a fair experiment, how much each technique adds: search, advanced search, knowledge graph, agent, memory; (3) learn "
        "and document vector databases, graph databases, GraphRAG, agents, memory, MCP and harnesses in a way that transfers "
        "to my company's ads assistant."),
      P("<b>Non-goals (this version):</b> explaining <i>why</i> a number changed, recommending or taking actions, writing to "
        "the database, dashboards. These are the roadmap stages in Section 16."),
      table([["Success target (fixed before building)", "Value"],
             ["Best version: correct final answer on the test set", "&ge; 75%"],
             ["Gain over basic search (B) on medium + tricky questions", "&ge; +10 percentage points"],
             ["Follow-up questions answered correctly with memory on", "&ge; 80%"],
             ["Typical (median) answer time / cost per question", "&le; 10 s / &le; $0.02"]],
            [W * 0.72, W * 0.28]),
      H3("Architecture at a glance"),
      arch_diagram(),
      P("Figure 1. One-time prep fills the stores; for each question the agent understands it, finds and connects tables "
        "through the MCP server, runs the query and answers. Details: Sections 4&ndash;9.", cap)]

# ---------- 2 ----------
s += [P("2. Problem &amp; Users", h2),
      P("<b>Users:</b> ad analysts, campaign managers and advertisers' account teams who ask quick data questions and do not "
        "know the warehouse layout."),
      P("<b>Why it is hard:</b> the same metric exists in several look-alike tables that differ only by <i>grain</i> "
        "(hourly / daily / weekly), <i>traffic quality</i> (all vs. suspicious clicks removed), <i>counting</i> (total views "
        "vs. unique people) and <i>freshness</i> (live-but-incomplete vs. final). The wrong choice returns a believable but "
        "wrong number. Questions also need connecting tables (e.g. brand lives on the ad, not on the view)."),
      P("<b>Hypothesis:</b> the main failure is telling look-alikes apart and missing connecting tables, not merely the size "
        "of the prompt. Version A (no search) tests this at 28 tables; the bigger-catalog test (Section 10) tests size."),
      table([["Example question", "Why it is tricky"],
             ["\"CTR for brand 95471 yesterday\"", "Brand is on the ad table, so views must be joined to ads; \"yesterday\" = 12 May 2017"],
             ["\"Clicks for campaign 83237 so far today\"", "Must use the live partial table, not the final daily table (which stops at yesterday)"],
             ["\"Unique users who saw campaign 83237 on 10 May, suspicious traffic removed\"", "Needs the reach family and the traffic-quality family together"],
             ["\"Now split that by age group\" (follow-up)", "Needs short-term memory of the previous question and a join to users"]],
            [W * 0.42, W * 0.58])]

# ---------- 3 ----------
s += [P("3. Requirements", h2),
      table([["ID", "Functional requirement"],
             ["F1", "Accept a plain-English question and the chat so far; return an answer, the SQL, the tables used and warnings"],
             ["F2", "Find candidate tables by searching table cards (keyword + meaning) and re-ranking"],
             ["F3", "Expand candidates with the knowledge graph: connecting tables, look-alike tables, metric definitions"],
             ["F4", "Generate DuckDB SQL, run it read-only, retry up to 3 times on errors or empty results"],
             ["F5", "Remember the conversation (follow-ups) and reuse verified past answers as examples"],
             ["F6", "Expose all data tools through one MCP server usable by any MCP client"],
             ["F7", "Run any version on any question set from a config file and produce all metrics (test harness)"]],
            [W * 0.08, W * 0.92]),
      Spacer(1, 4),
      table([["ID", "Non-functional requirement"],
             ["N1 Safety", "Cannot change data: read-only connection, single SELECT, 1,000-row cap, 20 s timeout, audit log"],
             ["N2 Performance", "Median &le; 10 s and &le; $0.02 per question; MCP overhead measured"],
             ["N3 Reproducibility", "Fixed \"now\", frozen table cards and questions, versioned configs, saved traces"],
             ["N4 Fairness", "Every version uses the same tools, cards and model; memory learns only from practice questions"],
             ["N5 Transparency", "Every answer shows its SQL and tables; every run is traced in Langfuse"]],
            [W * 0.18, W * 0.82])]

# ---------- 4 ----------
s += [P("4. Data &amp; Warehouse Model", h2),
      H3("4.1 Source and quality"),
      P("Taobao (Alibaba) display-ad dataset, public on Kaggle: <b>raw_sample</b> (26.56M ad views, 1.37M clicks, CTR "
        "5.14%, 1.14M users, 6&ndash;13 May 2017, 2 placements), <b>ad_feature</b> (847k ads: campaign, advertiser, brand, "
        "category, price), <b>user_profile</b> (1.06M users: gender, age group, spending level, shopping depth, student flag, "
        "city size). Issues fixed on load: reserved column name <font face='Courier'>user</font> renamed; literal \"NULL\" "
        "brands converted (29% of ads have no brand); 1.5M views have no user profile, so user joins must be LEFT JOINs."),
      H3("4.2 Fixed rules (written before any test question)"),
      B("<b>Now</b> = 2017-05-13 23:59:59 (China time). \"Yesterday\" = 12 May; \"today\" = 13 May."),
      B("<b>Final</b> daily/weekly tables cover 6&ndash;12 May (a simulated 1-day delay). <b>Live</b> tables cover only 13 May: "
        "the last 6 hours, or today so far."),
      B("<b>Suspicious traffic:</b> a user is flagged for a given hour if their clicks in that hour exceed a threshold chosen "
        "from the click distribution (e.g. the 99.9th percentile); <i>valid</i> tables exclude flagged user-hours."),
      B("<b>Click value</b> = clicks &times; item price, always labelled an estimate (no spend or revenue in the data)."),
      H3("4.3 The ~28 tables"),
      table([["Family", "Tables", "Grain / note"],
             ["Staging (3)", "stg_impressions, stg_ads, stg_users", "cleaned copies of the raw files"],
             ["Dimensions (7)", "dim_adgroup, dim_campaign, dim_advertiser, dim_brand, dim_category, dim_placement, dim_user",
              "one row per entity; labels for coded fields"],
             ["Event fact (1)", "fct_impressions", "one row per ad view, with click flag and hour"],
             ["Time grain (4)", "agg_adgroup_daily, agg_campaign_hourly, agg_campaign_daily, agg_campaign_weekly",
              "look-alikes by grain (ROLLS_UP_TO)"],
             ["Traffic quality (2)", "agg_campaign_daily_valid, agg_brand_daily_valid", "look-alikes of the all-traffic versions"],
             ["Reach (2)", "agg_campaign_reach_daily, agg_brand_reach_daily", "unique users instead of views"],
             ["Freshness (2)", "rt_campaign_last6h, rt_brand_today_partial", "live tables for 13 May only"],
             ["Entity summaries (3)", "agg_brand_daily, agg_category_daily, agg_advertiser_daily", "daily, all traffic"],
             ["Audience (2)", "agg_campaign_demo_daily, agg_campaign_city_tier_daily", "by gender &times; age group; by city size"],
             ["Value (1)", "agg_campaign_click_value_daily", "estimated click value"],
             ["Placement (1)", "agg_placement_hourly", "2 placements only"]],
            [W * 0.19, W * 0.53, W * 0.28]),
      KeepTogether([H3("4.4 Table cards"),
      P("Each table gets a card, generated from DuckDB's information_schema and column statistics, drafted in plain language "
        "by an LLM, then checked and frozen by hand. The same cards are used by every version."),
      C("""
table: agg_campaign_daily_valid          family: traffic_quality     grain: day   freshness: final (6-12 May)
description: Daily views, clicks and CTR per campaign with suspicious user-hours removed.
columns: date, campaign_id, impressions, clicks, ctr
example values: campaign_id 83237, 391; ctr 0.031, 0.058
joins: campaign_id -> dim_campaign.campaign_id
look-alike of: agg_campaign_daily (differs_by = traffic_filter)
""")]),
      H3("4.5 Bigger-catalog distractors"),
      P("To test scale, cards for public TPC-DS (24 tables, generated in DuckDB) and BIRD schemas are added to the catalog, "
        "growing it to ~100 and ~250 tables. They are tagged <font face='Courier'>is_distractor</font> and never appear in a "
        "correct answer.")]

# ---------- 5 ----------
s += [P("5. Knowledge Graph (Neo4j)", h2),
      table([["Node", "Key properties"],
             ["Table", "name, family, grain, freshness, row_count, description, is_distractor"],
             ["Column", "table, name, type, description"],
             ["Metric", "name (CTR, reach, click value), formula"],
             ["BusinessTerm", "text (\"views\", \"impressions\", \"people reached\")"],
             ["Dimension", "name (advertiser, campaign, adgroup, brand, category)"],
             ["VerifiedQuery", "question, sql, verified_by (long-term memory, practice split only during tests)"]],
            [W * 0.2, W * 0.8]),
      Spacer(1, 4),
      table([["Relationship", "Meaning"],
             ["(Table)-[:HAS_COLUMN]-&gt;(Column)", "table structure"],
             ["(Table)-[:JOINS_TO {left_col, right_col}]-&gt;(Table)", "how two tables join"],
             ["(Table)-[:VARIANT_OF {differs_by, value}]-&gt;(Table)", "look-alike tables (grain, traffic_filter, counting, freshness)"],
             ["(Table)-[:ROLLS_UP_TO]-&gt;(Table)", "hourly &rarr; daily &rarr; weekly"],
             ["(BusinessTerm)-[:MEANS]-&gt;(Metric)-[:COMPUTED_FROM]-&gt;(Column)", "business words to columns"],
             ["(Dimension)-[:PARENT_OF]-&gt;(Dimension)", "advertiser &rarr; campaign &rarr; adgroup"],
             ["(VerifiedQuery)-[:USED]-&gt;(Table)", "memory feeds back into the graph"]],
            [W * 0.5, W * 0.5]),
      P("<b>Map-walking (version D and the get_join_path tool):</b> for every pair of seed tables, find the shortest JOINS_TO "
        "route of at most 3 steps; add bridge tables on the route; add VARIANT_OF neighbours with their differs_by values so "
        "the LLM can choose; stop at 8 tables in total. Graph is loaded with idempotent MERGE statements, so it can be rebuilt "
        "at any time."),
      C("""
MATCH (a:Table {name: $t1}), (b:Table {name: $t2})
MATCH p = shortestPath((a)-[:JOINS_TO*..3]-(b))
RETURN [n IN nodes(p) | n.name] AS tables, [r IN relationships(p) | [r.left_col, r.right_col]] AS keys
""")]

# ---------- 6 ----------
s += [P("6. Vector Store &amp; Retrieval (Qdrant)", h2),
      table([["Collection", "Contents", "Vectors", "Payload (filters)"],
             ["table_cards", "one point per table card", "dense (meaning) + sparse BM25 (keywords)",
              "table, family, grain, freshness, is_distractor"],
             ["verified_queries", "long-term memory: question &rarr; SQL", "dense", "tables, split, verified_by, date"]],
            [W * 0.17, W * 0.3, W * 0.26, W * 0.27]),
      P("<b>Retrieval steps by version:</b> B = dense search, top 8 cards. C = (optional) question rewrite into intent &rarr; "
        "hybrid dense + BM25 search, top 20, fused with reciprocal-rank fusion &rarr; cross-encoder re-rank (bge-reranker) "
        "&rarr; top 8; each of the three pieces can be switched off for the ablation. D = C + map-walking. Filters from the "
        "rewritten intent (e.g. grain = hour) are applied as payload filters."),
      P("<b>Embeddings:</b> text-embedding-3-small once the course key arrives; a local FastEmbed model is used before that "
        "so nothing is blocked. The model is fixed before the final runs and identical for all versions.")]

# ---------- 7 ----------
s += [P("7. Agent Design", h2),
      H3("7.1 Single agent or multi-agent? Decision: single agent"),
      table([["Option", "For", "Against", "Verdict"],
             ["Fixed pipeline (no agent)", "Cheap, predictable, easy to debug", "Cannot recover from a bad search or a failing query",
              "Used for versions B&ndash;D"],
             ["<b>Single ReAct agent with tools</b>", "Can re-search, inspect tables and retry; one shared context; simple to trace",
              "More LLM calls than a pipeline", "<b>Chosen for version E</b>"],
             ["Multi-agent (planner, retriever, SQL writer, checker)", "Separation of roles; good for many different task types",
              "One sequential task here: hand-offs lose context, add cost and delay, and make failures harder to attribute",
              "Rejected now; planned for the roadmap"]],
            [W * 0.22, W * 0.25, W * 0.33, W * 0.2]),
      P("The \"checker\" role is kept, but as deterministic code (the validate step), not as a second LLM agent. Multi-agent "
        "becomes the right design once the assistant must handle different <i>kinds</i> of work (what / why / next / act; "
        "Section 16)."),
      KeepTogether([H3("7.2 Agent loop (LangGraph)"),
      agent_graph(),
      P("Figure 2. Version E as a LangGraph state graph. Pipelines B&ndash;D use the same nodes in a fixed order with no "
        "agent node.", cap)]),
      table([["State field", "Holds"],
             ["messages", "the chat (short-term memory, saved by the checkpointer per thread)"],
             ["intent", "metric, entities, grain, time window, filters (from rewrite)"],
             ["candidates / join_paths", "tables found and how they connect"],
             ["sql / result / attempts", "current query, its result, number of retries"],
             ["budget", "steps, tokens and dollars used so far"],
             ["caveats / answer / verified", "warnings, final text, whether a person confirmed it"]],
            [W * 0.27, W * 0.73]),
      H3("7.3 Memory"),
      B("<b>Short-term:</b> LangGraph checkpointer keyed by conversation thread; long chats are summarised after 6 turns."),
      B("<b>Long-term:</b> verified question &rarr; SQL pairs in Qdrant (top 3 similar ones are shown to the agent as "
        "examples) and user preferences (e.g. \"I mean valid traffic by default\") in the LangGraph store. Written only when a "
        "user clicks \"correct\" in the UI, or, during testing, when a practice-set answer matches the gold answer. Test "
        "questions never enter memory."),
      H3("7.4 Prompting"),
      P("System prompt states the fixed \"now\", the read-only rule, the look-alike families and what each differs_by value "
        "means, and asks the agent to state which look-alike it chose and why. Output of rewrite and of the final answer is "
        "structured (JSON schema) so the harness can score it.")]

# ---------- 8 ----------
s += [P("8. MCP Server (\"adskg\")", h2),
      table([["Tool", "Input", "Output"],
             ["search_tables", "query, k = 8, filters (grain, freshness)", "ranked table cards with scores"],
             ["get_join_path", "list of tables, max_hops = 3", "bridge tables and join keys"],
             ["list_lookalikes", "table", "look-alike tables with differs_by and value"],
             ["describe_table", "table", "card, columns and types, row count"],
             ["sample_rows", "table, n = 3", "example rows"],
             ["run_sql", "sql", "columns, up to 1,000 rows, row count, run time &mdash; or a clear error"]],
            [W * 0.18, W * 0.37, W * 0.45]),
      P("Also exposes the resource <font face='Courier'>catalog://tables/{name}</font>. Built with Python FastMCP; stdio "
        "transport for local runs and evaluation, streamable HTTP for the demo. Safety is enforced inside the server: "
        "read-only DuckDB connection, sqlglot check that the input is a single SELECT, row cap, timeout, and an audit log of "
        "every call. LangGraph connects through langchain-mcp-adapters; Claude Desktop or Cursor can connect unchanged.")]

# ---------- 9 ----------
s += [P("9. Agent Harness (rules around the agent)", h2),
      table([["Control", "Setting"],
             ["Budgets", "&le; 8 agent steps, &le; 3 SQL retries, token and dollar cap per question"],
             ["Context", "&le; 8 table cards (~2k tokens) at a time; tool outputs truncated to 50 rows; summary after 6 turns"],
             ["Hooks", "before a tool: validate SQL; after a tool: truncate output, log to Langfuse"],
             ["Permissions", "only read-only tools exist; enforced in the MCP server"],
             ["Stop rules", "stop when the query succeeds and passes validation, or when a budget runs out &rarr; answer "
              "\"not sure\" with what was tried"]],
            [W * 0.2, W * 0.8])]

# ---------- 10 ----------
s += [P("10. Evaluation Plan &amp; Test Harness", h2),
      H3("10.1 Benchmark"),
      B("120 questions: 40 easy (one table), 40 medium (joins), 40 tricky (look-alikes). Written from analyst-style templates "
        "<b>before</b> versions B&ndash;E exist; if possible 20 are written by a classmate who has not seen the system."),
      B("Each has gold tables and gold SQL, run against DuckDB and checked by hand. Split: 40 practice, 80 test (test is only "
        "used for final runs). Plus 20 follow-up conversations of 3&ndash;4 turns (5 practice, 15 test) and paraphrased "
        "repeats of practice questions for the memory test. All published in the repo."),
      H3("10.2 Metrics"),
      table([["Metric", "Definition"],
             ["Execution accuracy", "result rows equal the gold rows (order ignored unless the question asks for an order; "
              "numbers equal within 1e-6; column names ignored)"],
             ["Table precision / recall / F1", "tables used by the final SQL vs. gold tables (all versions)"],
             ["Recall@k", "share of gold tables among the top-k retrieved (versions B&ndash;E)"],
             ["Join-path correctness", "every gold join key pair appears in the SQL"],
             ["Retry rate", "share of questions needing &ge; 1 retry"],
             ["Latency / tokens / cost", "median and 95th percentile per question"],
             ["Follow-up accuracy", "execution accuracy on turns 2+ of conversations, memory on vs. off"]],
            [W * 0.27, W * 0.73]),
      H3("10.3 LLM-as-judge"),
      P("A larger model, different from the one that writes SQL, sees the question, the SQL result and the answer (not the "
        "version name) and scores three criteria from 1 to 5: <b>relevance</b> (answers what was asked), <b>caveats</b> "
        "(mentions incomplete live data, estimated value, filters used), <b>faithfulness</b> (every number in the text "
        "appears in the result). I grade 30 answers myself; agreement is reported as Cohen's kappa."),
      H3("10.4 Experiments"),
      table([["Experiment", "Versions", "What changes", "Main metric"],
             ["E1 Main comparison", "A, B, C, D, E", "technique", "execution accuracy, table F1"],
             ["E2 Smart-search ablation", "C", "hybrid / re-rank / rewrite on or off", "recall@k, execution accuracy"],
             ["E3 Graph settings (practice set)", "D", "max hops 1&ndash;3, table cap 4/8/12", "table F1"],
             ["E4 Memory", "E", "memory on vs. off", "follow-up accuracy"],
             ["E5 Bigger catalog", "A, B, C, D", "28 / ~100 / ~250 tables", "execution accuracy, tokens"],
             ["E6 Tools (stretch)", "E vs. E′", "custom vs. generic MCP servers", "execution accuracy, steps"]],
            [W * 0.27, W * 0.17, W * 0.3, W * 0.26]),
      P("<b>Statistics:</b> each configuration runs 3 times; results are reported with 95% bootstrap confidence intervals "
        "(1,000 resamples) and each step A&rarr;B&rarr;C&rarr;D&rarr;E is checked with a paired McNemar test on the 80 test "
        "questions. <b>Final choice:</b> highest test execution accuracy; when confidence intervals overlap, the cheaper and "
        "faster version wins."),
      H3("10.5 Test harness"),
      C("""
# configs/D_test.yaml                         python -m harness.run configs/D_test.yaml
version: D            # A | B | C | D | E | E_prime
split: test           # practice | test
catalog: base         # base (28) | plus100 | plus250
runs: 3
retrieval: {k: 8, hybrid: true, rerank: true, rewrite: true}
graph: {max_hops: 3, table_cap: 8}
memory: false
model: {generator: <small chat model>, judge: <larger model>}
"""),
      P("Outputs per run: <font face='Courier'>results/&lt;run_id&gt;/answers.jsonl</font> (question, SQL, tables, result, "
        "timing, cost), <font face='Courier'>metrics.json</font>, and a Langfuse trace per question. "
        "<font face='Courier'>harness/report.py</font> builds every table and chart in the final documentation from these "
        "files, so all numbers can be regenerated with one command."),
      H3("10.6 Failure analysis"),
      P("At least 30 failures are labelled: wrong look-alike, missing connecting table, wrong join key, too many tables, "
        "made-up column, wrong time window, SQL error not recovered. Counts per version go into the README together with "
        "every approach tried and every pivot made.")]

# ---------- 11-13 ----------
s += [P("11. User Interface (optional)", h2),
      P("Streamlit chat. Beside each answer: the table cards retrieved, the graph route used, the SQL, the result table and "
        "the warnings, plus \"correct / wrong\" buttons that feed long-term memory. A sidebar switches between versions A&ndash;E "
        "for the demo video."),
      P("12. Tech Stack &amp; Justification", h2),
      table([["Tool", "Role", "Why (alternative considered)"],
             ["DuckDB", "warehouse", "fast on a laptop with 26M rows, no server (Postgres)"],
             ["Qdrant", "vector database", "dense + sparse hybrid search and payload filters built in (Chroma, pgvector)"],
             ["Neo4j", "graph database", "Cypher route queries, persistence, industry standard; NetworkX would suffice at 28 "
              "tables but not for the 250-table test or for transfer to work (NetworkX)"],
             ["LangGraph", "agent + memory", "explicit state graph, retries, checkpointer and store (Pydantic AI, smolagents)"],
             ["FastMCP", "tool server", "one tool layer for every version and any client; safety in one place (plain functions)"],
             ["Langfuse", "tracing", "open source, per-step traces for failure analysis (LangSmith)"],
             ["sqlglot", "SQL safety", "real parser instead of regex"],
             ["OpenAI models, bge-reranker, FastEmbed", "LLM, re-ranking, local embeddings", "course key; open-source re-ranker; "
              "local embeddings until the key arrives"],
             ["Streamlit", "UI", "fastest way to a usable chat with side panels (Gradio)"]],
            [W * 0.2, W * 0.18, W * 0.62]),
      P("13. Repository Layout", h2),
      C("""
adskg-agent/
  data/            raw/ (Kaggle CSVs, not committed)   ads.duckdb
  warehouse/       build_tables.sql   rules.md (fixed rules from 4.2)
  catalog/         make_cards.py   cards/*.yaml (frozen)   load_qdrant.py   load_neo4j.py
  mcp_server/      server.py (FastMCP tools + safety)
  agent/           pipelines.py (A-D)   graph.py (E, LangGraph)   memory.py   prompts/
  harness/         run.py   metrics.py   judge.py   report.py
  configs/         *.yaml (one per experiment)
  benchmark/       questions.jsonl   conversations.jsonl   gold/*.sql
  results/         <run_id>/answers.jsonl, metrics.json
  app/             streamlit_app.py
  docs/            design_doc.pdf   README.md (results + failure analysis)
""")]

# ---------- 14 ----------
s += [P("14. Build Order &amp; Done-Criteria", h2),
      P("Each step must work before the next starts, so a usable, gradeable system exists at every point."),
      table([["#", "Milestone", "Done when"],
             ["M1", "Load data, build ~28 tables, write fixed rules", "all tables build from one SQL script; row counts checked"],
             ["M2", "Table cards + Qdrant (local embeddings)", "search_tables returns sensible cards for 10 sample questions"],
             ["M3", "Benchmark: 120 questions + gold SQL", "every gold SQL runs; practice/test split frozen"],
             ["M4", "Versions A and B + test harness", "harness prints execution accuracy for A and B on practice"],
             ["M5", "Neo4j graph + version D", "get_join_path finds the right bridge tables on 10 checks"],
             ["M6", "MCP server with safety", "all tools callable from LangGraph and from Claude Desktop; write attempts blocked"],
             ["M7", "Version E + memory + agent harness", "follow-up conversations work; budgets stop runaway loops"],
             ["M8", "Version C + ablations; bigger-catalog test", "E2 and E5 results saved"],
             ["M9", "Final runs, LLM judge, statistics", "all E1&ndash;E5 tables and charts generated by report.py"],
             ["M10", "Stretch E′, UI, README, 3-minute video", "submission package complete"]],
            [W * 0.07, W * 0.43, W * 0.5])]

# ---------- 15 ----------
s += [P("15. Risks", h2),
      table([["Risk", "Mitigation"],
             ["Course API key arrives late", "local FastEmbed embeddings; M1&ndash;M3 and M5&ndash;M6 need no LLM"],
             ["Version A wins at 28 tables", "reported as a real finding; E5 shows where search becomes necessary"],
             ["Benchmark bias (I wrote it)", "rules and questions frozen first; classmate subset; per-tier results; published"],
             ["LLM-drafted cards leak hints", "hand-checked, frozen, identical for all versions"],
             ["Neo4j / LangGraph / MCP setup trouble", "Docker images pinned; each tool tested alone before integration"],
             ["Too much scope for the time", "build order M1&rarr;M10; stretch items documented honestly if unfinished"],
             ["Simulated \"now\" and estimated value", "stated clearly; no question claims real spend or revenue"]],
            [W * 0.35, W * 0.65])]

# ---------- 16 ----------
s += [P("16. Roadmap: What &rarr; Why &rarr; What next &rarr; Act", h2),
      table([["Stage", "Question", "What gets added", "Agent design"],
             ["1. What (this capstone)", "\"What was CTR yesterday?\"", "table finding, SQL, memory", "single agent"],
             ["2. Why", "\"Why did CTR drop 18%?\"", "metric tree in the graph (value = views &times; CTR &times; price); "
              "breakdown tools by campaign, placement, audience; contribution ranking", "Why agent added"],
             ["3. What next", "\"What should I check or change?\"", "playbooks of causes and fixes searched with RAG; ranked "
              "suggestions with evidence", "What-next agent added"],
             ["4. Act", "\"Move budget from A to B\"", "optimiser proposes moves; new write tools in MCP; mandatory human "
              "approval; audit log", "Act agent + approval gate"]],
            [W * 0.17, W * 0.2, W * 0.43, W * 0.2]),
      Spacer(1, 4), future_graph(),
      P("Figure 3. From stage 2 the system becomes multi-agent: a supervisor routes each question to a specialist agent; all "
        "specialists share the MCP tools, knowledge graph, memory and harness built in this capstone.", cap)]

# ---------- 17-18 ----------
s += [P("17. Course Rubric Mapping", h2),
      table([["Course requirement / rubric item", "Where it is addressed"],
             ["Problem specificity", "Sections 1&ndash;3"],
             ["Data surface + data processing (ingestion)", "Sections 4, 8"],
             ["Retrieval design", "Sections 5, 6"],
             ["Orchestration, tool use, context handling", "Sections 7, 9"],
             ["Comparative evaluation of &ge; 2 approaches with justified choice", "Section 10.4 (E1), final-choice rule"],
             ["LLM-as-judge + quantitative metrics", "Sections 10.2, 10.3"],
             ["Failure analysis (attempts, failures, pivots)", "Section 10.6 and the README"],
             ["Decision reasoning (frameworks)", "Sections 7.1, 12"],
             ["User interface (optional)", "Section 11"]],
            [W * 0.55, W * 0.45]),
      P("18. Glossary", h2),
      table([["Term", "Meaning"],
             ["RAG", "search for relevant information first, then give it to the AI to answer"],
             ["Vector database", "finds text by meaning, not only exact words (Qdrant)"],
             ["Hybrid search / re-ranking", "combine keyword and meaning search; then a second model re-orders the best results"],
             ["Knowledge graph / GraphRAG", "a map of things and how they connect; GraphRAG uses that map to add related context"],
             ["Agent / ReAct", "an AI that alternates between thinking and using tools until the task is done"],
             ["Single vs. multi-agent", "one agent doing the whole task vs. several specialised agents handing work to each other"],
             ["MCP", "Model Context Protocol: a standard way to plug tools into any AI app, like USB for AI tools"],
             ["Agent harness / test harness", "rules around the agent (limits, retries) / one script that runs and scores every version"],
             ["LLM-as-judge", "using a second AI to grade answers, checked against human grades"]],
            [W * 0.27, W * 0.73])]


def footer(canvas, doc):
    canvas.saveState()
    canvas.setFont("Helvetica", 7.5)
    canvas.setFillColor(colors.HexColor("#777777"))
    canvas.drawRightString(A4[0] - 15 * mm, 8 * mm, f"AdsKG-Agent full design document · page {doc.page}")
    canvas.restoreState()


doc = SimpleDocTemplate(OUT, pagesize=A4, leftMargin=15 * mm, rightMargin=15 * mm, topMargin=13 * mm, bottomMargin=14 * mm,
                        title="AdsKG-Agent Full Design Document", author="Anshika Chaurasia")
doc.build(s, onFirstPage=footer, onLaterPages=footer)
