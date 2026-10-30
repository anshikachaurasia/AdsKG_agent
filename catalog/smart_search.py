"""M8: version C's "smart search" = three advanced-RAG tricks on top of B's basic search.
Each can be switched on/off (an "ablation" test shows which ones actually help):

  1. rewrite: the AI first rewrites the question as a description of the table it needs
              ("unique people last 6 hours" -> "live table, last 6 hours, unique users per campaign")
  2. hybrid:  search by meaning (dense) AND by keywords (BM25), merged with Reciprocal Rank Fusion (RRF):
              a table ranked high by either search ends up high
  3. rerank:  a cross-encoder (bge-reranker) reads the question and each of the top 20 cards TOGETHER
              and re-scores them - slower but more careful than vector similarity

Run from the project folder:
    .venv/bin/python catalog/smart_search.py "How many unique people saw campaign 83237 in the last 6 hours?"
"""
import sys
from pathlib import Path

from qdrant_client import QdrantClient, models

PROJECT = Path(__file__).resolve().parent.parent
sys.path += [str(PROJECT / "catalog"), str(PROJECT / "agent")]
from load_qdrant import QDRANT_PATH, collection_name, embed, embed_sparse  # noqa: E402

RERANK_MODEL = "BAAI/bge-reranker-base"
CANDIDATES = 20

REWRITE_PROMPT = """Rewrite this question about ads data as a short description of the database TABLE that would
answer it. Mention: the entity (ad, campaign, advertiser, brand, category, placement, user), the measure
(impressions, clicks, CTR, unique users/reach, estimated value), the time grain (hourly, daily, weekly, whole period),
the freshness (live last 6 hours, today so far, or final up to yesterday), and the traffic (all, or valid with
suspicious clicks removed) - only what the question implies. Reply with one sentence only.
Now = 2017-05-13 23:59; yesterday = 2017-05-12.

Question: {question}"""

_reranker = None


def rewrite_question(question, model):
    from llm import ask
    return ask(model, "You help find the right table in a data catalog.", REWRITE_PROMPT.format(question=question), "low")


def candidates(text, catalog_size, hybrid, client):
    """Top CANDIDATES tables: by meaning only, or hybrid (meaning + keywords, merged with RRF)."""
    name = collection_name(catalog_size)
    dense = embed([text])[0]
    if not hybrid:
        hits = client.query_points(name, query=dense, using="dense", limit=CANDIDATES).points
    else:
        sparse = embed_sparse([text])[0]
        hits = client.query_points(
            name,
            prefetch=[models.Prefetch(query=dense, using="dense", limit=CANDIDATES),
                      models.Prefetch(query=sparse, using="bm25", limit=CANDIDATES)],
            query=models.FusionQuery(fusion=models.Fusion.RRF),
            limit=CANDIDATES,
        ).points
    return [(h.payload["table"], h.payload["search_text"]) for h in hits]


def rerank(question, found):
    global _reranker
    if _reranker is None:
        from fastembed.rerank.cross_encoder import TextCrossEncoder
        _reranker = TextCrossEncoder(RERANK_MODEL)
    scores = list(_reranker.rerank(question, [text for _, text in found]))
    return [f for _, f in sorted(zip(scores, found), key=lambda pair: -pair[0])]


def smart_search(question, k=5, catalog_size=28, use_rewrite=True, use_hybrid=True, use_rerank=True,
                 model="gpt-5-mini", client=None):
    """Returns (top k table names, usage of the rewrite call)."""
    usage = {"tokens_in": 0, "tokens_out": 0}
    query_text = question
    if use_rewrite:
        rewritten, usage = rewrite_question(question, model)
        query_text = f"{question} {rewritten}"

    own_client = client is None
    client = client or QdrantClient(path=str(QDRANT_PATH))
    found = candidates(query_text, catalog_size, use_hybrid, client)
    if own_client:
        client.close()

    if use_rerank:
        found = rerank(query_text, found)
    return [table for table, _ in found[:k]], usage


if __name__ == "__main__":
    q = " ".join(sys.argv[1:]) or "What was campaign 143747's CTR yesterday, excluding suspicious clicks?"
    print(q)
    for flags in [(False, False, False), (True, False, False), (False, True, False), (False, False, True), (True, True, True)]:
        tables, _ = smart_search(q, *[], use_rewrite=flags[0], use_hybrid=flags[1], use_rerank=flags[2])
        print(f"rewrite={flags[0]!s:5} hybrid={flags[1]!s:5} rerank={flags[2]!s:5} -> {tables}")
