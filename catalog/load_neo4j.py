"""M5 step 1: build the table map (knowledge graph) in Neo4j.

What goes in:
  (:Table)   one per warehouse table, with grain / freshness / traffic
  (:Column)  (Table)-[:HAS_COLUMN]->(Column)
  (:Metric)  impressions, clicks, ctr, reach ...      (Table)-[:HAS_METRIC]->(Metric)
  (:Entity)  advertiser, campaign, ad, brand ...      (Entity)-[:HOME_TABLE]->(Table)
             business hierarchy: advertiser -[:OWNS]-> campaign -[:OWNS]-> ad
  (:Term)    business words people use               (Term)-[:MEANS]->(Metric or Entity)

How tables connect:
  (Table)-[:JOINS_WITH {on}]->(Table)       a table and the lookup table of a key column it has
  (Table)-[:LOOKALIKE_OF {differs_by}]->(Table)   from the cards: similar tables, different answer
  (Table)-[:ROLLS_UP_TO]->(Table)           hourly -> daily -> weekly

Run from the project folder (Neo4j must be running):
    .venv/bin/python catalog/load_neo4j.py
"""
import os
import sys
from pathlib import Path

import yaml
from dotenv import load_dotenv
from neo4j import GraphDatabase

PROJECT = Path(__file__).resolve().parent.parent
sys.path.append(str(PROJECT / "catalog"))
CARDS_DIR = PROJECT / "catalog" / "cards"
load_dotenv(PROJECT / ".env")

# key column -> the lookup ("home") table for it
KEY_HOME = {
    "ad_id": "dim_ad",
    "campaign_id": "dim_campaign",
    "advertiser_id": "dim_advertiser",
    "brand_id": "dim_ad",
    "category_id": "dim_ad",
    "user_id": "dim_user",
    "placement_id": "dim_placement",
    "event_date": "dim_date",
}

# business entities, their home table, and the words people use for them
ENTITIES = {
    "advertiser": ("dim_advertiser", ["advertiser", "advertisers", "customer"]),
    "campaign": ("dim_campaign", ["campaign", "campaigns"]),
    "ad": ("dim_ad", ["ad", "ads", "item price", "price"]),
    "brand": ("dim_ad", ["brand", "brands"]),
    "category": ("dim_ad", ["category", "categories", "product category"]),
    "user": ("dim_user", ["gender", "male", "female", "men", "women", "age", "student", "students",
                          "shopper", "shoppers", "shopping", "spending", "city", "audience", "demographics"]),
    "placement": ("dim_placement", ["placement", "placements", "position"]),
    "date": ("dim_date", ["weekday", "weekend", "day of the week", "saturday", "saturdays", "sunday", "sundays"]),
}
HIERARCHY = [("advertiser", "campaign"), ("campaign", "ad")]

# metrics: the column that holds them, and the words people use for them
METRICS = {
    "impressions": ("impressions", ["impressions", "views", "shown", "times shown"]),
    "clicks": ("clicks", ["clicks", "clicked"]),
    "ctr": ("ctr", ["ctr", "click-through rate", "click through rate"]),
    "reach": ("unique_users", ["reach", "unique people", "unique users", "distinct users", "different people"]),
    "est_value": ("est_value", ["estimated value", "value"]),
    "frequency": ("avg_frequency", ["frequency", "how many times did each person"]),
}

ROLL_UPS = [("agg_ad_hourly", "agg_ad_daily"), ("agg_ad_daily", "agg_ad_weekly"),
            ("agg_campaign_hourly", "agg_campaign_daily"), ("agg_campaign_daily", "agg_campaign_weekly"),
            ("agg_campaign_hourly_valid", "agg_campaign_daily_valid")]


def get_driver():
    return GraphDatabase.driver(os.environ["NEO4J_URI"], auth=(os.environ["NEO4J_USER"], os.environ["NEO4J_PASSWORD"]))


def load_cards():
    """Our 28 tables only (the distractors are added at the end of build_graph)."""
    return {p.stem: yaml.safe_load(p.read_text()) for p in sorted(CARDS_DIR.glob("*.yaml"))}


def differs_by(a, b):
    """Which of grain / freshness / traffic differ between two look-alike tables."""
    return [field for field in ["grain", "freshness", "traffic"] if a[field] != b[field]] or ["what is counted"]


def build_graph():
    cards = load_cards()
    driver = get_driver()
    run = lambda query, **params: driver.execute_query(query, **params)

    run("MATCH (n) DETACH DELETE n")   # start from an empty graph every time

    # tables and columns
    for name, c in cards.items():
        run("CREATE (:Table {name: $name, description: $description, grain: $grain, freshness: $freshness, "
            "traffic: $traffic})", name=name, description=c["description"], grain=c["grain"],
            freshness=c["freshness"], traffic=c["traffic"])
        for col in c["columns"]:
            run("MATCH (t:Table {name: $table}) CREATE (t)-[:HAS_COLUMN]->(:Column {name: $name, type: $type, table: $table})",
                table=name, name=col["name"], type=col["type"])

    # joins: every table with a key column joins to that key's home table
    for name, c in cards.items():
        for col in [col["name"] for col in c["columns"]]:
            home = KEY_HOME.get(col)
            if home and home != name:
                on = "event_date = date" if col == "event_date" else col
                run("MATCH (a:Table {name: $a}), (b:Table {name: $b}) MERGE (a)-[:JOINS_WITH {on: $on}]->(b)",
                    a=name, b=home, on=on)
    # the suspicious-traffic list joins the event table on user + hour
    run("MATCH (a:Table {name: 'ref_suspicious_user_hours'}), (b:Table {name: 'fact_ad_events'}) "
        "MERGE (a)-[:JOINS_WITH {on: 'user_id, event_hour'}]->(b)")

    # look-alikes and roll-ups
    for name, c in cards.items():
        for other in c.get("lookalikes") or []:
            run("MATCH (a:Table {name: $a}), (b:Table {name: $b}) MERGE (a)-[:LOOKALIKE_OF {differs_by: $d}]->(b)",
                a=name, b=other, d=differs_by(c, cards[other]))
    for small, big in ROLL_UPS:
        run("MATCH (a:Table {name: $a}), (b:Table {name: $b}) MERGE (a)-[:ROLLS_UP_TO]->(b)", a=small, b=big)

    # metrics and their words
    for metric, (column, words) in METRICS.items():
        run("CREATE (:Metric {name: $m, column: $col})", m=metric, col=column)
        run("MATCH (m:Metric {name: $m}), (t:Table)-[:HAS_COLUMN]->(:Column {name: $col}) MERGE (t)-[:HAS_METRIC]->(m)",
            m=metric, col=column)
        for w in words:
            run("MATCH (m:Metric {name: $m}) MERGE (w:Term {text: $w}) MERGE (w)-[:MEANS]->(m)", m=metric, w=w)

    # business entities, hierarchy and their words
    for entity, (home, words) in ENTITIES.items():
        run("MATCH (t:Table {name: $home}) CREATE (e:Entity {name: $e})-[:HOME_TABLE]->(t)", e=entity, home=home)
        for w in words:
            run("MATCH (e:Entity {name: $e}) MERGE (w:Term {text: $w}) MERGE (w)-[:MEANS]->(e)", e=entity, w=w)
    for parent, child in HIERARCHY:
        run("MATCH (a:Entity {name: $a}), (b:Entity {name: $b}) MERGE (a)-[:OWNS]->(b)", a=parent, b=child)

    # M8: the distractor tables of the bigger-catalog test, with their own joins (foreign keys)
    from distractors import load_catalog
    extra = {name: c for name, c in load_catalog(250).items() if name not in cards}
    for name, c in extra.items():
        run("CREATE (:Table {name: $name, description: $description, grain: $grain, freshness: 'static', "
            "traffic: 'n/a', distractor: true})", name=name, description=c["description"], grain=c["grain"])
    for name, c in extra.items():
        for col, target in (c.get("joins") or {}).items():
            run("MATCH (a:Table {name: $a}), (b:Table {name: $b}) MERGE (a)-[:JOINS_WITH {on: $on}]->(b)",
                a=name, b=target, on=col)

    counts = run("MATCH (n) RETURN labels(n)[0] AS label, count(*) AS n ORDER BY label").records
    rels = run("MATCH ()-[r]->() RETURN type(r) AS type, count(*) AS n ORDER BY type").records
    driver.close()
    print("Nodes:        ", {r["label"]: r["n"] for r in counts})
    print("Relationships:", {r["type"]: r["n"] for r in rels})


if __name__ == "__main__":
    build_graph()
