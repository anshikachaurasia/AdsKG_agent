"""M10: the presentation deck (14 slides, 16:9) with speaker notes. Numbers are read from the result files.

Run from the project folder:
    .venv/bin/python scripts/make_slides.py docs/AdsKG_Agent_Presentation.pptx
"""
import json
import sys
from collections import Counter

from pptx import Presentation
from pptx.chart.data import CategoryChartData
from pptx.dml.color import RGBColor
from pptx.enum.chart import XL_CHART_TYPE, XL_LABEL_POSITION
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import MSO_ANCHOR, PP_ALIGN
from pptx.util import Inches, Pt

OUT = sys.argv[1]
NAVY, INK, MUTED = RGBColor(0x14, 0x21, 0x3D), RGBColor(0x1F, 0x29, 0x37), RGBColor(0x5B, 0x64, 0x72)
TINT, LINE, WHITE = RGBColor(0xEE, 0xF2, 0xF8), RGBColor(0xD5, 0xDC, 0xE6), RGBColor(0xFF, 0xFF, 0xFF)
ACCENT, BAR = RGBColor(0xE7, 0x6F, 0x2E), RGBColor(0x8C, 0x9B, 0xB3)
ICE = RGBColor(0xB9, 0xC6, 0xDD)
FONT = "Calibri"

S = json.load(open("results/final_summary.json"))
Q, CONV = S["questions"], S["conversations"]
JUDGE = json.load(open("results/judge/summary.json"))
FAIL = Counter(json.loads(line)["type"] for line in open("results/failures.jsonl"))

prs = Presentation()
prs.slide_width, prs.slide_height = Inches(13.333), Inches(7.5)
BLANK = prs.slide_layouts[6]


# ---------- small helpers ----------
def text(slide, x, y, w, h, runs, size=16, color=INK, bold=False, align=PP_ALIGN.LEFT, anchor=MSO_ANCHOR.TOP, name=None):
    """runs: a string, or a list of paragraphs; each paragraph a string or a list of (text, {options}) runs."""
    box = slide.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
    if name:
        box.name = name
    tf = box.text_frame
    tf.word_wrap, tf.vertical_anchor = True, anchor
    tf.margin_left = tf.margin_right = tf.margin_top = tf.margin_bottom = 0
    paragraphs = runs if isinstance(runs, list) else [runs]
    for i, para in enumerate(paragraphs):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.alignment = align
        p.space_after = Pt(6)
        for chunk, opts in ([(para, {})] if isinstance(para, str) else para):
            r = p.add_run()
            r.text = chunk
            r.font.name, r.font.size = FONT, Pt(opts.get("size", size))
            r.font.bold = opts.get("bold", bold)
            r.font.italic = opts.get("italic", False)
            r.font.color.rgb = opts.get("color", color)
    return box


def box(slide, x, y, w, h, fill=TINT, line=None, shape=MSO_SHAPE.ROUNDED_RECTANGLE, name=None):
    s = slide.shapes.add_shape(shape, Inches(x), Inches(y), Inches(w), Inches(h))
    if name:
        s.name = name
    s.fill.solid()
    s.fill.fore_color.rgb = fill
    if line:
        s.line.color.rgb, s.line.width = line, Pt(1)
    else:
        s.line.fill.background()
    s.shadow.inherit = False
    if shape == MSO_SHAPE.ROUNDED_RECTANGLE:
        s.adjustments[0] = 0.08
    return s


def circle_number(slide, x, y, n, fill=NAVY, d=0.55):
    c = box(slide, x, y, d, d, fill=fill, shape=MSO_SHAPE.OVAL)
    tf = c.text_frame
    tf.margin_left = tf.margin_right = tf.margin_top = tf.margin_bottom = 0
    p = tf.paragraphs[0]
    p.alignment = PP_ALIGN.CENTER
    r = p.add_run()
    r.text = str(n)
    r.font.name, r.font.size, r.font.bold, r.font.color.rgb = FONT, Pt(18), True, WHITE
    tf.vertical_anchor = MSO_ANCHOR.MIDDLE


def content_slide(title, subtitle=None, notes=""):
    slide = prs.slides.add_slide(BLANK)
    text(slide, 0.6, 0.4, 12.1, 0.8, title, size=34, color=NAVY, bold=True, name="Title")
    if subtitle:
        text(slide, 0.6, 1.15, 12.1, 0.5, subtitle, size=17, color=MUTED, name="Subtitle")
    text(slide, 11.6, 7.0, 1.2, 0.3, str(len(prs.slides)), size=11, color=MUTED, align=PP_ALIGN.RIGHT)
    slide.notes_slide.notes_text_frame.text = notes
    return slide


def dark_slide(notes=""):
    slide = prs.slides.add_slide(BLANK)
    bg = slide.background.fill
    bg.solid()
    bg.fore_color.rgb = NAVY
    slide.notes_slide.notes_text_frame.text = notes
    return slide


def stat(slide, x, y, w, value, label, value_color=NAVY, fill=TINT, h=1.9):
    box(slide, x, y, w, h, fill=fill)
    text(slide, x + 0.2, y + 0.2, w - 0.4, 0.9, value, size=44, color=value_color, bold=True, align=PP_ALIGN.CENTER)
    text(slide, x + 0.2, y + 1.1, w - 0.4, h - 1.2, label, size=14, color=MUTED, align=PP_ALIGN.CENTER)


def bar_chart(slide, x, y, w, h, categories, values, colors, title, horizontal=False, fmt='0.0"%"', axis_max=100):
    data = CategoryChartData()
    data.categories = categories
    data.add_series(title, values)
    kind = XL_CHART_TYPE.BAR_CLUSTERED if horizontal else XL_CHART_TYPE.COLUMN_CLUSTERED
    chart = slide.shapes.add_chart(kind, Inches(x), Inches(y), Inches(w), Inches(h), data).chart
    chart.has_legend = False
    chart.has_title = True
    chart.chart_title.text_frame.text = title
    tp = chart.chart_title.text_frame.paragraphs[0]
    tp.runs[0].font.size, tp.runs[0].font.bold, tp.runs[0].font.color.rgb, tp.runs[0].font.name = Pt(14), True, INK, FONT
    plot = chart.plots[0]
    plot.gap_width = 60
    plot.has_data_labels = True
    labels = plot.data_labels
    labels.number_format, labels.number_format_is_linked = fmt, False
    labels.position = XL_LABEL_POSITION.OUTSIDE_END
    labels.font.size, labels.font.color.rgb, labels.font.name = Pt(13), INK, FONT
    for point, color in zip(plot.series[0].points, colors):
        point.format.fill.solid()
        point.format.fill.fore_color.rgb = color
    va, ca = chart.value_axis, chart.category_axis
    va.maximum_scale, va.minimum_scale = axis_max, 0
    va.has_major_gridlines = True
    va.major_gridlines.format.line.color.rgb = LINE
    va.format.line.fill.background()
    va.visible = False
    ca.tick_labels.font.size, ca.tick_labels.font.color.rgb, ca.tick_labels.font.name = Pt(13), INK, FONT
    ca.format.line.color.rgb = LINE
    if horizontal:
        ca.reverse_order = True
    return chart


# ---------- 1. title ----------
s = dark_slide("Hi, I'm Anshika. My capstone is AdsKG-Agent: an AI assistant that answers 'what happened' questions "
               "about ad performance, and a careful comparison of five ways to build it.")
text(s, 0.9, 2.1, 11.5, 1.2, "AdsKG-Agent", size=60, color=WHITE, bold=True)
text(s, 0.9, 3.3, 11.5, 0.9, "An AI assistant that finds the right ad data, and proof of which design works best",
     size=24, color=ICE)
text(s, 0.9, 5.6, 11.5, 0.9, [[("Anshika Chaurasia", {"bold": True, "color": WHITE})],
                              "AI Engineering Cohort capstone  ·  30 October 2026"], size=16, color=ICE)

# ---------- 2. problem ----------
s = content_slide("The problem: picking the right table",
                  "Ad teams ask simple questions, but the warehouse has many tables that look alike",
                  notes="A typical question. Writing the SQL is not the hard part. The hard part is choosing among "
                        "near-identical tables and finding the lookup tables to join. Pick the wrong one and you get "
                        "a confident, wrong number.")
box(s, 0.6, 1.9, 12.1, 1.15, fill=NAVY)
text(s, 1.0, 1.9, 11.4, 1.15, "“What was campaign 143747's CTR yesterday, excluding suspicious clicks?”",
     size=24, color=WHITE, anchor=MSO_ANCHOR.MIDDLE)
traps = [("Time grain", "hourly, daily or weekly?"), ("Traffic", "all clicks or valid only\n(suspicious removed)?"),
         ("People vs views", "unique people (reach)\nor impressions?"), ("Freshness", "live last 6 hours,\ntoday so far, or final?")]
for i, (head, body) in enumerate(traps):
    x = 0.6 + i * 3.1
    box(s, x, 3.45, 2.85, 2.45)
    circle_number(s, x + 0.3, 3.7, i + 1, fill=ACCENT)
    text(s, x + 0.3, 4.45, 2.3, 0.45, head, size=20, color=NAVY, bold=True)
    text(s, x + 0.3, 4.95, 2.4, 0.9, body, size=15, color=INK)
text(s, 0.6, 6.25, 12.1, 0.5, "Input: one English question (or a follow-up).  Output: the answer, the SQL behind it and "
     "the tables used, or “not sure”.", size=15, color=MUTED)

# ---------- 3. data ----------
s = content_slide("Data: a real ads log, a tricky warehouse",
                  "Public Taobao display/click data, 6–13 May 2017, built into DuckDB",
                  notes="I built 28 tables on purpose in look-alike families, wrote 19 rules first (time zone, what "
                        "'now' is, what a suspicious click is), and froze a 120-question benchmark before building "
                        "versions B to E.")
for i, (v, l) in enumerate([("26M", "ad impressions\n(+ ad features, user profiles)"), ("28", "tables in look-alike\nfamilies"),
                            ("120", "benchmark questions + 20\nthree-turn conversations"), ("222", "extra distractor tables\nfor the scale test")]):
    stat(s, 0.6 + i * 3.1, 1.9, 2.85, v, l)
rows = [("Dimensions", "dim_ad, dim_campaign, dim_user, dim_date ..."),
        ("Events", "fact_ad_events: every impression and click"),
        ("Look-alike families", "hourly / daily / weekly · all vs valid traffic · by audience · reach · live last 6 h"),
        ("Benchmark", "40 easy · 40 medium (joins) · 40 tricky (traps); 40 practice / 80 test; frozen before building")]
for i, (a, b) in enumerate(rows):
    y = 4.2 + i * 0.68
    text(s, 0.6, y, 2.6, 0.6, a, size=16, color=NAVY, bold=True)
    text(s, 3.3, y, 9.4, 0.6, b, size=16, color=INK)

# ---------- 4. architecture ----------
s = content_slide("Architecture: RAG + table map + agent", "All data tools sit behind one MCP server that can only read",
                  notes="One-time prep builds tables and description cards. Qdrant searches the cards, Neo4j knows how "
                        "tables join and which ones look alike, DuckDB holds the data. All tools sit behind one MCP "
                        "server that can only read. The LangGraph agent calls those tools, with hard limits and memory.")
s.shapes.add_picture("docs/architecture.png", Inches(1.17), Inches(1.75), width=Inches(11.0))
text(s, 0.6, 6.45, 12.1, 0.6, [[("Safety lives in the server: ", {"bold": True, "color": NAVY}),
                                ("read-only, no file access · one SELECT · 28 tables only · 1,000 rows · 20 s · 12/12 attacks blocked", {})]],
     size=15, color=INK)

# ---------- 5. versions ----------
s = content_slide("Five versions, one idea at a time",
                  "Every version answers the same frozen questions, so each step is measured",
                  notes="This avoids complexity bias. A is the simple baseline: show every card. Each next version adds "
                        "exactly one idea, so we can see what each idea is worth.")
versions = [("A", "No search", "all 28 table cards\nin the prompt"), ("B", "Basic search", "top 5 cards by\nmeaning (RAG)"),
            ("C", "Smart search", "rewrite + hybrid\n+ re-rank"), ("D", "Search + map", "+ join routes and\nlook-alikes (GraphRAG)"),
            ("E", "Agent", "LangGraph ReAct over\n6 MCP tools + memory")]
for i, (code, name, desc) in enumerate(versions):
    x = 0.6 + i * 2.48
    box(s, x, 2.2, 2.2, 3.2, fill=NAVY if code == "E" else TINT)
    fg = WHITE if code == "E" else NAVY
    text(s, x, 2.4, 2.2, 0.9, code, size=44, color=ACCENT if code == "E" else NAVY, bold=True, align=PP_ALIGN.CENTER)
    text(s, x + 0.15, 3.35, 1.9, 0.5, name, size=19, color=fg, bold=True, align=PP_ALIGN.CENTER)
    text(s, x + 0.15, 3.95, 1.9, 1.2, desc, size=14, color=WHITE if code == "E" else INK, align=PP_ALIGN.CENTER)
    if i < 4:
        a = s.shapes.add_shape(MSO_SHAPE.RIGHT_ARROW, Inches(x + 2.24), Inches(3.65), Inches(0.2), Inches(0.3))
        a.fill.solid()
        a.fill.fore_color.rgb = BAR
        a.line.fill.background()
text(s, 0.6, 5.85, 12.1, 0.8, "E also runs with example memory: 34 solved practice questions recalled as examples "
     "(test questions can never enter memory).", size=15, color=MUTED)

# ---------- 6. evaluation ----------
s = content_slide("How we tested: a fair, frozen exam",
                  "Built and fixed on 40 practice questions; judged once on 80 unseen test questions",
                  notes="Execution accuracy is the main score: run the SQL, compare rows with the correct answer. Three "
                        "runs per version, bootstrap confidence intervals, and McNemar tests before claiming any gain. "
                        "Plus an LLM judge and my own grading of 30 answers.")
cells = [("Execution accuracy", "run the AI's SQL; its rows must match the correct answer"),
         ("3 runs × 80 questions", "the AI isn't deterministic, so average it"),
         ("95% confidence intervals", "bootstrap: re-draw the questions 10,000 times"),
         ("McNemar test", "is a difference real? p < 0.05 to claim a gain"),
         ("LLM-as-a-judge", "gpt-5 grades every answer, blind to version and gold"),
         ("Human check", "I graded 30 answers: kappa 0.65 vs the AI judge")]
for i, (head, body) in enumerate(cells):
    x, y = 0.6 + (i % 3) * 4.1, 1.95 + (i // 3) * 2.35
    box(s, x, y, 3.8, 2.05)
    circle_number(s, x + 0.3, y + 0.3, i + 1)
    text(s, x + 1.05, y + 0.3, 2.6, 0.7, head, size=17, color=NAVY, bold=True)
    text(s, x + 0.3, y + 1.05, 3.25, 0.9, body, size=15, color=INK)

# ---------- 7. results ----------
names = {"A": "A. No search", "B": "B. Basic search", "C": "C. Smart search", "D": "D. Search + map",
         "E": "E. Agent", "E_memory": "E + memory"}
s = content_slide("Results: A and agent + memory are tied",
                  "Execution accuracy, 80 test questions, mean of 3 runs (95% confidence interval in notes)",
                  notes="E with example memory: 92.5% (88–96). A: 90.4% (84–96). E: 80.0%. D: 76.7%. B: 75.8%. "
                        "C: 68.3%. Real differences by McNemar: A beats D, memory beats no memory (15 fixed, 0 broken), "
                        "both holding after a Bonferroni correction; A beats B at p = 0.0063, borderline. A vs E + memory "
                        "is not significant (p = 0.11): a tie. E + memory was picked after seeing test results, so 92.5% "
                        "is somewhat optimistic.")
vals = [round(Q[v]["accuracy"] * 100, 1) for v in names]
bar_chart(s, 0.6, 1.75, 8.3, 5.3, list(names.values()), vals,
          [BAR, BAR, BAR, BAR, BAR, ACCENT], "Accuracy on unseen test questions (%)")
stat(s, 9.3, 1.85, 3.4, "92.5%", "agent + example memory\n(95% CI 88–96)", value_color=ACCENT, h=1.75)
text(s, 9.3, 3.85, 3.4, 3.2, [[("Real differences", {"bold": True, "color": NAVY})],
                              "• A beats D (B: borderline)", "• memory beats no memory",
                              [("Statistical tie (p = 0.11)", {"bold": True, "color": NAVY})], "• A vs agent + memory"],
     size=15, color=INK)

# ---------- 8. memory ----------
e, en = CONV["E"], CONV["E_nochat"]
s = content_slide("Memory: follow-ups go from 0% to 90%",
                  "15 test conversations × 3 turns, e.g. “…now split that by gender”",
                  notes="Without chat memory, turns 2 and 3 are impossible: 0%. With it, about 90%. Example memory "
                        "adds 12.5 points on single questions. Honesty check: 56 of 80 test questions share a template "
                        "with a practice example, but on the other 24 memory still lifts E from 72% to 85%.")
data = CategoryChartData()
data.categories = ["Turn 1", "Turn 2", "Turn 3"]
data.add_series("Chat memory ON", [round(v * 100) for v in e["turns"]])
data.add_series("Chat memory OFF", [round(v * 100) for v in en["turns"]])
chart = s.shapes.add_chart(XL_CHART_TYPE.COLUMN_CLUSTERED, Inches(0.6), Inches(1.75), Inches(7.6), Inches(5.3), data).chart
chart.has_title = True
chart.chart_title.text_frame.text = "Follow-up accuracy by turn (%)"
tr = chart.chart_title.text_frame.paragraphs[0].runs[0]
tr.font.size, tr.font.bold, tr.font.color.rgb, tr.font.name = Pt(14), True, INK, FONT
chart.has_legend = True
chart.legend.include_in_layout = False
chart.legend.font.size, chart.legend.font.name = Pt(13), FONT
plot = chart.plots[0]
plot.gap_width, plot.overlap = 60, 0
plot.has_data_labels = True
plot.data_labels.number_format, plot.data_labels.number_format_is_linked = '0"%"', False
plot.data_labels.position = XL_LABEL_POSITION.OUTSIDE_END
plot.data_labels.font.size, plot.data_labels.font.name = Pt(13), FONT
for series, color in zip(plot.series, [ACCENT, BAR]):
    series.format.fill.solid()
    series.format.fill.fore_color.rgb = color
chart.value_axis.maximum_scale, chart.value_axis.minimum_scale = 110, 0
chart.value_axis.visible = False
chart.value_axis.major_gridlines.format.line.color.rgb = LINE
chart.category_axis.tick_labels.font.size, chart.category_axis.tick_labels.font.name = Pt(13), FONT
stat(s, 8.6, 1.85, 4.1, f"{e['accuracy'] * 100:.0f}% vs {en['accuracy'] * 100:.0f}%", "all turns, chat memory on vs off", h=1.75)
stat(s, 8.6, 3.85, 4.1, "+12.5", "points from example memory\n(72% → 85% even on unseen templates)", value_color=ACCENT, h=2.0)

# ---------- 9. smart search + scale ----------
abl = S["ablation"]
s = content_slide("Two surprises: smart search hurt, A scaled",
                  notes="Turning off rewrite or re-rank made C better. Search ranks tables one at a time and misses "
                        "the lookup table a join needs. On scale: A stays at 90% with 250 tables, but its prompt grows "
                        "from 3k to 29k tokens and cost goes up 6 times; search versions cost the same at any size.")
cats = ["C: all 3 tricks", "C without rewrite", "C without hybrid", "C without re-rank", "B: no tricks"]
vals = [Q["C"]["accuracy"], abl["C_no_rewrite"]["accuracy"], abl["C_no_hybrid"]["accuracy"],
        abl["C_no_rerank"]["accuracy"], Q["B"]["accuracy"]]
bar_chart(s, 0.6, 1.4, 6.6, 5.6, cats, [round(v * 100, 1) for v in vals], [ACCENT, BAR, BAR, BAR, NAVY],
          "Smart search ablation: accuracy (%)", horizontal=True)
cat = S["catalog"]
text(s, 7.7, 1.55, 5.0, 0.5, "Bigger catalog: cost per question", size=17, color=NAVY, bold=True)
rows = [("Tables", "28", "100", "250")] + [
    (v, *[f"${cat[v][k]['avg_cost_usd']:.4f}" for k in ("28", "100", "250")]) for v in ("A", "B", "C", "D")]
tbl = s.shapes.add_table(len(rows), 4, Inches(7.7), Inches(2.15), Inches(5.0), Inches(2.6)).table
for r, row in enumerate(rows):
    for c, val in enumerate(row):
        cell = tbl.cell(r, c)
        cell.text = val
        para = cell.text_frame.paragraphs[0]
        para.runs[0].font.size, para.runs[0].font.name = Pt(15), FONT
        para.runs[0].font.bold = r == 0 or (r == 1 and c > 0)
        para.runs[0].font.color.rgb = WHITE if r == 0 else (ACCENT if r == 1 and c == 3 else INK)
        para.alignment = PP_ALIGN.CENTER if c else PP_ALIGN.LEFT
        cell.fill.solid()
        cell.fill.fore_color.rgb = NAVY if r == 0 else (TINT if r % 2 else WHITE)
text(s, 7.7, 5.0, 5.0, 1.9, ["A keeps 90% accuracy at 250 tables, but costs 6× more; at thousands of tables it won't fit.",
                             "B, C and D cost the same at any size."], size=15, color=INK)

# ---------- 10. failures ----------
order = ["wrong_calculation", "missing_connecting_table", "strict_grading", "wrong_lookalike", "not_sure"]
label = {"wrong_calculation": "Wrong calculation", "missing_connecting_table": "Missed the lookup table",
         "strict_grading": "Right value, strict format", "wrong_lookalike": "Wrong look-alike table", "not_sure": "Said “not sure”"}
other = sum(n for t, n in FAIL.items() if t not in order)
s = content_slide("Why answers fail: joins and look-alikes",
                  f"All {sum(FAIL.values())} wrong answers (first test run of every version), sorted by type",
                  notes="Most failures are a missing lookup table (search finds the summary table but not dim_user) "
                        "or a similar-looking wrong table. 17 answers had the right value but failed our strict, "
                        "frozen format rules, mostly the agent's ranked lists. I checked 27 labels by hand and agreed with 24.")
bar_chart(s, 0.6, 1.75, 7.4, 5.3, [label[t] for t in order] + ["Other"], [FAIL[t] for t in order] + [other],
          [ACCENT, ACCENT, BAR, ACCENT, BAR, BAR], "Wrong answers by type (count)", horizontal=True, fmt="0",
          axis_max=32)
examples = [("Missed the lookup table", "“high-spending users” answered from a brand summary, without joining dim_user"),
            ("Wrong look-alike", "valid-traffic table used when all traffic was asked"),
            ("Wrong calculation", "audience table has a row per age level; rows not added up")]
for i, (head, body) in enumerate(examples):
    y = 1.85 + i * 1.72
    box(s, 8.4, y, 4.3, 1.5)
    text(s, 8.65, y + 0.18, 3.9, 0.4, head, size=16, color=NAVY, bold=True)
    text(s, 8.65, y + 0.62, 3.9, 0.8, body, size=14, color=INK)

# ---------- 11. pivots ----------
s = content_slide("What went wrong, and how we pivoted",
                  notes="Every one of these changes was made on practice questions only and is written up in the README, "
                        "including the negative result for advanced RAG.")
pivots = [("D lost tables B had found", "start D from B's 5 search hits (practice 77.5% → 85%)"),
          ("Agent wrote SQL it never ran", "grade only SQL that actually ran; otherwise “not sure”"),
          ("Agent wasted steps hunting for names", "add data facts and working habits to its prompt (75% → 85%)"),
          ("langchain-mcp-adapters broke FastMCP", "a 25-line bridge using FastMCP's own client"),
          ("Final runs would take 3.5 hours", "5 parallel runs, one search-index copy each: about 2 hours")]
for i, (problem, fix) in enumerate(pivots):
    y = 1.5 + i * 1.08
    circle_number(s, 0.6, y + 0.15, i + 1, fill=ACCENT)
    box(s, 1.4, y, 5.2, 0.85)
    text(s, 1.65, y, 4.8, 0.85, problem, size=16, color=INK, bold=True, anchor=MSO_ANCHOR.MIDDLE)
    a = s.shapes.add_shape(MSO_SHAPE.RIGHT_ARROW, Inches(6.75), Inches(y + 0.27), Inches(0.45), Inches(0.32))
    a.fill.solid()
    a.fill.fore_color.rgb = BAR
    a.line.fill.background()
    box(s, 7.35, y, 5.35, 0.85, fill=WHITE, line=LINE)
    text(s, 7.6, y, 5.0, 0.85, fix, size=16, color=INK, anchor=MSO_ANCHOR.MIDDLE)

# ---------- 12. code review ----------
s = content_slide("A code review found real problems, now fixed",
                  "Reviewed after the final runs; every fix is in the README",
                  notes="An outside review found a security gap: a plain SELECT could read local files such as .env. "
                        "File access is now switched off and only the 28 warehouse tables can be read; re-checking all "
                        "3,280 earlier queries, no score changed. It also found two agent bugs. Because they were found by "
                        "reading test answers, the fixed agent is reported separately as a post-hoc result, not swapped in.")
fixes = [("Security", "SELECT could read files (.env)", "file access off + 28-table allow-list · 12/12 attacks blocked"),
         ("Agent", "long results broke JSON; SQL shown but never run", "rows trimmed, not text · sent back once to run it"),
         ("Scoring", "greedy column match", "backtracking (re-scored 666 answers: none changed)"),
         ("Claims", "8 tests, no correction; winner picked on test", "Bonferroni column · “tie with A” · optimism noted"),
         ("Tests", "no unit tests or CI", "27 unit tests, run on GitHub on every push")]
for i, (area, problem, fix) in enumerate(fixes):
    y = 1.85 + i * 0.86
    text(s, 0.6, y, 1.4, 0.7, area, size=16, color=NAVY, bold=True, anchor=MSO_ANCHOR.MIDDLE)
    text(s, 2.0, y, 3.9, 0.7, problem, size=15, color=INK, anchor=MSO_ANCHOR.MIDDLE)
    box(s, 6.1, y + 0.05, 3.7, 0.6, fill=TINT)
    text(s, 6.3, y + 0.05, 3.4, 0.6, fix, size=13, color=INK, anchor=MSO_ANCHOR.MIDDLE)
stat(s, 10.1, 1.85, 2.6, "84.2%", "E after fixes\n(was 80.0%)", value_color=ACCENT, h=2.0)
stat(s, 10.1, 4.05, 2.6, "95.0%", "E + memory after fixes\n(was 92.5%; still tied with A)", h=2.15)
text(s, 0.6, 6.45, 12.1, 0.5, "Post-hoc: reported next to the frozen results, never replacing them.", size=14, color=MUTED)

# ---------- 13. demo ----------
s = content_slide("Demo: ask it yourself",
                  "streamlit run app/streamlit_app.py  ·  every answer shows its SQL, result and tool calls",
                  notes="Live demo. Question 1 tests the valid-traffic trap. Question 2 is a follow-up that needs chat "
                        "memory. Question 3 tests reach versus impressions and the live table.")
demo = ["What was campaign 143747's CTR yesterday, excluding suspicious clicks?", "Now split that by gender",
        "How many unique people saw campaign 83237 in the last 6 hours?"]
tests = ["trap: valid vs all traffic", "follow-up: needs chat memory", "trap: reach vs impressions, live table"]
for i, (q, t) in enumerate(zip(demo, tests)):
    y = 2.0 + i * 1.5
    circle_number(s, 0.6, y + 0.3, i + 1)
    box(s, 1.4, y, 11.3, 1.2)
    text(s, 1.7, y + 0.15, 10.8, 0.5, f"“{q}”", size=18, color=NAVY, bold=True)
    text(s, 1.7, y + 0.68, 10.8, 0.4, t, size=15, color=MUTED)

# ---------- 14. conclusion ----------
s = dark_slide("At 28 tables the simple baseline and the agent with memory are tied. We ship the agent with memory because "
               "the real use needs follow-ups and a growing catalog; for one-shot questions on a small catalog, use A. "
               "Next stage: 'why did CTR drop?', with a multi-agent supervisor reusing the same MCP tools and test harness.")
text(s, 0.9, 0.7, 11.5, 0.9, "Final choice and lessons", size=36, color=WHITE, bold=True)
box(s, 0.9, 1.75, 5.6, 4.6, fill=RGBColor(0x22, 0x33, 0x55))
text(s, 1.2, 1.95, 5.1, 4.3, [[("Ship: agent + example memory", {"bold": True, "color": ACCENT, "size": 22})],
                              "92.5% on unseen questions (95.0% after fixes)", "the only one that does follow-ups (90%)",
                              "$0.002 and 8.6 s per question",
                              [("Tied with A (p = 0.11): for one-shot questions on a small catalog, use A", {"color": ICE})]],
     size=17, color=WHITE)
box(s, 6.85, 1.75, 5.6, 4.6, fill=RGBColor(0x22, 0x33, 0x55))
text(s, 7.15, 1.95, 5.1, 4.3, [[("Lessons", {"bold": True, "color": ACCENT, "size": 22})],
                               "Build the simple baseline first", "“Advanced” RAG isn't automatically better", "Get the code reviewed",
                               "The hard part is joins and look-alikes", "Memory matters most for an agent",
                               "Freeze the test and report everything"], size=17, color=WHITE)
text(s, 0.9, 6.6, 11.5, 0.5, "All 7 design-doc targets met  ·  code, results and notebooks in the repository  ·  Thank you!",
     size=15, color=ICE)

prs.core_properties.title, prs.core_properties.author = "AdsKG-Agent", "Anshika Chaurasia"
prs.save(OUT)
print(f"{OUT}: {len(prs.slides)} slides")
