"""Version E: a LangGraph ReAct agent that uses the MCP tools, retries, and remembers.

ReAct = REason + ACT, in a loop:
    agent (think, maybe call tools) -> tools (run them) -> agent (look at results) -> ... -> final answer

The graph:
    START -> agent --(tool calls?)--> tools -> agent ...
                   \\--(no tool calls)--> END

Agent rules (the "harness" around the agent):
  - at most 8 steps (agent turns) per question
  - at most 3 failed SQL runs per question
  - a token budget per question (a cost limit)
  When a limit is hit, the agent must answer from queries that already ran, or say it is not sure.
  The answer is graded on the last SQL that actually ran without an error, never on SQL it only wrote.

Memory:
  - chat memory (short-term): earlier turns of the same conversation are kept (LangGraph checkpointer),
    so "now split that by age" works. Only the last 6 user turns are sent to the AI.
  - example memory (long-term): similar questions answered correctly before are added to the prompt (memory.py).
"""
import json
import sys
from pathlib import Path
from typing import Annotated

from dotenv import load_dotenv
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage
from langchain_openai import ChatOpenAI
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode
from typing_extensions import TypedDict

sys.path.append(str(Path(__file__).resolve().parent))
load_dotenv(Path(__file__).resolve().parent.parent / ".env")   # OPENAI_API_KEY
from mcp_tools import MCPConnection, langchain_tools  # noqa: E402
from memory import recall  # noqa: E402

MAX_STEPS = 8
MAX_SQL_ERRORS = 3
MAX_TOKENS_IN = 60_000
KEEP_USER_TURNS = 6

SYSTEM_PROMPT = """You answer questions about an ads data warehouse (Taobao ads, May 2017) using tools.

Facts about time:
- "Now" is 2017-05-13 23:59 (China time). Today = 2017-05-13. Yesterday = 2017-05-12.
- The data covers 2017-05-06 to 2017-05-13.

Facts about the data:
- IDs are numbers. There are NO names for advertisers, campaigns, ads, brands, categories or placements.
- fact_ad_events has one row per impression (with user_id, ad, campaign, brand, category, click). It can answer
  anything the summary tables can't, by joining it to the lookup tables (e.g. dim_user for gender or age).

You have at most 8 steps, so work efficiently:
1. search_tables to find candidate tables (search at most twice).
2. Many tables look alike (hourly/daily/weekly, all vs valid traffic, impressions vs unique people,
   live vs final). Use list_lookalikes and describe_table to pick the one that matches the question.
3. If no single table has everything, JOIN tables: get_join_path shows how they connect. Don't keep searching
   for a ready-made table. sample_rows shows real values.
4. run_sql with ONE read-only DuckDB SELECT as soon as you have a plausible query. If it fails, read the error,
   fix the query and try again.

Final answer (when you are done):
- A short answer in plain words, with any caveats (incomplete day, partial week, estimate, ...).
- Then the exact final SQL in a ```sql code block. CTR is a fraction (clicks / impressions), not a percentage.
- If you cannot find a reliable answer, say "not sure" and explain why. Do not guess.
"""

FINISH_NOW = ("You have reached your limit for this question. Do not call tools. Give your final answer now, based "
              "ONLY on queries that already ran successfully. If none did, say \"not sure\".")


class State(TypedDict):
    messages: Annotated[list, add_messages]
    steps: int
    sql_errors: int
    tokens_in: int
    tokens_out: int


def recent_turns(messages, keep=KEEP_USER_TURNS):
    """Only the last `keep` user turns (cut at a question, so tool calls and results stay together)."""
    starts = [i for i, m in enumerate(messages) if isinstance(m, HumanMessage)]
    return messages[starts[-keep]:] if len(starts) > keep else messages


def count_sql_errors(messages):
    """How many run_sql calls failed in the latest batch of tool results."""
    errors = 0
    for m in reversed(messages):
        if not isinstance(m, ToolMessage):
            break
        if m.name == "run_sql":
            try:
                errors += bool(json.loads(m.content).get("error"))
            except json.JSONDecodeError:
                errors += 1
    return errors


def build_agent(config, connection):
    tools = langchain_tools(connection)
    llm = ChatOpenAI(model=config["model"], reasoning_effort=config.get("reasoning_effort"))
    llm_with_tools = llm.bind_tools(tools)

    def agent(state):
        messages = recent_turns(state["messages"])
        question = [m for m in messages if isinstance(m, HumanMessage)][-1].content
        system = SYSTEM_PROMPT
        if config.get("example_memory"):
            examples = recall(question)
            if examples:
                system += "\nSimilar questions answered correctly before:\n" + "\n".join(
                    f"Q: {e['question']}\nSQL: {e['sql']}" for e in examples)

        at_limit = (state["steps"] >= MAX_STEPS or state["sql_errors"] >= MAX_SQL_ERRORS
                    or state["tokens_in"] >= MAX_TOKENS_IN)
        if at_limit:
            response = llm.invoke([SystemMessage(system)] + messages + [HumanMessage(FINISH_NOW)])
        else:
            response = llm_with_tools.invoke([SystemMessage(system)] + messages)

        usage = response.usage_metadata or {}
        return {"messages": [response], "steps": state["steps"] + 1,
                "tokens_in": state["tokens_in"] + usage.get("input_tokens", 0),
                "tokens_out": state["tokens_out"] + usage.get("output_tokens", 0)}

    tool_node = ToolNode(tools)

    def run_tools(state):
        result = tool_node.invoke(state)
        all_messages = state["messages"] + result["messages"]
        return {"messages": result["messages"], "sql_errors": state["sql_errors"] + count_sql_errors(all_messages)}

    def next_step(state):
        last = state["messages"][-1]
        return "tools" if isinstance(last, AIMessage) and last.tool_calls else END

    graph = StateGraph(State)
    graph.add_node("agent", agent)
    graph.add_node("tools", run_tools)
    graph.add_edge(START, "agent")
    graph.add_conditional_edges("agent", next_step, {"tools": "tools", END: END})
    graph.add_edge("tools", "agent")
    return graph.compile(checkpointer=InMemorySaver())


def last_good_sql(messages):
    """The last run_sql query that actually ran without an error (the answer is graded on what really ran)."""
    results = {m.tool_call_id: m.content for m in messages if isinstance(m, ToolMessage) and m.name == "run_sql"}
    good = ""
    for m in messages:
        if isinstance(m, AIMessage):
            for call in m.tool_calls:
                if call["name"] == "run_sql" and call["id"] in results:
                    try:
                        if not json.loads(results[call["id"]]).get("error"):
                            good = call["args"]["sql"]
                    except json.JSONDecodeError:
                        pass
    return good


def tables_seen(messages):
    """Tables the agent looked at through the tools (for the 'needed tables shown' score)."""
    seen = []
    for m in messages:
        if not isinstance(m, ToolMessage):
            continue
        try:
            data = json.loads(m.content)
        except json.JSONDecodeError:
            continue
        items = data if isinstance(data, list) else [data]
        for item in items:
            if isinstance(item, dict):
                seen += [item["table"]] if "table" in item else []
                seen += item.get("path", [])
    return list(dict.fromkeys(seen))


class AgentE:
    """Keeps one MCP connection and one compiled agent for a whole run."""

    def __init__(self, config):
        self.config = config
        self.connection = MCPConnection()
        self.agent = build_agent(config, self.connection)

    def ask(self, question, thread_id):
        """Ask one question in a conversation thread. Returns the final answer and what happened."""
        run_config = {"configurable": {"thread_id": thread_id}, "recursion_limit": 4 * MAX_STEPS}
        before = len(self.agent.get_state(run_config).values.get("messages", []))
        state = self.agent.invoke({"messages": [HumanMessage(question)], "steps": 0, "sql_errors": 0,
                                   "tokens_in": 0, "tokens_out": 0}, run_config)
        new = state["messages"][before:]
        answer = new[-1].content
        not_sure = "not sure" in answer.lower()
        return {
            "answer": answer,
            "sql": "" if not_sure else last_good_sql(new),   # never grade SQL that was not actually run
            "steps": state["steps"],
            "sql_errors": state["sql_errors"],
            "tool_calls": [f"{c['name']}({json.dumps(c['args'])[:120]})" for m in new
                           if isinstance(m, AIMessage) for c in m.tool_calls],
            "tables_shown": tables_seen(new),
            "tokens_in": state["tokens_in"],
            "tokens_out": state["tokens_out"],
        }

    def close(self):
        self.connection.close()
