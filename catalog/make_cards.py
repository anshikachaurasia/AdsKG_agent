"""M2 step 1: make one description card per table.

A card = hand-written notes (table_notes.yaml) + facts read from the database
(columns, row count, date range, example values).

Run from the project folder:
    .venv/bin/python catalog/make_cards.py
"""
from pathlib import Path

import duckdb
import yaml

PROJECT = Path(__file__).resolve().parent.parent
DB_PATH = PROJECT / "data" / "ads.duckdb"
NOTES_PATH = PROJECT / "catalog" / "table_notes.yaml"
CARDS_DIR = PROJECT / "catalog" / "cards"

DATE_COLUMNS = ["event_date", "event_hour", "week_start", "date"]


def table_facts(con, table):
    """Read columns, row count, date range and 3 example rows from the database."""
    columns = [{"name": name, "type": col_type}
               for name, col_type, *_ in con.execute(f"DESCRIBE {table}").fetchall()]
    row_count = con.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]

    date_range = None
    for col in DATE_COLUMNS:
        if col in [c["name"] for c in columns]:
            first, last = con.execute(f"SELECT MIN({col}), MAX({col}) FROM {table}").fetchone()
            date_range = f"{first} to {last}"
            break

    rows = con.execute(f"SELECT * FROM {table} LIMIT 3").fetchall()
    names = [c["name"] for c in columns]
    examples = [{n: str(v) for n, v in zip(names, row)} for row in rows]

    return {"columns": columns, "row_count": row_count, "date_range": date_range, "examples": examples}


def card_text(card):
    """The text that gets turned into a vector and searched. Plain words, no YAML."""
    columns = ", ".join(c["name"] for c in card["columns"])
    return (
        f"Table {card['table']}. {card['description']} "
        f"One row = {card['grain']}. Freshness: {card['freshness']}. Traffic: {card['traffic']}. "
        f"Columns: {columns}."
    )


def make_cards():
    notes = yaml.safe_load(NOTES_PATH.read_text())
    con = duckdb.connect(str(DB_PATH), read_only=True)
    CARDS_DIR.mkdir(exist_ok=True)

    for table, note in notes.items():
        card = {"table": table, **note, **table_facts(con, table)}
        card["search_text"] = card_text(card)
        path = CARDS_DIR / f"{table}.yaml"
        path.write_text(yaml.safe_dump(card, sort_keys=False, allow_unicode=True))
        print(f"  wrote {path.name}")

    con.close()
    print(f"\n{len(notes)} cards written to {CARDS_DIR}")


if __name__ == "__main__":
    make_cards()
