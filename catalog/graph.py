"""M5 step 2: ask the table map questions.

  get_join_path(a, b)        tables on the shortest join route from a to b (at most 3 steps)
  list_lookalikes(table)     similar tables, and how each one differs
  tables_for_terms(question) lookup tables for business words in the question ("gender" -> dim_user)
  expand_tables(question)    version D's rule: search + map -> at most 8 tables

The first three become MCP tools in M6.
"""
import re
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent))
from load_neo4j import get_driver  # noqa: E402
from search import search_tables  # noqa: E402

_driver = None


def query(cypher, **params):
    global _driver
    if _driver is None:
        _driver = get_driver()
    return _driver.execute_query(cypher, **params).records


def get_join_path(a, b, max_steps=3):
    """Table names on the shortest JOINS_WITH route from a to b, or [] if there is none."""
    if a == b:
        return [a]
    records = query(
        f"MATCH p = shortestPath((a:Table {{name: $a}})-[:JOINS_WITH*..{max_steps}]-(b:Table {{name: $b}})) "
        "RETURN [n IN nodes(p) | n.name] AS tables", a=a, b=b)
    return records[0]["tables"] if records else []


def join_keys(a, b):
    """The column(s) two neighbouring tables join on."""
    records = query("MATCH (:Table {name: $a})-[r:JOINS_WITH]-(:Table {name: $b}) RETURN r.on AS on", a=a, b=b)
    return records[0]["on"] if records else None


def list_lookalikes(table):
    """[(other_table, [what differs]), ...]"""
    records = query("MATCH (:Table {name: $t})-[r:LOOKALIKE_OF]->(o:Table) RETURN o.name AS name, r.differs_by AS d",
                    t=table)
    return [(r["name"], r["d"]) for r in records]


def tables_for_terms(question):
    """Home tables of the business entities named in the question (whole-word match)."""
    text = question.lower()
    records = query("MATCH (w:Term)-[:MEANS]->(:Entity)-[:HOME_TABLE]->(t:Table) RETURN w.text AS word, t.name AS table")
    found = []
    for r in records:
        if re.search(rf"\b{re.escape(r['word'])}\b", text) and r["table"] not in found:
            found.append(r["table"])
    return found


def expand_tables(question, seeds=5, max_tables=8, catalog=None, catalog_size=28):
    """Version D's rule for which cards the AI sees.

    1. search: the top `seeds` tables for the question (from Qdrant)
    2. words:  lookup tables for business words in the question ("category" -> dim_ad)
    3. joins:  every table on the shortest join route between any two of those
    4. look-alikes of the best search hit, so the AI can choose between them
    Kept in that order, without repeats, at most `max_tables` (and only tables in `catalog`, if given).
    """
    found = [t for t, _ in search_tables(question, k=seeds, catalog_size=catalog_size)]
    terms = tables_for_terms(question)
    start = list(dict.fromkeys(found + terms))

    bridges = []
    for i, a in enumerate(start):
        for b in start[i + 1:]:
            bridges += get_join_path(a, b)
    lookalikes = [t for t, _ in list_lookalikes(found[0])]

    ordered = list(dict.fromkeys(start + bridges + lookalikes))
    if catalog is not None:   # bigger-catalog test: only tables in this catalog
        ordered = [t for t in ordered if t in catalog]
    return ordered[:max_tables]


if __name__ == "__main__":
    q = " ".join(sys.argv[1:]) or "What was the CTR among heavy shoppers for campaign 12519 yesterday?"
    print(q)
    print("search :", [t for t, _ in search_tables(q, k=3)])
    print("words  :", tables_for_terms(q))
    print("D sees :", expand_tables(q))
