# AdsKG-Agent: 3-minute demo video

A shot-by-shot script for the demo video, with the exact words to say, what to show, and a checklist for recording.
Spoken text is about 340 words (about 2.5 minutes at a calm pace), which leaves room for the app to answer. Aim to finish at **2:50**.

---

## Before you record (10 minutes)

1. **Start Neo4j:** `/opt/homebrew/opt/neo4j/bin/neo4j start`
2. **Start the app:** `.venv/bin/streamlit run app/streamlit_app.py`, then ask one warm-up question.
   The first answer is slow because it loads the search models. Then click **New conversation**.
3. **Open, each in its own window or tab:**
   - the app (browser, zoom 125%)
   - `docs/AdsKG_Agent_Presentation.pptx`: slides 2, 4, 7, 8, 10 and 13 are used below
   - the README on GitHub, scrolled to **Failure analysis**
4. **Screen recorder:** on a Mac, QuickTime → File → New Screen Recording (or Cmd+Shift+5). Record at 1080p
   with the microphone on. Close notifications (Focus mode on).
5. **Do one silent practice run** of the three demo questions so you know roughly how long each answer takes
   (about 10 s). Keep talking while it works, or cut the waiting time when editing.

---

## The script

| Time | Show | Say |
|---|---|---|
| **0:00–0:20** | Slide 2: *The problem* | "Ad teams ask simple *what happened* questions, like *what was campaign 143747's CTR yesterday, excluding suspicious clicks?* Writing the SQL is the easy part. The hard part is picking the right table, because the warehouse has many that look alike: hourly or daily, all traffic or valid traffic, impressions or unique people." |
| **0:20–0:40** | Slide 4: *Architecture* | "I built 28 tables from the public Taobao ads data. Each table has a description card in Qdrant for search, a map of joins and look-alikes in Neo4j, and the data in DuckDB. All tools sit behind one MCP server that can only read the 28 tables. A LangGraph agent uses those tools, with chat memory and a memory of solved examples." |
| **0:40–1:15** | App: type **What was campaign 143747's CTR yesterday, excluding suspicious clicks?** → open *How I got this* | "It searched, compared the look-alike tables, and picked the *valid-traffic* daily table, not the all-traffic one. Here's the exact SQL it ran, the result, and every tool call. Nothing is hidden." |
| **1:15–1:40** | App: type **Now split that by gender** | "This is a follow-up. Chat memory knows what *that* means. It also warns me that the gender table includes all traffic, so suspicious clicks can't be removed there. That's the kind of caveat a careful analyst would give." |
| **1:40–1:55** | App: type **How many unique people saw campaign 83237 in the last 6 hours?** | "*Unique people* means reach, not impressions, and *last 6 hours* means the live table. These traps are exactly what the benchmark tests." |
| **1:55–2:25** | Slide 7: *Results* | "I compared five versions on 80 test questions I never used while building, three runs each. Showing every table card (version A) scores 90%. The agent with example memory scores 92.5%, but statistically those two are tied. Search-based versions land around 70 to 77%, and advanced RAG tricks actually made things worse." |
| **2:25–2:40** | Slide 8: *Memory* | "Memory is what makes the agent worth it: follow-up questions go from 0% without chat memory to 90% with it. That's why I ship the agent; for one-shot questions on a small catalog, the simple version A is just as good." |
| **2:40–2:55** | Slide 10: *Why answers fail* | "Most remaining errors aren't SQL syntax. They're a missing lookup table or a similar-looking wrong table. Everything, including the negative results, is in the README." |
| **2:55–3:00** | Slide 13 (conclusion) or the GitHub page | "Thanks for watching." |

---

## If something goes wrong while recording

- **An answer takes long:** keep talking about what it's doing ("it's checking the look-alike tables now"), or
  cut the wait when editing.
- **The agent says "not sure" or gets one wrong:** that's fine and honest. Say "it says *not sure* rather than
  guessing, which is the behaviour I wanted." Or re-record that question.
- **The app errors:** check that Neo4j is running (`/opt/homebrew/opt/neo4j/bin/neo4j status`) and restart the app.
- **Running over 3:00:** drop the 1:40 question or the *Why answers fail* slide; both are optional.

---

## Key numbers (so you say them correctly)

| What | Number |
|---|---|
| Test questions / runs | 80 unseen test questions, 3 runs per version |
| A: show every table card | 90.4% |
| E + example memory | 92.5% (tied with A, p = 0.11) |
| E, the agent without example memory | 80.0% |
| Search versions B / C / D | 75.8% / 68.3% / 76.7% |
| Follow-ups, turns 2–3 | 0% without chat memory → about 90% with it |
| Cost and speed (E + memory) | about $0.002 and 8.6 s per question |

---

## After recording

1. Watch it once. Check that the sound is clear and the screen text is readable.
2. Export as MP4 (QuickTime: File → Export As → 1080p).
3. Upload it (YouTube *unlisted*, Google Drive or Loom) and set it so anyone with the link can view.
4. Put the link in the README's *What's in this repository* table (or ask Claude to add it), and in your
   submission form.
