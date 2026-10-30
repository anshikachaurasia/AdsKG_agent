"""All versions. A, B and D are fixed pipelines (no agent): they only differ in WHICH table cards the AI sees.

  A. No search:    the AI gets all 28 table cards, then writes SQL.
  B. Basic search: Qdrant finds the 5 closest cards to the question; the AI only gets those.
  C. Smart search:  B + question rewriting, hybrid (meaning + keyword) search, re-ranking (smart_search.py).
  D. Search + map: B's 5 search hits, then the Neo4j table map adds lookup tables for business
                   words, the tables needed to join them, and look-alikes (at most 8 cards).
                   (For now D builds on B's search; it will use C's smart search once C exists, M8.)
  E. Agent:        see agent_graph.py - chooses MCP tools itself, retries, remembers.
"""
import atexit
import re
import sys
import uuid
from pathlib import Path


PROJECT = Path(__file__).resolve().parent.parent
sys.path.append(str(PROJECT / "catalog"))

from llm import ask  # noqa: E402
from distractors import load_catalog  # noqa: E402
from graph import expand_tables  # noqa: E402
from search import search_tables  # noqa: E402
from smart_search import smart_search  # noqa: E402

SYSTEM_PROMPT = """You write DuckDB SQL for an ads data warehouse (Taobao ads, May 2017).

Facts about time:
- "Now" is 2017-05-13 23:59 (China time). Today = 2017-05-13. Yesterday = 2017-05-12.
- The data covers 2017-05-06 to 2017-05-13.

Rules:
- Use ONLY the tables and columns listed below.
- Write exactly ONE read-only SELECT query.
- Return only the columns needed to answer the question.
- CTR is a fraction (clicks / impressions), not a percentage.
- Reply with the SQL inside a ```sql code block and nothing else.
"""


CARDS = load_catalog(28)          # our 28 tables
_catalogs = {28: CARDS}


def cards_for(config):
    """The catalog this run uses: 28 tables, or 100 / 250 with distractor tables (M8)."""
    size = config.get("catalog_size", 28)
    if size not in _catalogs:
        _catalogs[size] = load_catalog(size)
    return _catalogs[size]


def card_for_prompt(card):
    """The short version of a card that the AI reads."""
    columns = ", ".join(f"{c['name']} {c['type']}" for c in card["columns"])
    joins = ", ".join(f"{col} -> {target}" for col, target in (card.get("joins") or {}).items())
    lines = [
        f"### {card['table']}",
        card["description"],
        f"One row = {card['grain']}. Freshness: {card['freshness']}. Traffic: {card['traffic']}.",
        f"Columns: {columns}",
    ]
    if card.get("date_range"):
        lines.append(f"Dates: {card['date_range']}")
    if joins:
        lines.append(f"Joins: {joins}")
    return "\n".join(lines)


def extract_sql(text):
    """Take the SQL out of a ```sql ... ``` block (or use the whole reply)."""
    match = re.search(r"```(?:sql)?\s*(.*?)```", text, re.DOTALL | re.IGNORECASE)
    sql = match.group(1) if match else text
    return sql.strip().rstrip(";").strip()


def write_sql(question, tables, config):
    """Give the AI the cards for `tables` and the question; get SQL back."""
    cards = cards_for(config)
    cards_text = "\n\n".join(card_for_prompt(cards[t]) for t in tables)
    user = f"Tables:\n\n{cards_text}\n\nQuestion: {question}"
    reply, usage = ask(config["model"], SYSTEM_PROMPT, user, config.get("reasoning_effort"))
    return extract_sql(reply), usage


def version_a(question, config, thread_id=None):
    """A. No search: show the AI every table card."""
    tables = list(cards_for(config))
    sql, usage = write_sql(question, tables, config)
    return {"sql": sql, "tables_shown": tables, **usage}


def version_b(question, config, thread_id=None):
    """B. Basic search: show the AI only the k closest table cards."""
    tables = [t for t, _ in search_tables(question, k=config.get("k", 5), catalog_size=config.get("catalog_size", 28))]
    sql, usage = write_sql(question, tables, config)
    return {"sql": sql, "tables_shown": tables, **usage}


def version_c(question, config, thread_id=None):
    """C. Smart search: B + question rewriting, hybrid (meaning + keyword) search and re-ranking.
    Each piece can be switched off in the config (rewrite / hybrid / rerank) to test what helps."""
    tables, rewrite_usage = smart_search(
        question, k=config.get("k", 5), catalog_size=config.get("catalog_size", 28),
        use_rewrite=config.get("rewrite", True), use_hybrid=config.get("hybrid", True),
        use_rerank=config.get("rerank", True), model=config["model"])
    sql, usage = write_sql(question, tables, config)
    usage["tokens_in"] += rewrite_usage["tokens_in"]
    usage["tokens_out"] += rewrite_usage["tokens_out"]
    return {"sql": sql, "tables_shown": tables, **usage}


def version_d(question, config, thread_id=None):
    """D. Search + table map: search hits, plus the tables the map says are needed to join them."""
    tables = expand_tables(question, seeds=config.get("seeds", 5), max_tables=config.get("max_tables", 8),
                           catalog=cards_for(config), catalog_size=config.get("catalog_size", 28))
    sql, usage = write_sql(question, tables, config)
    return {"sql": sql, "tables_shown": tables, **usage}


_agent = None


def version_e(question, config, thread_id=None):
    """E. Agent: a LangGraph ReAct agent that picks MCP tools itself, retries, and remembers (agent_graph.py).
    The same thread_id = the same conversation (chat memory)."""
    global _agent
    if _agent is None:
        from agent_graph import AgentE     # imported here so A/B/D don't start the MCP server
        _agent = AgentE(config)
        atexit.register(_agent.close)
    if not config.get("chat_memory", True):
        thread_id = None
    return _agent.ask(question, thread_id or str(uuid.uuid4()))


VERSIONS = {"A": version_a, "B": version_b, "C": version_c, "D": version_d, "E": version_e}
