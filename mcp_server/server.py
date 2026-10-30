"""M6: the MCP server "adskg" - one standard plug for all the data tools.

MCP (Model Context Protocol) is a standard way for any AI app to discover and call tools.
The agent (M7) uses these tools, and so could any other MCP app.

Tools:
  search_tables(question, k)       find tables by meaning (Qdrant)
  get_join_path(from_table, to_table)   shortest join route (Neo4j)
  list_lookalikes(table)           similar tables and how they differ (Neo4j)
  describe_table(table)            the table's card: meaning, grain, freshness, columns
  sample_rows(table, n)            a few real rows
  run_sql(sql)                     run ONE read-only SELECT (safety rules in safety.py)

Safety lives HERE, inside the server, so no app can get around it. Every call is logged to logs/mcp_calls.jsonl.

Run it (stdio, the way AI apps start MCP servers):
    .venv/bin/python mcp_server/server.py
"""
import functools
import json
import sys
import time
from datetime import datetime
from pathlib import Path

import duckdb
from fastmcp import FastMCP
from fastmcp.exceptions import ToolError

PROJECT = Path(__file__).resolve().parent.parent
sys.path += [str(PROJECT / "catalog"), str(PROJECT / "mcp_server")]

import graph  # noqa: E402
import safety  # noqa: E402
from make_cards import CARDS_DIR  # noqa: E402
from search import search_tables as qdrant_search  # noqa: E402

import yaml  # noqa: E402

DB_PATH = PROJECT / "data" / "ads.duckdb"
LOG_PATH = PROJECT / "logs" / "mcp_calls.jsonl"

CARDS = {p.stem: yaml.safe_load(p.read_text()) for p in sorted(CARDS_DIR.glob("*.yaml"))}

mcp = FastMCP("adskg", instructions=(
    "Tools for an ads data warehouse (Taobao ads, May 2017; now = 2017-05-13 23:59 China time). "
    "Find tables with search_tables, check look-alikes and join routes, then answer with one read-only run_sql."))

_con = None


def db():
    """One read-only database connection for the whole server."""
    global _con
    if _con is None:
        _con = duckdb.connect(str(DB_PATH), read_only=True)
    return _con


def logged(fn):
    """Write one line per tool call to logs/mcp_calls.jsonl (tool, arguments, time, error)."""
    @functools.wraps(fn)
    def wrapper(*args, **kwargs):
        start, error = time.time(), ""
        try:
            result = fn(*args, **kwargs)
            if isinstance(result, dict):
                error = result.get("error", "")
            return result
        except Exception as e:
            error = f"{type(e).__name__}: {e}"
            raise
        finally:
            LOG_PATH.parent.mkdir(exist_ok=True)
            with open(LOG_PATH, "a") as f:
                f.write(json.dumps({"time": datetime.now().isoformat(timespec="seconds"), "tool": fn.__name__,
                                    "args": kwargs or [str(a) for a in args],
                                    "seconds": round(time.time() - start, 3), "error": error}) + "\n")
    return wrapper


def check_table(table):
    """Only real warehouse tables are allowed (stops anything sneaky in a table name)."""
    if table not in CARDS:
        raise ToolError(f"unknown table '{table}'. Use search_tables to find table names.")


@mcp.tool
@logged
def search_tables(question: str, k: int = 5) -> list[dict]:
    """Find the k tables whose description best matches the question (search by meaning)."""
    k = max(1, min(k, 10))
    return [{"table": t, "score": s, "description": CARDS[t]["description"]} for t, s in qdrant_search(question, k=k)]


@mcp.tool
@logged
def get_join_path(from_table: str, to_table: str) -> dict:
    """Shortest route of joins between two tables (at most 3 steps), with the join column for each step."""
    check_table(from_table)
    check_table(to_table)
    path = graph.get_join_path(from_table, to_table)
    steps = [{"from": a, "to": b, "on": graph.join_keys(a, b)} for a, b in zip(path, path[1:])]
    return {"path": path, "steps": steps}


@mcp.tool
@logged
def list_lookalikes(table: str) -> list[dict]:
    """Tables that look similar to this one but answer a different question, and what differs."""
    check_table(table)
    return [{"table": t, "differs_by": d, "description": CARDS[t]["description"]} for t, d in graph.list_lookalikes(table)]


@mcp.tool
@logged
def describe_table(table: str) -> dict:
    """The table's card: what it means, one row = ?, freshness, traffic, columns, dates, joins."""
    check_table(table)
    c = CARDS[table]
    return {k: c.get(k) for k in ["table", "description", "grain", "freshness", "traffic",
                                  "columns", "row_count", "date_range", "joins", "lookalikes"]}


@mcp.tool
@logged
def sample_rows(table: str, n: int = 5) -> dict:
    """A few real rows from a table (at most 20)."""
    check_table(table)
    n = max(1, min(n, 20))
    rows, columns, error = safety.run_sql(db(), f"SELECT * FROM {table} LIMIT {n}")
    return {"columns": columns, "rows": [[str(v) for v in r] for r in rows], "error": error}


@mcp.tool
@logged
def run_sql(sql: str) -> dict:
    """Run ONE read-only SELECT query (DuckDB SQL). At most 1,000 rows; stopped after 20 seconds."""
    rows, columns, error = safety.run_sql(db(), sql)
    return {"columns": columns, "rows": [[str(v) for v in r] for r in rows], "row_count": len(rows),
            "truncated": len(rows) == safety.MAX_ROWS, "error": error}


if __name__ == "__main__":
    mcp.run(show_banner=False)   # stdio: the AI app starts this script and talks to it over stdin/stdout
