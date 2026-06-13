import os
import requests
import sqlite3
import zipfile
import numpy as np
from dotenv import load_dotenv

load_dotenv()

# Paths relative to search.py
RAG_DIR = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.dirname(RAG_DIR)
ZIP_PATH = os.path.join(BACKEND_DIR, "rag_data.zip")
VECTORS_PATH = os.path.join(BACKEND_DIR, "vectors.npy")
DB_PATH = os.path.join(BACKEND_DIR, "chunks.db")
TOP_K = 10

# Automatic database restore on startup
if not os.path.exists(VECTORS_PATH) or not os.path.exists(DB_PATH):
    print("NumPy vector DB or chunks DB not found. Restoring from zip...")
    if os.path.exists(ZIP_PATH):
        try:
            with zipfile.ZipFile(ZIP_PATH, 'r') as zip_ref:
                zip_ref.extractall(BACKEND_DIR)
            print("Restoration complete!")
        except Exception as e:
            print(f"Error extracting RAG database zip: {e}")
    else:
        print(f"Warning: {ZIP_PATH} not found. Cannot restore database.")

# Load vectors once at module level (exactly 36MB RAM)
vectors = None
if os.path.exists(VECTORS_PATH):
    print("Loading vectors into memory...")
    try:
        vectors = np.load(VECTORS_PATH)
        print(f"Loaded vectors with shape: {vectors.shape}")
    except Exception as e:
        print(f"Error loading vectors.npy: {e}")

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
    global vectors
    if vectors is None:
        print("Warning: Vector database is not loaded!")
        return []
        
    # Embed query
    query_vector = get_embedding(query)
    query_vector = np.array(query_vector, dtype=np.float32)
    
    # Compute cosine similarity using vectorized numpy
    # Cosine similarity = dot(A, B) / (norm(A) * norm(B))
    dot_products = np.dot(vectors, query_vector)
    vector_norms = np.linalg.norm(vectors, axis=1)
    query_norm = np.linalg.norm(query_vector)
    
    if query_norm == 0:
        return []
        
    # Prevent division by zero
    vector_norms[vector_norms == 0] = 1e-10
    
    similarities = dot_products / (vector_norms * query_norm)
    
    # Get top_k indices sorted descending
    top_indices = np.argsort(similarities)[::-1][:top_k]
    
    # Connect to SQLite metadata DB
    results = []
    if os.path.exists(DB_PATH):
        try:
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            for idx in top_indices:
                score = float(similarities[idx])
                # Query metadata by ID
                cursor.execute("SELECT url, title, text FROM chunks WHERE id = ?", (int(idx),))
                row = cursor.fetchone()
                if row:
                    results.append({
                        "score": round(score, 4),
                        "url": row[0],
                        "title": row[1],
                        "text": row[2]
                    })
            conn.close()
        except Exception as e:
            print(f"Error querying SQLite chunks metadata: {e}")
            
    return results

if __name__ == "__main__":
    query = input("Enter test query: ")
    results = search(query)
    for i, r in enumerate(results):
        print(f"\n--- Result {i+1} (score: {r['score']}) ---")
        print(f"URL: {r['url']}")
        print(f"Title: {r['title']}")
        print(f"Text: {r['text'][:200]}...")