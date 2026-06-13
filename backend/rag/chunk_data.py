import json
import os

INPUT_FILE = os.path.join(os.path.dirname(__file__), "../data/clean_pages.json")
OUTPUT_FILE = os.path.join(os.path.dirname(__file__), "../data/chunks.json")

CHUNK_SIZE = 300    # words
OVERLAP = 50        # words

def chunk_text(text, chunk_size=CHUNK_SIZE, overlap=OVERLAP):
    words = text.split()
    chunks = []
    start = 0
    while start < len(words):
        end = start + chunk_size
        chunk = " ".join(words[start:end])
        chunks.append(chunk)
        start += chunk_size - overlap
        if start >= len(words):
            break
    return chunks

def chunk_data():
    print("Loading clean pages...")
    with open(INPUT_FILE, "r", encoding="utf-8") as f:
        clean_pages = json.load(f)

    print(f"Total clean pages: {len(clean_pages)}")

    all_chunks = []
    chunk_id = 0

    for page in clean_pages:
        url = page.get("url", "")
        title = page.get("title", "")
        content = page.get("content", "")

        if not content:
            continue

        chunks = chunk_text(content)

        for i, chunk in enumerate(chunks):
            all_chunks.append({
                "id": chunk_id,
                "url": url,
                "title": title,
                "chunk_index": i,
                "text": chunk
            })
            chunk_id += 1

    print(f"Total chunks created: {len(all_chunks)}")

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(all_chunks, f, ensure_ascii=False, indent=2)

    print(f"Saved to {OUTPUT_FILE}")

if __name__ == "__main__":
    chunk_data()