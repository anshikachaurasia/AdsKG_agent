"""M10: a small chat UI for the final version (E + example memory).

Ask a question about the ads data; follow-ups work ("now split that by gender"). Under each answer you can open
the SQL that ran, its result, the tables used and the tool calls the agent made.

Run from the project folder (Neo4j must be running):
    .venv/bin/streamlit run app/streamlit_app.py
"""
import sys
import uuid
from pathlib import Path

import duckdb
import pandas as pd
import streamlit as st
import yaml

PROJECT = Path(__file__).resolve().parent.parent
sys.path += [str(PROJECT / "agent"), str(PROJECT / "mcp_server")]
from agent_graph import AgentE  # noqa: E402
from safety import run_sql, tables_in_sql  # noqa: E402

CONFIG = yaml.safe_load((PROJECT / "configs" / "E_memory.yaml").read_text())
EXAMPLES = [
    "What was campaign 143747's CTR yesterday, excluding suspicious clicks?",
    "How many unique people saw campaign 83237 in the last 6 hours?",
    "Which brand in category 4307 had the most clicks yesterday?",
]


@st.cache_resource
def get_agent():
    return AgentE(CONFIG)   # one MCP connection, shared by every chat


@st.cache_resource
def get_db():
    return duckdb.connect(str(PROJECT / "data" / "ads.duckdb"), read_only=True)


def show_details(out):
    with st.expander(f"How I got this: {out['steps']} steps, {len(out['tool_calls'])} tool calls, "
                     f"{out['tokens_in'] + out['tokens_out']:,} tokens"):
        if out["sql"]:
            st.code(out["sql"], language="sql")
            rows, columns, error = run_sql(get_db(), out["sql"])
            st.dataframe(pd.DataFrame(rows, columns=columns)) if not error else st.error(error)
            st.write("**Tables used:**", ", ".join(tables_in_sql(out["sql"])))
        st.write("**Tool calls:**")
        for call in out["tool_calls"]:
            st.text(call)


st.set_page_config(page_title="AdsKG Agent", page_icon="📊")
st.title("AdsKG Agent")
st.caption("Ask what happened in the ads data (Taobao, 6–13 May 2017; now = 13 May 23:59). "
           "IDs only, no names. Every answer shows the SQL it ran.")

if "thread" not in st.session_state:
    st.session_state.thread = str(uuid.uuid4())
    st.session_state.chat = []
with st.sidebar:
    st.write("**Try:**")
    for example in EXAMPLES:
        st.caption(example)
    if st.button("New conversation"):
        st.session_state.thread = str(uuid.uuid4())
        st.session_state.chat = []

for role, text, out in st.session_state.chat:
    with st.chat_message(role):
        st.markdown(text)
        if out:
            show_details(out)

question = st.chat_input("e.g. How many clicks did campaign 390070 get today so far?")
if question:
    st.session_state.chat.append(("user", question, None))
    with st.chat_message("user"):
        st.markdown(question)
    with st.chat_message("assistant"):
        with st.spinner("Searching tables, checking joins, running SQL..."):
            out = get_agent().ask(question, st.session_state.thread)
        st.markdown(out["answer"])
        show_details(out)
    st.session_state.chat.append(("assistant", out["answer"], out))
