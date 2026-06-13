import os
from sentence_transformers import SentenceTransformer
from qdrant_client import QdrantClient

QDRANT_PATH = os.path.join(os.path.dirname(__file__), "../local_qdrant")
COLLECTION_NAME = "college_kb"
EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
TOP_K = 10

# Load once at module level (reused across calls)
print("Loading embedding model for search...")
model = SentenceTransformer(EMBEDDING_MODEL)
client = QdrantClient(path=QDRANT_PATH)

def search(query: str, top_k: int = TOP_K):
    # Embed the query
    query_vector = model.encode(query, convert_to_numpy=True).tolist()

    # Search Qdrant
    try:
        results = client.query_points(
            collection_name=COLLECTION_NAME,
            query=query_vector,
            limit=top_k,
            with_payload=True
        ).points
    except Exception as e:
        print(f"Warning: Qdrant search failed (local database might be empty or uninitialized): {e}")
        return []

    # Format results
    formatted = []
    for r in results:
        formatted.append({
            "score": round(r.score, 4),
            "text": r.payload.get("text", ""),
            "url": r.payload.get("url", ""),
            "title": r.payload.get("title", "")
        })

    return formatted


# Quick test
if __name__ == "__main__":
    query = input("Enter test query: ")
    results = search(query)
    for i, r in enumerate(results):
        print(f"\n--- Result {i+1} (score: {r['score']}) ---")
        print(f"URL: {r['url']}")
        print(f"Title: {r['title']}")
        print(f"Text: {r['text'][:200]}...")