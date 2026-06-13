import asyncio
import json
from urllib.parse import urlparse

from crawl4ai import AsyncWebCrawler


START_URL = "https://manavrachna.edu.in"
MAX_PAGES =5000


async def main():

    visited = set()
    queue = [START_URL]
    results = []

    async with AsyncWebCrawler() as crawler:

        while queue and len(visited) < MAX_PAGES:

            url = queue.pop(0)

            if url in visited:
                continue

            try:
                print(f"[{len(visited)+1}] Crawling: {url}")

                result = await crawler.arun(url=url)
                print("\nLINKS TYPE:", type(result.links))
                print(result.links)

                visited.add(url)

                results.append({
                    "url": url,
                    "markdown": result.markdown
                })

                if len(results) % 100 == 0:
                    with open(
                        "data/raw_pages.json",
                        "w",
                        encoding="utf-8"
                    ) as f:
                        json.dump(results, f, ensure_ascii=False, indent=2)

                    print(f"Saved {len(results)} pages")

                if hasattr(result, "links") and result.links:

                    internal_links = result.links.get("internal", [])

                    print(f"Found {len(internal_links)} internal links")

                    for link in internal_links:

                        href = link.get("href")

                        if not href:
                            continue

                        if href in visited:
                            continue

                        if href not in queue:
                            queue.append(href)

            except Exception as e:
                print("ERROR:", url, e)

    with open(
        "data/raw_pages.json",
        "w",
        encoding="utf-8"
    ) as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    print("\nDONE")
    print("Pages crawled:", len(results))


if __name__ == "__main__":
    asyncio.run(main())