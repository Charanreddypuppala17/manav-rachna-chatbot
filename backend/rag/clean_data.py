import json
import re
import os

INPUT_FILE = os.path.join(os.path.dirname(__file__), "../data/raw_pages.json")
OUTPUT_FILE = os.path.join(os.path.dirname(__file__), "../data/clean_pages.json")

def clean_text(text):
    if not text:
        return ""
    text = re.sub(r'!\[.*?\]\(.*?\)', ' ', text)
    text = re.sub(r'\[([^\]]+)\]\([^\)]+\)', r'\1', text)
    text = re.sub(r'[#*`>|\\~^]+', ' ', text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text

def clean_data():
    print("Loading raw pages...")
    with open(INPUT_FILE, "r", encoding="utf-8") as f:
        raw_pages = json.load(f)

    print(f"Total raw pages: {len(raw_pages)}")

    cleaned = []
    seen_urls = set()
    skipped = 0

    for page in raw_pages:
        url = page.get("url", "")
        content = clean_text(page.get("markdown") or page.get("content") or "")

        # Skip if too short
        if len(content) < 100:
            skipped += 1
            continue

        # Skip duplicate URLs only
        if url in seen_urls:
            skipped += 1
            continue

        seen_urls.add(url)
        cleaned.append({
            "url": url,
            "title": "",
            "content": content
        })

    print(f"Cleaned pages: {len(cleaned)}")
    print(f"Skipped: {skipped}")

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(cleaned, f, ensure_ascii=False, indent=2)

    print(f"Saved to {OUTPUT_FILE}")

if __name__ == "__main__":
    clean_data()