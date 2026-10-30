"""M6 done-test: start the MCP server like an AI app would, call every tool, and try to break the safety rules.

Run from the project folder (Neo4j must be running):
    .venv/bin/python mcp_server/check_mcp.py
"""
import asyncio
from pathlib import Path

from fastmcp import Client

SERVER = Path(__file__).resolve().parent / "server.py"

TOOL_CALLS = [
    ("search_tables", {"question": "unique people who saw a campaign in the last 6 hours", "k": 3}),
    ("get_join_path", {"from_table": "dim_user", "to_table": "agg_campaign_daily"}),
    ("list_lookalikes", {"table": "agg_campaign_daily"}),
    ("describe_table", {"table": "reach_campaign_total"}),
    ("sample_rows", {"table": "dim_campaign", "n": 2}),
    ("run_sql", {"sql": "SELECT ctr FROM agg_campaign_daily WHERE campaign_id = 359520 AND event_date = '2017-05-12'"}),
]

# each of these must be refused
ATTACKS = [
    ("run_sql", {"sql": "DROP TABLE dim_ad"}),
    ("run_sql", {"sql": "DELETE FROM dim_ad"}),
    ("run_sql", {"sql": "SELECT 1; DROP TABLE dim_ad"}),
    ("run_sql", {"sql": "COPY dim_ad TO 'stolen.csv'"}),
    ("run_sql", {"sql": "INSERT INTO dim_ad VALUES (1, 1, 1, 1, 1, 1)"}),
    ("sample_rows", {"table": "dim_ad; DROP TABLE dim_ad"}),
    # reads of local files and of anything outside the 28 warehouse tables
    ("run_sql", {"sql": "SELECT content FROM read_text('.env')"}),
    ("run_sql", {"sql": "SELECT * FROM read_csv('/etc/passwd', header=false)"}),
    ("run_sql", {"sql": "SELECT * FROM glob('*')"}),
    ("run_sql", {"sql": "SELECT * FROM dim_ad WHERE ad_id IN (SELECT 1 FROM read_text('.env'))"}),
    ("run_sql", {"sql": "SELECT * FROM raw_sample LIMIT 1"}),
    ("run_sql", {"sql": "SET enable_external_access = true"}),
]


async def main():
    async with Client(SERVER) as client:
        tools = await client.list_tools()
        print(f"Server offers {len(tools)} tools: {[t.name for t in tools]}\n")

        ok = 0
        for name, args in TOOL_CALLS:
            result = await client.call_tool(name, args)
            print(f"OK  {name}({args})\n      -> {str(result.data)[:160]}")
            ok += 1

        blocked = 0
        print()
        for name, args in ATTACKS:
            result = await client.call_tool(name, args, raise_on_error=False)
            refused = result.is_error or bool((result.data or {}).get("error"))
            blocked += refused
            reason = result.content[0].text if result.is_error else result.data["error"]
            print(f"{'BLOCKED' if refused else 'NOT BLOCKED!'}  {name}({args})\n      -> {reason[:110]}")

    print(f"\nTools working: {ok}/{len(TOOL_CALLS)}   Attacks blocked: {blocked}/{len(ATTACKS)}")


if __name__ == "__main__":
    asyncio.run(main())
