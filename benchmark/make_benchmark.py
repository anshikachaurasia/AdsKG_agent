"""M3 step 1: make the 120 test questions + 20 follow-up conversations, each with its correct (gold) SQL.

How it works:
  1. Each TEMPLATE is one kind of question with its gold SQL, written once by hand.
  2. Real IDs (campaigns, brands, ads ...) are picked from the data with a fixed random seed,
     so the same benchmark comes out every time. No ID is used twice.
  3. Each template is used 4 times -> 10 templates x 4 x 3 levels = 120 questions.

Writes:
  benchmark/questions.jsonl       one question per line
  benchmark/conversations.jsonl   one conversation (3 turns) per line
  benchmark/gold/*.sql            the correct SQL for each question / turn

Run from the project folder:
    .venv/bin/python benchmark/make_benchmark.py
"""
import json
import random
from pathlib import Path

import duckdb

PROJECT = Path(__file__).resolve().parent.parent
DB_PATH = PROJECT / "data" / "ads.duckdb"
BENCH = PROJECT / "benchmark"
GOLD = BENCH / "gold"
FROZEN = BENCH / "FROZEN.txt"

SEED = 42
YESTERDAY = "2017-05-12"
FINAL_DATES = ["2017-05-06", "2017-05-07", "2017-05-08", "2017-05-09", "2017-05-10", "2017-05-11", "2017-05-12"]


# ---------------------------------------------------------------------
# 1. ID pools: lists of IDs that have enough data to make a good question
# ---------------------------------------------------------------------
POOLS = {
    # campaigns with data on all 7 final days, at least 100 impressions each day
    "campaign": """
        SELECT campaign_id FROM agg_campaign_daily
        GROUP BY campaign_id HAVING COUNT(*) = 7 AND MIN(impressions) >= 100""",
    # campaigns whose clicks yesterday change when suspicious traffic is removed
    "campaign_suspicious": f"""
        SELECT a.campaign_id FROM agg_campaign_daily a
        JOIN agg_campaign_daily_valid v USING (event_date, campaign_id)
        WHERE a.event_date = '{YESTERDAY}' AND a.clicks <> v.clicks AND a.impressions >= 100""",
    # campaigns active in the last 6 hours
    "campaign_live": """
        SELECT campaign_id FROM live_campaign_last6h WHERE impressions >= 100 AND clicks >= 3""",
    # campaigns active today (13 May)
    "campaign_today": """
        SELECT campaign_id FROM agg_campaign_hourly WHERE event_hour >= '2017-05-13'
        GROUP BY campaign_id HAVING SUM(impressions) >= 100""",
    # campaigns with several ads, where one ad clearly had the most clicks yesterday
    "campaign_top_ad": f"""
        SELECT campaign_id FROM (
            SELECT campaign_id, clicks, MAX(clicks) OVER (PARTITION BY campaign_id) AS top
            FROM agg_ad_daily WHERE event_date = '{YESTERDAY}')
        GROUP BY campaign_id
        HAVING COUNT(*) >= 2 AND COUNT(*) FILTER (WHERE clicks = top) = 1 AND MAX(top) >= 3""",
    # campaigns where one day clearly had the most clicks
    "campaign_top_day": """
        SELECT campaign_id FROM (
            SELECT campaign_id, clicks, MAX(clicks) OVER (PARTITION BY campaign_id) AS top
            FROM agg_campaign_daily)
        GROUP BY campaign_id
        HAVING COUNT(*) = 7 AND COUNT(*) FILTER (WHERE clicks = top) = 1 AND MAX(top) >= 20""",
    # campaigns with at least 2 ads
    "campaign_multi_ad": """
        SELECT c.campaign_id FROM dim_campaign c JOIN reach_campaign_total r USING (campaign_id)
        WHERE c.num_ads >= 2 AND r.unique_users >= 500""",
    # ads with data on all 7 final days
    "ad": """
        SELECT ad_id FROM agg_ad_daily
        GROUP BY ad_id HAVING COUNT(*) = 7 AND MIN(impressions) >= 50""",
    # brands with data on all 7 final days
    "brand": """
        SELECT brand_id FROM agg_brand_daily
        GROUP BY brand_id HAVING COUNT(*) = 7 AND MIN(impressions) >= 200""",
    # advertisers with 2+ campaigns and data on all 7 final days
    "advertiser": """
        SELECT d.advertiser_id FROM agg_advertiser_daily d JOIN dim_advertiser a USING (advertiser_id)
        WHERE a.num_campaigns >= 2
        GROUP BY d.advertiser_id HAVING COUNT(*) = 7 AND MIN(d.impressions) >= 200""",
    # categories where one brand clearly had the most clicks yesterday
    "category_top_brand": f"""
        WITH brand_clicks AS (
            SELECT a.category_id, a.brand_id, SUM(d.clicks) AS clicks
            FROM agg_ad_daily d JOIN dim_ad a USING (ad_id)
            WHERE d.event_date = '{YESTERDAY}' AND a.brand_id IS NOT NULL
            GROUP BY a.category_id, a.brand_id),
        ranked AS (
            SELECT *, MAX(clicks) OVER (PARTITION BY category_id) AS top FROM brand_clicks)
        SELECT category_id FROM ranked
        GROUP BY category_id
        HAVING COUNT(*) >= 5 AND COUNT(*) FILTER (WHERE clicks = top) = 1 AND MAX(top) >= 10""",
}

# pairs (advertiser, category) with clicks yesterday, for advertisers selling in 2+ categories
PAIR_POOLS = {
    "advertiser_category": f"""
        SELECT a.advertiser_id, a.category_id
        FROM agg_ad_daily d JOIN dim_ad a USING (ad_id)
        WHERE d.event_date = '{YESTERDAY}'
          AND a.advertiser_id IN (SELECT advertiser_id FROM dim_ad GROUP BY 1 HAVING COUNT(DISTINCT category_id) >= 2)
        GROUP BY a.advertiser_id, a.category_id HAVING SUM(d.clicks) >= 3""",
    # (campaign, hour) where suspicious traffic changes the hourly clicks
    "campaign_hour_suspicious": """
        SELECT a.campaign_id, a.event_hour
        FROM agg_campaign_hourly a JOIN agg_campaign_hourly_valid v USING (event_hour, campaign_id)
        WHERE a.event_hour < '2017-05-13' AND a.clicks <> v.clicks AND a.impressions >= 50""",
}


# ---------------------------------------------------------------------
# 2. Question templates: {placeholders} are filled with picked values
# ---------------------------------------------------------------------
TEMPLATES = [
    # ---------------- EASY: one table, no joins ----------------
    dict(key="E1", tier="easy", needs=["campaign", "date"], tables=["agg_campaign_daily"],
         questions=["What was the CTR of campaign {campaign} on {date_text}?",
                    "Give me the click-through rate for campaign {campaign} on {date_text}."],
         sql="SELECT ctr FROM agg_campaign_daily WHERE campaign_id = {campaign} AND event_date = '{date}'"),
    dict(key="E2", tier="easy", needs=["ad", "date"], tables=["agg_ad_daily"],
         questions=["How many clicks did ad {ad} get on {date_text}?",
                    "Number of clicks for ad {ad} on {date_text}?"],
         sql="SELECT clicks FROM agg_ad_daily WHERE ad_id = {ad} AND event_date = '{date}'"),
    dict(key="E3", tier="easy", needs=["brand", "date"], tables=["agg_brand_daily"],
         questions=["How many impressions did brand {brand} have on {date_text}?",
                    "How many times were brand {brand}'s ads shown on {date_text}?"],
         sql="SELECT impressions FROM agg_brand_daily WHERE brand_id = {brand} AND event_date = '{date}'"),
    dict(key="E4", tier="easy", needs=["date"], tables=["agg_category_daily"],
         questions=["Which product category got the most clicks on {date_text}, and how many?",
                    "Top category by clicks on {date_text}?"],
         sql="SELECT category_id, clicks FROM agg_category_daily WHERE event_date = '{date}' "
             "ORDER BY clicks DESC LIMIT 1"),
    dict(key="E5", tier="easy", needs=["campaign"], tables=["dim_campaign"],
         questions=["Which advertiser runs campaign {campaign}?",
                    "Who is the advertiser behind campaign {campaign}?"],
         sql="SELECT advertiser_id FROM dim_campaign WHERE campaign_id = {campaign}"),
    dict(key="E6", tier="easy", needs=["campaign_multi_ad"], tables=["dim_campaign"],
         questions=["How many ads does campaign {campaign_multi_ad} have?",
                    "Number of ads in campaign {campaign_multi_ad}?"],
         sql="SELECT num_ads FROM dim_campaign WHERE campaign_id = {campaign_multi_ad}"),
    dict(key="E7", tier="easy", needs=["ad"], tables=["dim_ad"],
         questions=["What is the item price for ad {ad}?",
                    "How much does the product in ad {ad} cost?"],
         sql="SELECT price FROM dim_ad WHERE ad_id = {ad}"),
    dict(key="E8", tier="easy", needs=["advertiser", "date"], tables=["agg_advertiser_daily"],
         questions=["What was the estimated value for advertiser {advertiser} on {date_text}?",
                    "Estimated value (clicks x price) for advertiser {advertiser} on {date_text}?"],
         sql="SELECT est_value FROM agg_advertiser_daily WHERE advertiser_id = {advertiser} AND event_date = '{date}'"),
    dict(key="E9", tier="easy", needs=["date"], tables=["agg_placement_daily"],
         questions=["Which ad placement had the higher CTR on {date_text}?",
                    "On {date_text}, which placement had the best click-through rate?"],
         sql="SELECT placement_id, ctr FROM agg_placement_daily WHERE event_date = '{date}' "
             "ORDER BY ctr DESC LIMIT 1"),
    dict(key="E10", tier="easy", needs=["advertiser"], tables=["dim_advertiser"],
         questions=["How many campaigns does advertiser {advertiser} run?",
                    "Number of campaigns for advertiser {advertiser}?"],
         sql="SELECT num_campaigns FROM dim_advertiser WHERE advertiser_id = {advertiser}"),

    # ---------------- MEDIUM: tables must be joined ----------------
    dict(key="M1", tier="medium", needs=["advertiser_category"], tables=["agg_ad_daily", "dim_ad"],
         questions=["How many clicks did advertiser {advertiser}'s ads in category {category} get yesterday?",
                    "Yesterday's clicks for advertiser {advertiser}, only ads in category {category}?"],
         sql="SELECT SUM(d.clicks) AS clicks FROM agg_ad_daily d JOIN dim_ad a ON a.ad_id = d.ad_id "
             "WHERE a.advertiser_id = {advertiser} AND a.category_id = {category} AND d.event_date = '2017-05-12'"),
    dict(key="M2", tier="medium", needs=["campaign", "date"], tables=["fact_ad_events", "dim_user"],
         questions=["What was the CTR among heavy shoppers (shopping depth 3) for campaign {campaign} on {date_text}?",
                    "For campaign {campaign} on {date_text}, what CTR did heavy shoppers have?"],
         sql="SELECT SUM(e.is_click) / COUNT(*) AS ctr FROM fact_ad_events e JOIN dim_user u ON u.user_id = e.user_id "
             "WHERE e.campaign_id = {campaign} AND u.shopping_depth = 3 AND e.event_date = '{date}'"),
    dict(key="M3", tier="medium", needs=["brand"], tables=["fact_ad_events", "dim_user"],
         questions=["How many clicks did brand {brand} get from high-spending users (spending level 3) from 6 to 12 May?",
                    "Brand {brand}: clicks from users with the highest spending level, 6-12 May?"],
         sql="SELECT SUM(e.is_click) AS clicks FROM fact_ad_events e JOIN dim_user u ON u.user_id = e.user_id "
             "WHERE e.brand_id = {brand} AND u.spending_level = 3 AND e.event_date <= '2017-05-12'"),
    dict(key="M4", tier="medium", needs=["advertiser"], tables=["agg_ad_daily", "dim_ad"],
         questions=["Break down advertiser {advertiser}'s estimated value yesterday by product category.",
                    "Estimated value per category for advertiser {advertiser} yesterday?"],
         sql="SELECT a.category_id, SUM(d.est_value) AS est_value FROM agg_ad_daily d JOIN dim_ad a ON a.ad_id = d.ad_id "
             "WHERE a.advertiser_id = {advertiser} AND d.event_date = '2017-05-12' "
             "GROUP BY a.category_id ORDER BY a.category_id"),
    dict(key="M5", tier="medium", needs=["category_top_brand"], tables=["agg_ad_daily", "dim_ad"],
         questions=["Which brand in category {category_top_brand} had the most clicks yesterday?",
                    "Top brand by clicks yesterday within category {category_top_brand}?"],
         sql="SELECT a.brand_id, SUM(d.clicks) AS clicks FROM agg_ad_daily d JOIN dim_ad a ON a.ad_id = d.ad_id "
             "WHERE a.category_id = {category_top_brand} AND a.brand_id IS NOT NULL AND d.event_date = '2017-05-12' "
             "GROUP BY a.brand_id ORDER BY clicks DESC LIMIT 1"),
    dict(key="M6", tier="medium", needs=["advertiser", "date"], tables=["fact_ad_events", "dim_user"],
         questions=["How many clicks did advertiser {advertiser} get from users in city level 1 on {date_text}?",
                    "Clicks for advertiser {advertiser} from city-level-1 users on {date_text}?"],
         sql="SELECT SUM(e.is_click) AS clicks FROM fact_ad_events e JOIN dim_user u ON u.user_id = e.user_id "
             "WHERE e.advertiser_id = {advertiser} AND u.city_level = 1 AND e.event_date = '{date}'"),
    dict(key="M7", tier="medium", needs=["campaign_top_day"], tables=["agg_campaign_daily", "dim_date"],
         questions=["On which day of the week did campaign {campaign_top_day} get the most clicks (6-12 May)?",
                    "Campaign {campaign_top_day}'s best weekday for clicks between 6 and 12 May?"],
         sql="SELECT d.weekday, c.clicks FROM agg_campaign_daily c JOIN dim_date d ON d.date = c.event_date "
             "WHERE c.campaign_id = {campaign_top_day} ORDER BY c.clicks DESC LIMIT 1"),
    dict(key="M8", tier="medium", needs=["campaign_top_ad"], tables=["agg_ad_daily", "dim_ad"],
         questions=["Which ad in campaign {campaign_top_ad} got the most clicks yesterday, and what is its price?",
                    "Campaign {campaign_top_ad}: top ad by clicks yesterday and its item price?"],
         sql="SELECT d.ad_id, d.clicks, a.price FROM agg_ad_daily d JOIN dim_ad a ON a.ad_id = d.ad_id "
             "WHERE d.campaign_id = {campaign_top_ad} AND d.event_date = '2017-05-12' ORDER BY d.clicks DESC LIMIT 1"),
    dict(key="M9", tier="medium", needs=["campaign"], tables=["agg_campaign_daily", "dim_date"],
         questions=["How many clicks did campaign {campaign} get on weekend days (final data only)?",
                    "Total weekend clicks for campaign {campaign} (Saturdays and Sundays, final days)?"],
         sql="SELECT SUM(c.clicks) AS clicks FROM agg_campaign_daily c JOIN dim_date d ON d.date = c.event_date "
             "WHERE c.campaign_id = {campaign} AND d.weekday IN ('Saturday', 'Sunday')"),
    dict(key="M10", tier="medium", needs=["campaign", "date"], tables=["fact_ad_events", "dim_user"],
         questions=["How many unique male users saw campaign {campaign} on {date_text}?",
                    "Reach among men for campaign {campaign} on {date_text}?"],
         sql="SELECT COUNT(DISTINCT e.user_id) AS unique_users FROM fact_ad_events e "
             "JOIN dim_user u ON u.user_id = e.user_id "
             "WHERE e.campaign_id = {campaign} AND u.gender = 'male' AND e.event_date = '{date}'"),

    # ---------------- TRICKY: a look-alike table is easy to pick by mistake ----------------
    dict(key="T1", tier="tricky", needs=["campaign_suspicious"], tables=["agg_campaign_daily_valid"],
         trap="all-traffic table agg_campaign_daily",
         questions=["What was campaign {campaign_suspicious}'s CTR yesterday, excluding suspicious clicks?",
                    "Campaign {campaign_suspicious} CTR yesterday with bot traffic removed?"],
         sql="SELECT ctr FROM agg_campaign_daily_valid WHERE campaign_id = {campaign_suspicious} "
             "AND event_date = '2017-05-12'"),
    dict(key="T2", tier="tricky", needs=["campaign"], tables=["reach_campaign_total"],
         trap="adding up reach_campaign_daily counts people twice",
         questions=["How many unique people saw campaign {campaign} from 6 to 12 May?",
                    "Total reach (unique users) of campaign {campaign} over the final period?"],
         sql="SELECT unique_users FROM reach_campaign_total WHERE campaign_id = {campaign}"),
    dict(key="T3", tier="tricky", needs=["campaign_live"], tables=["live_reach_campaign_last6h"],
         trap="impressions instead of unique people; daily tables",
         questions=["How many unique people saw campaign {campaign_live} in the last 6 hours?",
                    "Campaign {campaign_live}: unique users reached in the last six hours?"],
         sql="SELECT unique_users FROM live_reach_campaign_last6h WHERE campaign_id = {campaign_live}"),
    dict(key="T4", tier="tricky", needs=["campaign_live"], tables=["live_campaign_last6h"],
         trap="daily final tables do not have today",
         questions=["How many clicks has campaign {campaign_live} had in the last 6 hours?",
                    "Clicks for campaign {campaign_live} right now (last six hours)?"],
         sql="SELECT clicks FROM live_campaign_last6h WHERE campaign_id = {campaign_live}"),
    dict(key="T5", tier="tricky", needs=["campaign_today"], tables=["agg_campaign_hourly"],
         trap="daily tables stop at yesterday; live tables only cover 6 hours",
         questions=["How many clicks has campaign {campaign_today} had today so far?",
                    "Today's clicks so far for campaign {campaign_today}?"],
         sql="SELECT SUM(clicks) AS clicks FROM agg_campaign_hourly WHERE campaign_id = {campaign_today} "
             "AND event_hour >= '2017-05-13'"),
    dict(key="T6", tier="tricky", needs=["campaign"], tables=["agg_campaign_weekly"],
         trap="the week of 8 May only has 5 final days",
         questions=["How many clicks did campaign {campaign} get in the week starting Monday 8 May?",
                    "Weekly clicks for campaign {campaign}, week of 8 May?"],
         sql="SELECT clicks, days_in_week FROM agg_campaign_weekly WHERE campaign_id = {campaign} "
             "AND week_start = '2017-05-08'"),
    dict(key="T7", tier="tricky", needs=["brand"], tables=["reach_brand_daily"],
         trap="impressions (agg_brand_daily) instead of unique people",
         questions=["How many unique people saw brand {brand}'s ads yesterday?",
                    "Brand {brand}: number of distinct users reached yesterday?"],
         sql="SELECT unique_users FROM reach_brand_daily WHERE brand_id = {brand} AND event_date = '2017-05-12'"),
    dict(key="T8", tier="tricky", needs=["campaign", "date"], tables=["agg_campaign_daily_by_audience"],
         trap="the audience table has several rows per gender (one per age level)",
         questions=["What was the CTR for campaign {campaign} on {date_text}, split by gender?",
                    "Campaign {campaign} CTR by gender on {date_text}?"],
         sql="SELECT gender, SUM(clicks) / SUM(impressions) AS ctr FROM agg_campaign_daily_by_audience "
             "WHERE campaign_id = {campaign} AND event_date = '{date}' GROUP BY gender ORDER BY gender"),
    dict(key="T9", tier="tricky", needs=["campaign_hour_suspicious"], tables=["agg_campaign_hourly_valid"],
         trap="all-traffic hourly table; daily valid table",
         questions=["How many valid clicks (suspicious traffic removed) did campaign {campaign} get at {hour_text}?",
                    "Campaign {campaign}: clicks at {hour_text} after removing bot traffic?"],
         sql="SELECT clicks FROM agg_campaign_hourly_valid WHERE campaign_id = {campaign} "
             "AND event_hour = '{hour}'"),
    dict(key="T10", tier="tricky", needs=["campaign"], tables=["reach_campaign_total"],
         trap="needs impressions per unique person, not per day",
         questions=["On average, how many times did each person see campaign {campaign} from 6 to 12 May?",
                    "Average frequency per user for campaign {campaign} over the final period?"],
         sql="SELECT avg_frequency FROM reach_campaign_total WHERE campaign_id = {campaign}"),
]

# Follow-up conversations: 3 turns, the later turns only make sense with the earlier ones (memory test)
CONVERSATION_TEMPLATES = [
    dict(key="C1", needs=["campaign"], turns=[
        ("What was campaign {campaign}'s CTR yesterday?", ["agg_campaign_daily"],
         "SELECT ctr FROM agg_campaign_daily WHERE campaign_id = {campaign} AND event_date = '2017-05-12'"),
        ("Now split that by age level.", ["agg_campaign_daily_by_audience"],
         "SELECT age_level, SUM(clicks) / SUM(impressions) AS ctr FROM agg_campaign_daily_by_audience "
         "WHERE campaign_id = {campaign} AND event_date = '2017-05-12' GROUP BY age_level ORDER BY age_level"),
        ("And what was the overall CTR the day before?", ["agg_campaign_daily"],
         "SELECT ctr FROM agg_campaign_daily WHERE campaign_id = {campaign} AND event_date = '2017-05-11'"),
    ]),
    dict(key="C2", needs=["brand"], turns=[
        ("How many clicks did brand {brand} get yesterday?", ["agg_brand_daily"],
         "SELECT clicks FROM agg_brand_daily WHERE brand_id = {brand} AND event_date = '2017-05-12'"),
        ("How many unique people saw it?", ["reach_brand_daily"],
         "SELECT unique_users FROM reach_brand_daily WHERE brand_id = {brand} AND event_date = '2017-05-12'"),
        ("How many unique people saw it the day before?", ["reach_brand_daily"],
         "SELECT unique_users FROM reach_brand_daily WHERE brand_id = {brand} AND event_date = '2017-05-11'"),
    ]),
    dict(key="C3", needs=["campaign_live"], turns=[
        ("How many clicks has campaign {campaign_live} had in the last 6 hours?", ["live_campaign_last6h"],
         "SELECT clicks FROM live_campaign_last6h WHERE campaign_id = {campaign_live}"),
        ("How many different people clicked?", ["live_reach_campaign_last6h"],
         "SELECT unique_clickers FROM live_reach_campaign_last6h WHERE campaign_id = {campaign_live}"),
        ("Which advertiser runs this campaign?", ["dim_campaign"],
         "SELECT advertiser_id FROM dim_campaign WHERE campaign_id = {campaign_live}"),
    ]),
    dict(key="C4", needs=["campaign_suspicious"], turns=[
        ("How many clicks did campaign {campaign_suspicious} get from 6 to 12 May?", ["agg_campaign_daily"],
         "SELECT SUM(clicks) AS clicks FROM agg_campaign_daily WHERE campaign_id = {campaign_suspicious}"),
        ("How many of those are left after removing suspicious clicks?", ["agg_campaign_daily_valid"],
         "SELECT SUM(clicks) AS clicks FROM agg_campaign_daily_valid WHERE campaign_id = {campaign_suspicious}"),
        ("Break the cleaned clicks down by day.", ["agg_campaign_daily_valid"],
         "SELECT event_date, clicks FROM agg_campaign_daily_valid WHERE campaign_id = {campaign_suspicious} "
         "ORDER BY event_date"),
    ]),
]


# ---------------------------------------------------------------------
# 3. Picking values
# ---------------------------------------------------------------------
def date_text(date):
    return "yesterday" if date == YESTERDAY else f"{int(date[-2:])} May 2017"


class Picker:
    """Hands out random IDs from the pools. Every ID is handed out only once."""

    def __init__(self, con, rng):
        self.con, self.rng = con, rng
        self.pools = {name: [r[0] for r in con.execute(sql + " ORDER BY 1").fetchall()] for name, sql in POOLS.items()}
        self.pairs = {name: con.execute(sql + " ORDER BY 1, 2").fetchall() for name, sql in PAIR_POOLS.items()}
        self.used = set()

    def one(self, pool):
        while True:
            value = self.rng.choice(self.pools[pool])
            if value not in self.used:
                self.used.add(value)
                return value

    def pair(self, pool):
        while True:
            a, b = self.rng.choice(self.pairs[pool])
            if a not in self.used:
                self.used.add(a)
                return a, b

    def values(self, needs):
        v = {}
        for need in needs:
            if need == "date":
                v["date"] = self.rng.choice(FINAL_DATES)
                v["date_text"] = date_text(v["date"])
            elif need == "advertiser_category":
                v["advertiser"], v["category"] = self.pair(need)
            elif need == "campaign_hour_suspicious":
                v["campaign"], hour = self.pair(need)
                v["hour"] = hour.strftime("%Y-%m-%d %H:%M:%S")
                v["hour_text"] = f"{hour.hour}:00-{hour.hour}:59 on {hour.day} May 2017"
            else:
                v[need] = self.one(need)
        return v


# ---------------------------------------------------------------------
# 4. Build everything
# ---------------------------------------------------------------------
def split_labels(n, n_practice, rng):
    labels = ["practice"] * n_practice + ["test"] * (n - n_practice)
    rng.shuffle(labels)
    return labels


def make_benchmark():
    if FROZEN.exists():
        raise SystemExit("The benchmark is FROZEN (benchmark/FROZEN.txt). Do not regenerate it.")

    rng = random.Random(SEED)
    con = duckdb.connect(str(DB_PATH), read_only=True)
    picker = Picker(con, rng)
    GOLD.mkdir(exist_ok=True)
    for old in GOLD.glob("*.sql"):
        old.unlink()

    # 120 questions: 40 per level, 4 per template; per level ~13 practice / ~27 test
    questions = []
    practice_per_tier = {"easy": 13, "medium": 13, "tricky": 14}   # 40 practice in total
    for tier in ["easy", "medium", "tricky"]:
        tier_questions = []
        for t in [t for t in TEMPLATES if t["tier"] == tier]:
            for i in range(4):
                v = picker.values(t["needs"])
                tier_questions.append({
                    "tier": tier,
                    "template": t["key"],
                    "question": t["questions"][i % 2].format(**v).replace("on yesterday", "yesterday"),
                    "sql": t["sql"].format(**v),
                    "gold_tables": t["tables"],
                    "trap": t.get("trap", ""),
                    "values": {k: val for k, val in v.items() if not k.endswith("_text")},
                })
        for q, label in zip(tier_questions, split_labels(40, practice_per_tier[tier], rng)):
            q["split"] = label
        questions += tier_questions

    with open(BENCH / "questions.jsonl", "w") as f:
        for n, q in enumerate(questions, start=1):
            qid = f"q{n:03d}"
            (GOLD / f"{qid}.sql").write_text(q.pop("sql") + "\n")
            f.write(json.dumps({"id": qid, **q, "gold_sql": f"gold/{qid}.sql"}) + "\n")

    # 20 conversations: 5 per template; 5 practice / 15 test
    conversations = []
    for t in CONVERSATION_TEMPLATES:
        for _ in range(5):
            v = picker.values(t["needs"])
            conversations.append({"template": t["key"], "turns": [
                {"question": q.format(**v), "sql": sql.format(**v), "gold_tables": tables}
                for q, tables, sql in t["turns"]]})
    labels = split_labels(20, 5, rng)

    with open(BENCH / "conversations.jsonl", "w") as f:
        for n, (c, label) in enumerate(zip(conversations, labels), start=1):
            cid = f"c{n:02d}"
            for k, turn in enumerate(c["turns"], start=1):
                (GOLD / f"{cid}_t{k}.sql").write_text(turn.pop("sql") + "\n")
                turn["gold_sql"] = f"gold/{cid}_t{k}.sql"
            f.write(json.dumps({"id": cid, "split": label, **c}) + "\n")

    con.close()
    print(f"Wrote {len(questions)} questions and {len(conversations)} conversations to {BENCH}")


if __name__ == "__main__":
    make_benchmark()
