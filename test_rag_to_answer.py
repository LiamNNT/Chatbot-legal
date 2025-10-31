#!/usr/bin/env python3
"""
Test script to verify data flow from RAG to Answer Agent.
This checks if answer_agent receives full content from RAG.
"""

import requests
import json


def test_rag_response_structure():
    """Test RAG service response structure."""
    print("=" * 80)
    print("TESTING RAG SERVICE RESPONSE STRUCTURE")
    print("=" * 80)
    
    try:
        response = requests.post(
            'http://localhost:8000/v1/search',
            json={
                'query': 'quy định đào tạo UIT',
                'top_k': 2,
                'search_mode': 'hybrid'
            },
            timeout=None
        )
        
        if response.status_code == 200:
            data = response.json()
            print(f"\n✓ RAG Service responded with status 200")
            print(f"✓ Top-level keys: {list(data.keys())}")
            
            # Check hits
            hits = data.get('hits', [])
            print(f"✓ Number of hits: {len(hits)}")
            
            if hits:
                print("\n" + "=" * 80)
                print("ANALYZING FIRST HIT")
                print("=" * 80)
                
                first_hit = hits[0]
                print(f"\nKeys in hit: {list(first_hit.keys())}")
                print(f"Score: {first_hit.get('score', 'N/A')}")
                
                # Check text field
                text = first_hit.get('text', '')
                content = first_hit.get('content', '')
                
                print(f"\n📄 'text' field length: {len(text)} characters")
                print(f"📄 'content' field length: {len(content)} characters")
                
                # Show first part of text
                if text:
                    print(f"\n--- First 300 characters of 'text' field ---")
                    print(text[:300])
                    print("...")
                    
                    # Check if text is truncated in middle
                    if len(text) > 500:
                        print(f"\n--- Middle 300 characters (around position {len(text)//2}) ---")
                        mid = len(text) // 2
                        print(text[mid-150:mid+150])
                        print("...")
                    
                    # Check end
                    if len(text) > 300:
                        print(f"\n--- Last 300 characters of 'text' field ---")
                        print("...")
                        print(text[-300:])
                
                print("\n" + "=" * 80)
                print("CHECKING ALL HITS")
                print("=" * 80)
                
                for i, hit in enumerate(hits, 1):
                    text_len = len(hit.get('text', ''))
                    content_len = len(hit.get('content', ''))
                    score = hit.get('score', 0)
                    print(f"\nHit {i}:")
                    print(f"  Score: {score:.4f}")
                    print(f"  Text length: {text_len} chars")
                    print(f"  Content length: {content_len} chars")
                    print(f"  Metadata: {hit.get('metadata', {})}")
            
            return data
        else:
            print(f"✗ RAG Service error: {response.status_code}")
            print(response.text)
            return None
            
    except Exception as e:
        print(f"✗ Error: {e}")
        import traceback
        traceback.print_exc()
        return None


def test_answer_agent_input():
    """Simulate what answer_agent receives."""
    print("\n" + "=" * 80)
    print("SIMULATING ANSWER AGENT INPUT")
    print("=" * 80)
    
    # Get RAG data
    rag_response = test_rag_response_structure()
    
    if not rag_response:
        print("✗ No RAG response to analyze")
        return
    
    # Simulate what orchestrator passes to answer_agent
    hits = rag_response.get('hits', [])
    
    # Check the mapping in orchestrator
    print("\n--- Checking Orchestrator Mapping ---")
    print("Orchestrator creates context_documents from hits...")
    
    context_documents = []
    for i, doc in enumerate(hits, 1):
        # This is what multi_agent_orchestrator does
        mapped_doc = {
            "title": doc.get("title", f"Document {i}"),
            "content": doc.get("text", doc.get("content", "")),  # Key mapping here!
            "score": doc.get("score", 0.0),
            "source": doc.get("source", "Unknown")
        }
        context_documents.append(mapped_doc)
        
        print(f"\nDocument {i}:")
        print(f"  Original 'text' length: {len(doc.get('text', ''))} chars")
        print(f"  Original 'content' length: {len(doc.get('content', ''))} chars")
        print(f"  Mapped 'content' length: {len(mapped_doc['content'])} chars")
        
        # Check if mapping loses data
        original_text_len = len(doc.get('text', ''))
        mapped_content_len = len(mapped_doc['content'])
        
        if original_text_len != mapped_content_len:
            print(f"  ⚠️  WARNING: Length mismatch! {original_text_len} -> {mapped_content_len}")
        else:
            print(f"  ✓ Length preserved: {mapped_content_len} chars")
    
    print("\n" + "=" * 80)
    print("ANSWER AGENT PROMPT CONSTRUCTION")
    print("=" * 80)
    
    # Simulate answer_agent._build_answer_prompt
    query = "quy định đào tạo UIT"
    
    print(f"\nQuery: {query}")
    print(f"Number of context documents: {len(context_documents)}")
    
    for i, doc in enumerate(context_documents, 1):
        title = doc.get("title", f"Tài liệu {i}")
        content = doc.get("content", "")
        score = doc.get("score", 0.0)
        source = doc.get("source", "Unknown")
        
        print(f"\n[{i}] {title} (Score: {score:.2f}, Source: {source})")
        print(f"Content length being sent to LLM: {len(content)} chars")
        
        # Check if content is being truncated in prompt building
        # In the original code, it was: content[:500] - THIS WAS THE BUG!
        print(f"First 200 chars: {content[:200]}")
        
        if len(content) > 500:
            print(f"\n⚠️  CRITICAL: This document has {len(content)} chars!")
            print(f"If answer_agent truncates to 500 chars, it loses {len(content) - 500} chars!")
    
    return context_documents


if __name__ == "__main__":
    test_answer_agent_input()
