#!/usr/bin/env python3
"""Check merged JSON structure"""
import json

with open('merged_20251211_134623_3149bf44.json', encoding='utf-8') as f:
    data = json.load(f)

print("Top-level keys:", list(data.keys()))
print()

stage2 = data.get('stage2_semantic', {})
print("stage2_semantic keys:", list(stage2.keys()))
print()

# Check for articles in different places
for key in stage2.keys():
    val = stage2.get(key)
    if isinstance(val, list):
        print(f"  {key}: list of {len(val)} items")
        if val and isinstance(val[0], dict):
            print(f"    First item keys: {list(val[0].keys())}")
    elif isinstance(val, dict):
        print(f"  {key}: dict with keys {list(val.keys())[:5]}")
    else:
        print(f"  {key}: {type(val).__name__}")

# Look for tieng anh anywhere
print("\n--- Searching for 'tiếng anh' ---")
def search_dict(d, path=""):
    if isinstance(d, dict):
        for k, v in d.items():
            search_dict(v, f"{path}.{k}")
    elif isinstance(d, list):
        for i, item in enumerate(d):
            search_dict(item, f"{path}[{i}]")
    elif isinstance(d, str):
        if 'tiếng anh' in d.lower():
            print(f"Found at {path}: {d[:80]}...")

search_dict(stage2)
