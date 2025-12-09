#!/usr/bin/env python3
"""
Final test: Full pipeline với content đã fix
Test xem LLM có trả lời được từ KG content không
"""

import sys
import os

# Add paths
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'rag_services')))

from app.agents.optimized_orchestrator import OptimizedMultiAgentOrchestrator
import asyncio


async def test_full_pipeline():
    """Test full pipeline với KG content đã fix"""
    
    print("=" * 80)
    print("🧪 TEST FULL PIPELINE VỚI KG CONTENT ĐÃ FIX")
    print("=" * 80)
    print()
    
    # Init orchestrator
    print("1. Initializing orchestrator...")
    orchestrator = OptimizedMultiAgentOrchestrator()
    
    # Test questions that should use KG
    test_questions = [
        "Điều 19 quy định gì?",
        "Sinh viên chuyển ngành cần điều kiện gì?",
        "Điều kiện để chuyển trường là gì?",
    ]
    
    for i, question in enumerate(test_questions, 1):
        print()
        print("=" * 80)
        print(f"TEST {i}: {question}")
        print("=" * 80)
        
        # Process
        result = await orchestrator.process(
            query=question,
            conversation_history=[],
            session_id="test_session_final"
        )
        
        print()
        print("📝 ANSWER:")
        print("-" * 80)
        print(result.get("answer", "No answer"))
        print("-" * 80)
        
        print()
        print("🔍 METADATA:")
        metadata = result.get("metadata", {})
        print(f"   - Used KG: {metadata.get('used_knowledge_graph', False)}")
        print(f"   - Confidence: {metadata.get('confidence', 0)}")
        
        if "graph_context" in metadata:
            graph_ctx = metadata["graph_context"]
            print(f"   - Graph nodes: {len(graph_ctx.get('nodes', []))}")
            print(f"   - Context length: {len(str(graph_ctx))} chars")
        
        print()
        print("✅ Test completed")
    
    print()
    print("=" * 80)
    print("✅ ALL TESTS COMPLETED")
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(test_full_pipeline())
