#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test Knowledge Graph với các câu hỏi thực tế
"""

import requests
import json
import sys

# Ensure UTF-8 encoding for output
sys.stdout.reconfigure(encoding='utf-8')

API_URL = "http://localhost:8001/api/v1/chat"

test_questions = [
    {
        "name": "Chuyển ngành",
        "query": "Sinh viên muốn chuyển ngành cần điều kiện gì?"
    },
    {
        "name": "ĐTBC chuyển ngành",
        "query": "ĐTBC bao nhiêu thì được chuyển ngành?"
    },
    {
        "name": "Năm nhất chuyển ngành",
        "query": "Năm nhất có được chuyển ngành không?"
    },
    {
        "name": "Điều kiện thi",
        "query": "Phải đi học bao nhiêu phần trăm mới được thi?"
    },
    {
        "name": "Điều 19",
        "query": "Điều 19 quy định gì?"
    }
]

print("=" * 80)
print("🧪 TEST KNOWLEDGE GRAPH - CÂU HỎI THỰC TẾ")
print("=" * 80)
print()

for i, test in enumerate(test_questions, 1):
    print(f"\n{'=' * 80}")
    print(f"TEST {i}: {test['name']}")
    print(f"Query: {test['query']}")
    print("=" * 80)
    
    try:
        # Send request
        response = requests.post(
            API_URL,
            json={
                "query": test['query'],
                "session_id": f"test_final_{i}"
            },
            headers={"Content-Type": "application/json; charset=utf-8"},
            timeout=60
        )
        
        result = response.json()
        
        # Print answer
        print("\n📝 ANSWER:")
        print("-" * 80)
        print(result.get("response", "No answer"))
        print("-" * 80)
        
        # Print metadata
        rag_context = result.get("rag_context", {})
        processing = result.get("processing_stats", {})
        
        print("\n🔍 METADATA:")
        print(f"   ✓ Used KG: {rag_context.get('use_knowledge_graph', False)}")
        print(f"   ✓ Complexity: {processing.get('plan_complexity', 'unknown')}")
        print(f"   ✓ Documents: {rag_context.get('total_documents', 0)}")
        print(f"   ✓ Total time: {processing.get('total_time', 0):.2f}s")
        
        # Check if KG content is included
        if rag_context.get('use_knowledge_graph'):
            docs = rag_context.get('documents', [])
            if docs and 'content' in docs[0]:
                content = docs[0]['content']
                if 'Content:' in content:
                    print(f"   ✅ KG Content included! ({len(content)} chars)")
                else:
                    print(f"   ❌ KG Content missing! (only {len(content)} chars)")
        
        print("\n✅ Test completed")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")

print("\n" + "=" * 80)
print("✅ ALL TESTS COMPLETED")
print("=" * 80)
