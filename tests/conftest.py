"""Unit tests that need no data, no Neo4j, no Qdrant and no API key (they run on GitHub too).

Run from the project folder:
    .venv/bin/python -m pytest -q
"""
import sys
from pathlib import Path

PROJECT = Path(__file__).resolve().parent.parent
sys.path += [str(PROJECT / "agent"), str(PROJECT / "mcp_server"), str(PROJECT / "harness")]
