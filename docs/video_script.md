# 3-minute demo video: script and shot list

**Before recording**
1. Start Neo4j: `/opt/homebrew/opt/neo4j/bin/neo4j start`
2. Start the app: `.venv/bin/streamlit run app/streamlit_app.py`, and ask one warm-up question (the first answer is slow: it loads models)
3. Have open: the app, `docs/AdsKG_Agent_Documentation.pdf` (page 1 diagram), `docs/accuracy_ci.png`, the README
4. Click **New conversation** in the app, then start recording

Each answer takes about 10 s. Keep talking while it works, or cut the wait in editing.

| Time | Show | Say (roughly) |
|---|---|---|
| 0:00–0:20 | Documentation page 1, title + problem | "Ad teams ask *what happened* questions. The hard part isn't SQL, it's picking the right table among look-alikes: hourly or daily, all traffic or valid, impressions or unique people. AdsKG-Agent finds the right tables, joins them, runs the query and shows its work." |
| 0:20–0:45 | Architecture diagram | "28 tables built from the Taobao ads data. Each has a description card in Qdrant, a map of joins and look-alikes in Neo4j, and the data in DuckDB. All tools sit behind one MCP server that can only read. A LangGraph agent calls those tools, with chat memory and memory of solved examples." |
| 0:45–1:25 | App: ask **"What was campaign 143747's CTR yesterday, excluding suspicious clicks?"** then open *How I got this* | "It found the *valid-traffic* daily table, not the all-traffic one. Here's the SQL, the result and every tool call. Nothing is hidden." |
| 1:25–1:55 | App: follow-up **"Now split that by gender"** | "A follow-up. Chat memory knows what *that* means. Without memory, follow-ups score 0%; with it, 90%." |
| 1:55–2:10 | App: ask **"How many unique people saw campaign 83237 in the last 6 hours?"** | "*Unique people* means reach, not impressions, and *last 6 hours* means the live table. These are the traps the benchmark tests." |
| 2:10–2:45 | `docs/accuracy_ci.png` | "I compared five versions on 80 test questions, 3 runs each. Showing every card (A) is a strong baseline at 28 tables. Basic, smart and graph search land around 70–77%. Advanced RAG actually hurt. The agent with example memory is best at 92.5%, significantly better than without memory." |
| 2:45–3:00 | README *Failure analysis* table | "Most remaining errors are wrong calculations and missing lookup joins. Some correct answers fail our strict format rules, and I report those honestly. Final choice: the agent with memory; for a tiny catalog, the simple baseline. Thanks!" |

**Tips:** record at 1080p with the browser zoomed to 125%. QuickTime → File → New Screen Recording works on a Mac.
Aim for 2:50 so there's room to spare.
