#!/usr/bin/env python3
"""Check stage1_structure for articles"""
import json

with open('merged_20251211_134623_3149bf44.json', encoding='utf-8') as f:
    data = json.load(f)

stage1 = data.get('stage1_structure', {})
print("stage1_structure keys:", list(stage1.keys()))

articles = stage1.get('articles', [])
print(f"\nArticles in stage1: {len(articles)}")

# Find English articles
eng_articles = []
for a in articles:
    title = a.get('title', '').lower()
    text = a.get('full_text', a.get('content', '')).lower()
    if 'tiếng anh' in title or 'tiếng anh' in text:
        eng_articles.append(a)

print(f"Articles about 'tiếng anh': {len(eng_articles)}")
for a in eng_articles[:5]:
    print(f"  - {a.get('title')}")
