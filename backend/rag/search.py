import os
import requests
import zipfile
from qdrant_client import QdrantClient

QDRANT_PATH = os.path.join(os.path.dirname(__file__), "../local_qdrant")
COLLECTION_NAME = "college_kb"
TOP_K = 10

# Automatically restore Qdrant local database if missing/empty
db_parent = os.path.dirname(QDRANT_PATH)
zip_path = os.path.join(db_parent, "local_qdrant.zip")

if not os.path.exists(QDRANT_PATH) or not os.listdir(QDRANT_PATH):
    print("Qdrant local database not found or empty.")
    if os.path.exists(zip_path):
        print(f"Extracting {zip_path} to {QDRANT_PATH}...")
        try:
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                zip_ref.extractall(db_parent)
            print("Extraction complete!")
        except Exception as e:
            print(f"Error extracting Qdrant database zip: {e}")
    else:
        print(f"Warning: {zip_path} not found. Cannot restore Qdrant database.")

# Load once at module level (reused across calls)
print("Initializing Qdrant client...")
client = QdrantClient(path=QDRANT_PATH)

def get_embedding(text: str) -> list:
    """Get vector embedding using Hugging Face's serverless Inference API (uses 0MB of local RAM)."""
    api_url = "https://router.huggingface.co/hf-inference/models/sentence-transformers/all-MiniLM-L6-v2/pipeline/feature-extraction"
    hf_token = os.getenv("HF_TOKEN")
    
    headers = {}
    if hf_token:
        headers["Authorization"] = f"Bearer {hf_token}"
        
    try:
        response = requests.post(api_url, headers=headers, json={"inputs": text}, timeout=5)
        # Fallback to alternate URL if pipeline URL is busy
        if response.status_code != 200:
            api_url_alt = "https://router.huggingface.co/hf-inference/models/sentence-transformers/all-MiniLM-L6-v2"
            response = requests.post(api_url_alt, headers=headers, json={"inputs": text}, timeout=5)
            
        if response.status_code != 200:
            raise Exception(f"HF Inference API returned status {response.status_code}: {response.text}")
            
        result = response.json()
        if isinstance(result, list) and len(result) > 0 and isinstance(result[0], list):
            return result[0]
        return result
    except Exception as e:
        print(f"Embedding generation failed: {e}")
        return [0.0] * 384 # 384 dimensions for all-MiniLM-L6-v2


def search(query: str, top_k: int = TOP_K):
    # Embed the query using Hugging Face API
    query_vector = get_embedding(query)

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