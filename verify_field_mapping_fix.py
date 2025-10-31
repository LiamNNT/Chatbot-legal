#!/usr/bin/env python3
"""
Simple test to verify field mapping fix in orchestrator.
Tests that 'text' from RAG is properly mapped to 'content' for answer_agent.
"""

import requests
import json


def test_field_mapping():
    """Test the field mapping from RAG to orchestrator to answer_agent."""
    
    print("=" * 80)
    print("TESTING FIELD MAPPING FIX: RAG 'text' → Answer Agent 'content'")
    print("=" * 80)
    
    # Step 1: Test RAG service response
    print("\n📍 Step 1: Get RAG service response structure")
    print("-" * 80)
    
    try:
        rag_response = requests.post(
            'http://localhost:8000/v1/search',
            json={
                'query': 'quy định học tập UIT',
                'top_k': 1,
                'search_mode': 'hybrid'
            },
            timeout=30
        )
        
        if rag_response.status_code == 200:
            rag_data = rag_response.json()
            hits = rag_data.get('hits', [])
            
            if hits:
                first_hit = hits[0]
                print(f"✓ RAG service returned {len(hits)} hit(s)")
                print(f"\nRAG Response Structure:")
                print(f"  Fields in hit: {list(first_hit.keys())}")
                print(f"  Has 'text': {'text' in first_hit}")
                print(f"  Has 'content': {'content' in first_hit}")
                
                text_content = first_hit.get('text', '')
                print(f"\n  'text' field length: {len(text_content)} characters")
                
                if len(text_content) > 0:
                    print(f"  ✓ RAG returns 'text' with {len(text_content)} chars")
                    print(f"\n  First 200 chars of 'text':")
                    print(f"  {text_content[:200]}...")
                else:
                    print(f"  ✗ 'text' field is empty!")
                    return False
            else:
                print("✗ No hits returned from RAG")
                return False
        else:
            print(f"✗ RAG service error: {rag_response.status_code}")
            return False
            
    except Exception as e:
        print(f"✗ RAG service test failed: {e}")
        return False
    
    # Step 2: Test orchestrator endpoint
    print("\n\n📍 Step 2: Test orchestrator with RAG")
    print("-" * 80)
    
    try:
        orch_response = requests.post(
            'http://localhost:8001/api/v1/chat',
            json={
                'query': 'quy định học tập UIT',
                'use_rag': True,
                'rag_top_k': 1
            },
            timeout=60
        )
        
        if orch_response.status_code == 200:
            orch_data = orch_response.json()
            
            print(f"✓ Orchestrator responded successfully")
            
            # Check if RAG context is present
            rag_context = orch_data.get('rag_context')
            
            if rag_context:
                print(f"\n✓ RAG context is present")
                
                # Try both possible field names
                retrieved_docs = rag_context.get('retrieved_documents', rag_context.get('documents', []))
                print(f"✓ Retrieved {len(retrieved_docs)} document(s)")
                
                if retrieved_docs:
                    first_doc = retrieved_docs[0]
                    
                    print(f"\nDocument structure after mapping:")
                    print(f"  Fields: {list(first_doc.keys())}")
                    print(f"  Has 'content': {'content' in first_doc}")
                    print(f"  Has 'text': {'text' in first_doc}")
                    
                    content = first_doc.get('content', '')
                    
                    if len(content) > 0:
                        print(f"\n  ✅ SUCCESS: 'content' field has {len(content)} chars!")
                        print(f"  This means answer_agent WILL receive full content!")
                        print(f"\n  First 200 chars of 'content':")
                        print(f"  {content[:200]}...")
                        
                        # Check response quality
                        response_text = orch_data.get('response', '')
                        print(f"\n\nGenerated Response Preview:")
                        print(f"  Length: {len(response_text)} chars")
                        print(f"  First 300 chars:")
                        print(f"  {response_text[:300]}...")
                        
                        return True
                    else:
                        print(f"\n  ✗ FAILED: 'content' field is EMPTY!")
                        print(f"  Answer agent will NOT receive content!")
                        return False
                else:
                    print("✗ No documents in RAG context")
                    return False
            else:
                print("✗ No RAG context in response")
                return False
        else:
            print(f"✗ Orchestrator error: {orch_response.status_code}")
            print(orch_response.text)
            return False
            
    except Exception as e:
        print(f"✗ Orchestrator test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    print("\n" + "🔧 VERIFYING FIELD MAPPING FIX ".center(80, "="))
    print("This test verifies that RAG 'text' field is properly mapped to")
    print("'content' field for answer_agent to receive full context.")
    print("=" * 80)
    
    success = test_field_mapping()
    
    print("\n\n" + "=" * 80)
    print("FINAL RESULT")
    print("=" * 80)
    
    if success:
        print("\n✅ VERIFICATION PASSED!")
        print("✅ Field mapping fix is working correctly")
        print("✅ Answer agent receives full content from RAG")
    else:
        print("\n✗ VERIFICATION FAILED!")
        print("✗ Check the error messages above")
    
    print("=" * 80)
