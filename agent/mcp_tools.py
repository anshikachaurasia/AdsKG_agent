"""Connect to the MCP server and turn its tools into LangChain tools the agent can call.

The agent does NOT import the data code directly: it asks the MCP server "what tools do you have?"
and uses whatever comes back - exactly like any other MCP app would.

How: the MCP client needs an async event loop. We run one in a background thread, so the rest
of the agent can stay simple, normal (non-async) Python.
"""
import asyncio
import os
import threading
from pathlib import Path

from answer_checks import fit_rows
from fastmcp import Client
from fastmcp.client.transports import PythonStdioTransport
from langchain_core.tools import StructuredTool

SERVER = Path(__file__).resolve().parent.parent / "mcp_server" / "server.py"


class MCPConnection:
    """One long-lived connection to the MCP server (started once, used for every question)."""

    def __init__(self, server=SERVER):
        self.loop = asyncio.new_event_loop()
        threading.Thread(target=self.loop.run_forever, daemon=True).start()
        # the server starts with a clean environment; pass on which Qdrant copy to use (parallel runs, M9)
        env = {"QDRANT_PATH": os.environ["QDRANT_PATH"]} if "QDRANT_PATH" in os.environ else None
        self.client = Client(PythonStdioTransport(server, env=env))
        self._wait(self.client.__aenter__())          # starts the server program

    def _wait(self, coroutine):
        """Run an async call on the background loop and wait for its result."""
        return asyncio.run_coroutine_threadsafe(coroutine, self.loop).result()

    def list_tools(self):
        return self._wait(self.client.list_tools())

    def call(self, name, args):
        """Call one MCP tool. Returns text for the AI (errors come back as text too, so it can fix them)."""
        result = self._wait(self.client.call_tool(name, args, raise_on_error=False))
        if result.is_error:
            return fit_rows(result.content[0].text)
        return fit_rows(result.data)   # long results lose rows, not their JSON shape

    def close(self):
        self._wait(self.client.__aexit__(None, None, None))
        self.loop.call_soon_threadsafe(self.loop.stop)


def langchain_tools(connection):
    """One LangChain tool per MCP tool, with the name, description and inputs the server gives."""
    tools = []
    for t in connection.list_tools():
        tools.append(StructuredTool(
            name=t.name,
            description=t.description,
            args_schema=t.input_schema,     # the JSON schema of the inputs, straight from MCP
            func=lambda _name=t.name, **kwargs: connection.call(_name, kwargs),
        ))
    return tools
