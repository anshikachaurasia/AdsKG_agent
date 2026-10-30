"""M2: search the table cards with a plain-English question (search by meaning).

This is the `search_tables` tool (M6) and version B's search. Version C's smart search is in smart_search.py.

Run from the project folder:
    .venv/bin/python catalog/search.py "How many unique people saw campaign 83237 yesterday?"
"""
import sys

from qdrant_client import QdrantClient

from load_qdrant import QDRANT_PATH, collection_name, embed


def search_tables(question, k=5, client=None, catalog_size=28):
    """Return the k most similar tables as (table, score) pairs. Higher score = more similar."""
    own_client = client is None
    if own_client:
        client = QdrantClient(path=str(QDRANT_PATH))
    query_vector = embed([question])[0]
    hits = client.query_points(collection_name(catalog_size), query=query_vector, using="dense", limit=k).points
    if own_client:
        client.close()
    return [(hit.payload["table"], round(hit.score, 3)) for hit in hits]


if __name__ == "__main__":
    question = " ".join(sys.argv[1:]) or "What was the CTR for campaign 359520 yesterday?"
    print(question)
    for table, score in search_tables(question):
        print(f"  {score:.3f}  {table}")
