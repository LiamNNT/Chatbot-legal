#!/usr/bin/env python3
"""
Debug Smart Planner - xem nó có quyết định dùng KG không
"""
import asyncio
import sys
import os
from pathlib import Path
import json

# Add orchestrator to path
sys.path.insert(0, str(Path(__file__).parent))

# Load environment
try:
    from dotenv import load_dotenv
    env_path = Path(__file__).parent / '.env'
    load_dotenv(env_path)
except:
    pass

# Import after path is set
from app.core.container import get_container
from app.core.domain import OrchestrationRequest


async def debug_planner():
    """Debug Smart Planner decisions"""
    
    print("=" * 80)
    print("DEBUG: SMART PLANNER DECISIONS")
    print("=" * 80)
    
    test_queries = [
        "Điều 19 quy định về vấn đề gì?",
        "Điều kiện chuyển ngành là gì?",
    ]
    
    try:
        print("\n🔧 Khởi tạo Orchestrator...")
        container = get_container()
        orchestrator = container.get_multi_agent_orchestrator()
        
        # Access Smart Planner directly
        if hasattr(orchestrator, 'smart_planner') and orchestrator.smart_planner:
            planner = orchestrator.smart_planner
            print("✅ Smart Planner: AVAILABLE")
        else:
            print("❌ Smart Planner: NOT AVAILABLE")
            return
        
        print("\n" + "=" * 80)
        
        for i, query in enumerate(test_queries, 1):
            print(f"\n{'=' * 80}")
            print(f"TEST {i}/{len(test_queries)}: {query}")
            print(f"{'=' * 80}")
            
            try:
                # Call planner's process method with dict input
                print("\n⏳ Calling Smart Planner...")
                input_data = {
                    "query": query,
                    "context": {}
                }
                
                plan_result = await planner.process(input_data)
                
                if plan_result:
                    print("\n✅ Plan Result received")
                    
                    # Check specific fields without JSON serialization
                    print("\n🔍 Key Decisions:")
                    if hasattr(plan_result, 'use_knowledge_graph'):
                        kg_decision = plan_result.use_knowledge_graph
                        print(f"   - Use Knowledge Graph: {'✅ YES' if kg_decision else '❌ NO'}")
                    else:
                        print("   - use_knowledge_graph field: NOT FOUND")
                    
                    if hasattr(plan_result, 'requires_rag'):
                        print(f"   - Requires RAG: {'✅ YES' if plan_result.requires_rag else '❌ NO'}")
                    
                    if hasattr(plan_result, 'intent'):
                        print(f"   - Intent: {plan_result.intent}")
                    
                    if hasattr(plan_result, 'complexity_score'):
                        print(f"   - Complexity: {plan_result.complexity_score}/10")
                    
                    if hasattr(plan_result, 'strategy'):
                        print(f"   - Strategy: {plan_result.strategy}")
                    
                    if hasattr(plan_result, 'optimized_queries'):
                        print(f"   - Optimized Queries: {len(plan_result.optimized_queries)}")
                        for idx, q in enumerate(plan_result.optimized_queries[:3], 1):
                            print(f"      {idx}. {q}")
                    
                    if hasattr(plan_result, 'search_terms'):
                        print(f"   - Search Terms: {plan_result.search_terms}")
                    
                    # Show all attributes
                    print("\n📋 All Attributes:")
                    for attr in dir(plan_result):
                        if not attr.startswith('_'):
                            try:
                                value = getattr(plan_result, attr)
                                if not callable(value):
                                    print(f"   - {attr}: {type(value).__name__}")
                            except:
                                pass
                    
                else:
                    print("\n❌ No plan result")
                    
            except Exception as e:
                print(f"\n❌ Error: {e}")
                import traceback
                traceback.print_exc()
            
            if i < len(test_queries):
                print("\n⏸️  Waiting 1 second...")
                await asyncio.sleep(1)
        
        print(f"\n{'=' * 80}")
        print("DEBUG COMPLETED")
        print(f"{'=' * 80}")
        
    except Exception as e:
        print(f"\n❌ CRITICAL ERROR: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    print("\n🚀 Starting Planner Debug\n")
    asyncio.run(debug_planner())
