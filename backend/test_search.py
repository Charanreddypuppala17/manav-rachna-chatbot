from rag.search import search

results = search('manoj kumar faculty')
for r in results:
    print(r['url'])
    print(r['text'][:200])
    print('---')