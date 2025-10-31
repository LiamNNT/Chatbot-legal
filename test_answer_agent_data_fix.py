#!/usr/bin/env python3
"""
Test script to verify that answer_agent receives full content from RAG.
This tests the fix for field mapping: 'text' → 'content'
"""

import asyncio
import sys
import os

# Add project root to path
sys.path.insert(0, '/home/kien/Kien/study/SE363.Q11/Chatbot-UIT/services/orchestrator')

from app.agents.multi_agent_orchestrator import MultiAgentOrchestrator
from app.adapters.rag_adapter import RAGServiceAdapter
from app.adapters.agent_adapter import AgentServiceAdapter
from app.core.agent_factory import AgentFactory
from app.core.domain import OrchestrationRequest


async def test_rag_to_answer_agent_flow():
    """Test the complete flow from RAG to Answer Agent."""
    
    print("=" * 80)
    print("TESTING RAG → ANSWER AGENT DATA FLOW")
    print("=" * 80)
    
    # Initialize adapters
    print("\n1. Initializing adapters...")
    rag_adapter = RAGServiceAdapter(rag_service_url="http://localhost:8000")
    agent_adapter = AgentServiceAdapter()
    
    # Check RAG service health
    print("\n2. Checking RAG service health...")
    is_healthy = await rag_adapter.health_check()
    if not is_healthy:
        print("✗ RAG service is not healthy!")
        return
    print("✓ RAG service is healthy")
    
    # Test RAG retrieval
    print("\n3. Testing RAG retrieval...")
    test_query = "quy định đào tạo UIT"
    
    try:
        rag_result = await rag_adapter.retrieve_context(test_query, top_k=2)
        
        print(f"\n✓ RAG returned {len(rag_result.get('retrieved_documents', []))} documents")
        
        # Analyze RAG response structure
        print("\n--- RAG Response Structure ---")
        for i, doc in enumerate(rag_result.get("retrieved_documents", []), 1):
            print(f"\nDocument {i}:")
            print(f"  Keys: {list(doc.keys())}")
            print(f"  Has 'text' field: {'text' in doc}")
            print(f"  Has 'content' field: {'content' in doc}")
            
            text_len = len(doc.get('text', ''))
            content_len = len(doc.get('content', ''))
            
            print(f"  'text' length: {text_len} chars")
            print(f"  'content' length: {content_len} chars")
            
            if text_len > 0:
                print(f"  First 100 chars of 'text': {doc.get('text', '')[:100]}")
    
    except Exception as e:
        print(f"✗ RAG retrieval failed: {e}")
        import traceback
        traceback.print_exc()
        return
    
    # Initialize orchestrator
    print("\n4. Initializing Multi-Agent Orchestrator...")
    
    try:
        # Load agent configurations
        import yaml
        config_path = '/home/kien/Kien/study/SE363.Q11/Chatbot-UIT/services/orchestrator/config/agents_config.yaml'
        
        with open(config_path, 'r', encoding='utf-8') as f:
            agent_configs = yaml.safe_load(f)
        
        agent_factory = AgentFactory(agent_configs)
        
        orchestrator = MultiAgentOrchestrator(
            agent_port=agent_adapter,
            rag_port=rag_adapter,
            agent_factory=agent_factory,
            enable_verification=False,  # Disable for faster testing
            enable_planning=False
        )
        
        print("✓ Orchestrator initialized")
        
    except Exception as e:
        print(f"✗ Failed to initialize orchestrator: {e}")
        import traceback
        traceback.print_exc()
        return
    
    # Test the retrieval step
    print("\n5. Testing _execute_retrieval_step (with field mapping fix)...")
    
    try:
        request = OrchestrationRequest(
            user_query=test_query,
            use_rag=True,
            rag_top_k=2
        )
        
        processing_stats = {}
        rag_context = await orchestrator._execute_retrieval_step(
            request,
            plan_result=None,
            processing_stats=processing_stats
        )
        
        if not rag_context:
            print("✗ No RAG context returned")
            return
        
        print(f"✓ RAG context created with {len(rag_context.retrieved_documents)} documents")
        
        # Verify field mapping
        print("\n--- Verifying Field Mapping Fix ---")
        for i, doc in enumerate(rag_context.retrieved_documents, 1):
            print(f"\nDocument {i} (after mapping):")
            print(f"  Keys: {list(doc.keys())}")
            print(f"  Has 'content' field: {'content' in doc}")
            print(f"  Has 'text' field: {'text' in doc}")
            
            content = doc.get('content', '')
            print(f"  'content' length: {len(content)} chars")
            
            if len(content) == 0:
                print(f"  ✗ WARNING: 'content' field is EMPTY!")
            else:
                print(f"  ✓ 'content' field has data: {len(content)} chars")
                print(f"  First 150 chars: {content[:150]}")
            
            # Check other fields
            print(f"  'title': {doc.get('title', 'N/A')}")
            print(f"  'source': {doc.get('source', 'N/A')}")
            print(f"  'score': {doc.get('score', 0.0):.4f}")
        
        # Test Answer Agent input preparation
        print("\n6. Testing Answer Agent input preparation...")
        
        answer_input = {
            "query": test_query,
            "context_documents": rag_context.retrieved_documents,
            "rewritten_queries": rag_context.rewritten_queries or [],
            "previous_context": ""
        }
        
        print(f"\nAnswer Agent will receive:")
        print(f"  Query: {answer_input['query']}")
        print(f"  Number of documents: {len(answer_input['context_documents'])}")
        
        for i, doc in enumerate(answer_input['context_documents'], 1):
            content = doc.get('content', '')
            print(f"\n  Document {i}:")
            print(f"    Content length: {len(content)} chars")
            
            if len(content) > 0:
                print(f"    ✓ Answer Agent WILL receive this content")
            else:
                print(f"    ✗ Answer Agent will receive EMPTY content!")
        
        print("\n" + "=" * 80)
        print("TEST SUMMARY")
        print("=" * 80)
        
        # Check if fix worked
        all_have_content = all(
            len(doc.get('content', '')) > 0 
            for doc in rag_context.retrieved_documents
        )
        
        if all_have_content:
            print("\n✅ SUCCESS: All documents have 'content' field with data!")
            print("✅ Answer Agent will receive FULL CONTENT from RAG")
        else:
            print("\n✗ FAILED: Some documents have empty 'content' field")
            print("✗ Answer Agent will NOT receive full content")
        
    except Exception as e:
        print(f"\n✗ Test failed: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        # Cleanup
        await rag_adapter.close()
        await agent_adapter.close()


if __name__ == "__main__":
    asyncio.run(test_rag_to_answer_agent_flow())
