"""M2 (+M8): put the table cards into Qdrant so they can be searched.

Each card gets TWO vectors:
  - "dense": meaning (FastEmbed bge-small, 384 numbers) - used by every search
  - "bm25":  keywords (a sparse vector: which words appear, weighted) - used by version C's hybrid search
Qdrant runs in "local mode": it is just a folder (data/qdrant), no server or Docker needed.

One collection per catalog size: table_cards (our 28 tables), table_cards_100, table_cards_250 (M8).

Run from the project folder:
    .venv/bin/python catalog/load_qdrant.py
"""
import os
import sys
from pathlib import Path

from fastembed import SparseTextEmbedding, TextEmbedding
from qdrant_client import QdrantClient, models

PROJECT = Path(__file__).resolve().parent.parent
sys.path.append(str(PROJECT / "catalog"))
QDRANT_PATH = Path(os.environ.get("QDRANT_PATH", PROJECT / "data" / "qdrant"))   # M9: a copy per parallel run

COLLECTION = "table_cards"
MODEL_NAME = "BAAI/bge-small-en-v1.5"   # small, free, runs locally
SPARSE_MODEL_NAME = "Qdrant/bm25"

_models = {}


def get_model(kind="dense"):
    """Load each embedding model once (first time downloads it)."""
    if kind not in _models:
        _models[kind] = TextEmbedding(MODEL_NAME) if kind == "dense" else SparseTextEmbedding(SPARSE_MODEL_NAME)
    return _models[kind]


def embed(texts):
    return [vector.tolist() for vector in get_model("dense").embed(texts)]


def embed_sparse(texts):
    return [models.SparseVector(indices=v.indices.tolist(), values=v.values.tolist()) for v in get_model("sparse").embed(texts)]


def collection_name(catalog_size=28):
    return COLLECTION if catalog_size == 28 else f"{COLLECTION}_{catalog_size}"


def build_index(catalog_size=28, client=None):
    from distractors import load_catalog
    cards = list(load_catalog(catalog_size).values())
    texts = [c["search_text"] for c in cards]
    dense, sparse = embed(texts), embed_sparse(texts)

    own_client = client is None
    client = client or QdrantClient(path=str(QDRANT_PATH))
    name = collection_name(catalog_size)
    if client.collection_exists(name):
        client.delete_collection(name)
    client.create_collection(
        name,
        vectors_config={"dense": models.VectorParams(size=len(dense[0]), distance=models.Distance.COSINE)},
        sparse_vectors_config={"bm25": models.SparseVectorParams(modifier=models.Modifier.IDF)},
    )
    client.upsert(name, [
        models.PointStruct(id=i, vector={"dense": d, "bm25": s}, payload={"table": c["table"], "search_text": c["search_text"]})
        for i, (c, d, s) in enumerate(zip(cards, dense, sparse))
    ])
    print(f"Loaded {len(cards)} cards into Qdrant collection '{name}'")
    if own_client:
        client.close()


if __name__ == "__main__":
    client = QdrantClient(path=str(QDRANT_PATH))
    for size in [28, 100, 250]:
        build_index(size, client)
    client.close()
