import json
import os
import numpy as np
from sentence_transformers import SentenceTransformer
from qdrant_client import QdrantClient
from qdrant_client.models import VectorParams, Distance, PointStruct, ScalarQuantization, ScalarQuantizationConfig, ScalarType

INPUT_FILE = os.path.join(os.path.dirname(__file__), "../data/chunks.json")
QDRANT_PATH = os.path.join(os.path.dirname(__file__), "../local_qdrant")
COLLECTION_NAME = "college_kb"
EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
VECTOR_DIM = 384
BATCH_SIZE = 64
UPSERT_BATCH = 500

def build_index():
    print("Loading chunks...")
    with open(INPUT_FILE, "r", encoding="utf-8") as f:
        chunks = json.load(f)
    print(f"Total chunks: {len(chunks)}")

    print("Loading embedding model...")
    model = SentenceTransformer(EMBEDDING_MODEL)

    texts = [chunk["text"] for chunk in chunks]

    print("Generating embeddings (this will take 20-40 mins)...")
    embeddings = model.encode(
        texts,
        batch_size=BATCH_SIZE,
        show_progress_bar=True,
        convert_to_numpy=True
    )
    print("Embeddings done!")

    print("Connecting to Qdrant...")
    client = QdrantClient(path=QDRANT_PATH)

    # Delete collection if exists
    existing = [c.name for c in client.get_collections().collections]
    if COLLECTION_NAME in existing:
        print(f"Deleting existing collection: {COLLECTION_NAME}")
        client.delete_collection(COLLECTION_NAME)

    # Create fresh collection with on-disk index and INT8 scalar quantization to optimize memory usage (RAM < 20MB)
    client.create_collection(
        collection_name=COLLECTION_NAME,
        vectors_config=VectorParams(size=VECTOR_DIM, distance=Distance.COSINE, on_disk=True),
        quantization_config=ScalarQuantization(
            scalar=ScalarQuantizationConfig(
                type=ScalarType.INT8,
                always_ram=False,
            )
        )
    )
    print(f"Collection '{COLLECTION_NAME}' created")

    # Build points
    points = []
    for i, chunk in enumerate(chunks):
        points.append(PointStruct(
            id=chunk["id"],
            vector=embeddings[i].tolist(),
            payload={
                "url": chunk["url"],
                "title": chunk["title"],
                "chunk_index": chunk["chunk_index"],
                "text": chunk["text"]
            }
        ))

    # Upsert in batches
    print("Upserting vectors to Qdrant...")
    for i in range(0, len(points), UPSERT_BATCH):
        batch = points[i: i + UPSERT_BATCH]
        client.upsert(collection_name=COLLECTION_NAME, points=batch)
        print(f"  Upserted {min(i + UPSERT_BATCH, len(points))}/{len(points)}")

    print(f"Index built! Total vectors: {len(points)}")

if __name__ == "__main__":
    build_index()