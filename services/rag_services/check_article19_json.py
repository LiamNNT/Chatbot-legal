#!/usr/bin/env python3
import json

with open('data/extraction_results/full_extraction_20251205_151556.json', encoding='utf-8') as f:
    data = json.load(f)

articles = data.get('stage1_structure', {}).get('articles', [])
print(f'Total articles in JSON: {len(articles)}')

article_19 = [a for a in articles if a.get('number') == 19]
print(f'Article 19 found: {len(article_19) > 0}')

if article_19:
    print(f'Article 19 ID: {article_19[0].get("id")}')
    print(f'Article 19 Title: {article_19[0].get("title")}')
    print(f'Has clauses: {len(article_19[0].get("clauses", []))}')
else:
    print('Article 19 NOT in JSON - need to re-extract or index from Neo4j')
