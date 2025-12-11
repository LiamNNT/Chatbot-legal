#!/usr/bin/env python3
"""Check merged JSON for English articles"""
import json

with open('merged_20251211_134623_3149bf44.json', encoding='utf-8') as f:
    data = json.load(f)

print(f"Keys: {data.keys()}")
print(f"Total articles: {len(data.get('articles', []))}")

# Find articles about tieng anh
articles = data.get('articles', [])
eng_articles = []
for a in articles:
    title = a.get('title', '').lower()
    text = a.get('full_text', '').lower()
    if 'tiếng anh' in title or 'tiếng anh' in text:
        eng_articles.append(a)

print(f"\nArticles about 'tiếng anh': {len(eng_articles)}")
for a in eng_articles[:5]:
    print(f"  - {a.get('title')}")
