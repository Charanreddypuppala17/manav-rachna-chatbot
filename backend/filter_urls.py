import json

with open("data/raw_pages.json", "r", encoding="utf-8") as f:
    data = json.load(f)

print(f"Total before: {len(data)}")

filtered = [p for p in data if "manavrachna.edu.in" in p.get("url", "")]

print(f"Total after: {len(filtered)}")

with open("data/raw_pages.json", "w", encoding="utf-8") as f:
    json.dump(filtered, f, ensure_ascii=False, indent=2)

print("Done!")