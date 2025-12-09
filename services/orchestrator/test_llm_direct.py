"""
Test trực tiếp gọi LLM để kiểm tra xem LLM có trả về use_knowledge_graph=true không.
"""

import os
import sys
import json
import asyncio
from pathlib import Path

# Set UTF-8 encoding for console
if os.name == 'nt':  # Windows
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

sys.path.insert(0, str(Path(__file__).parent))

# Check environment
if not os.getenv("OPENROUTER_API_KEY"):
    print("ERROR: OPENROUTER_API_KEY not set!")
    sys.exit(1)


async def test_llm_direct_call():
    """Test gọi trực tiếp LLM với Smart Planner prompt"""
    
    from app.core.agent_factory import ConfigurableAgentFactory
    from app.adapters.openrouter_adapter import OpenRouterAdapter
    
    print("\n" + "="*80)
    print("TEST: GỌI LLM TRỰC TIẾP VỚI SMART PLANNER PROMPT")
    print("="*80)
    
    # Initialize LLM adapter
    api_key = os.getenv("OPENROUTER_API_KEY")
    base_url = os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")
    
    llm_adapter = OpenRouterAdapter(
        api_key=api_key,
        base_url=base_url
    )
    
    # Create agent factory
    agent_factory = ConfigurableAgentFactory()
    
    # Create Smart Planner
    print("\n1. Creating Smart Planner...")
    smart_planner = agent_factory.create_agent("smart_planner", llm_adapter)
    print(f"   Model: {smart_planner.config.model}")
    print(f"   Temperature: {smart_planner.config.temperature}")
    
    # Test queries
    test_queries = [
        {
            "query": "Môn IT001 có những môn tiên quyết nào?",
            "expected_kg": True,
            "reason": "Câu hỏi về môn tiên quyết"
        },
        {
            "query": "Nhập môn lập trình học những gì?",
            "expected_kg": True,
            "reason": "Câu hỏi về nội dung môn học"
        },
        {
            "query": "Điều 14 quy định gì?",
            "expected_kg": True,
            "reason": "Câu hỏi về Điều cụ thể"
        },
        {
            "query": "Học phí năm 2024 là bao nhiêu?",
            "expected_kg": False,
            "reason": "Câu hỏi về số liệu"
        }
    ]
    
    results = []
    
    for idx, test in enumerate(test_queries, 1):
        query = test["query"]
        expected = test["expected_kg"]
        reason = test["reason"]
        
        print(f"\n{'='*80}")
        print(f"TEST {idx}/4: {query}")
        print(f"Expected use_knowledge_graph: {expected}")
        print(f"Reason: {reason}")
        print("-" * 80)
        
        try:
            # Call Smart Planner
            print("\n2. Calling Smart Planner.process()...")
            result = await smart_planner.process({"query": query})
            
            print(f"\n3. Smart Planner Result:")
            print(f"   - intent: {result.intent}")
            print(f"   - complexity: {result.complexity} (score: {result.complexity_score})")
            print(f"   - requires_rag: {result.requires_rag}")
            print(f"   - strategy: {result.strategy}")
            
            # Key fields
            use_kg = result.use_knowledge_graph
            graph_type = result.graph_query_type if hasattr(result, 'graph_query_type') else None
            
            print(f"\n4. KNOWLEDGE GRAPH FLAGS:")
            print(f"   - use_knowledge_graph: {use_kg}")
            print(f"   - graph_query_type: {graph_type}")
            
            # Check if correct
            if use_kg == expected:
                print(f"\n   ✅ PASS - Correct!")
                status = "PASS"
            else:
                print(f"\n   ❌ FAIL - Expected {expected} but got {use_kg}")
                status = "FAIL"
            
            # Show rewritten queries
            if result.rewritten_queries:
                print(f"\n5. Rewritten Queries:")
                for i, rq in enumerate(result.rewritten_queries[:3], 1):
                    print(f"   {i}. {rq}")
            
            results.append({
                "query": query,
                "expected": expected,
                "actual": use_kg,
                "status": status,
                "graph_query_type": graph_type,
                "complexity": result.complexity,
                "complexity_score": result.complexity_score
            })
            
        except Exception as e:
            print(f"\n   ❌ ERROR: {e}")
            import traceback
            traceback.print_exc()
            results.append({
                "query": query,
                "expected": expected,
                "actual": None,
                "status": "ERROR",
                "error": str(e)
            })
    
    # Summary
    print(f"\n{'='*80}")
    print("📊 SUMMARY")
    print("="*80)
    
    passed = sum(1 for r in results if r["status"] == "PASS")
    failed = sum(1 for r in results if r["status"] == "FAIL")
    errors = sum(1 for r in results if r["status"] == "ERROR")
    total = len(results)
    
    print(f"\nResults: {passed}/{total} passed, {failed}/{total} failed, {errors}/{total} errors")
    
    # Show details
    print("\nDetails:")
    for i, r in enumerate(results, 1):
        status_icon = "✅" if r["status"] == "PASS" else "❌"
        print(f"{i}. {status_icon} {r['query']}")
        print(f"   Expected: {r['expected']}, Actual: {r.get('actual')}")
        if r.get('graph_query_type'):
            print(f"   Type: {r['graph_query_type']}")
    
    # Diagnosis
    print(f"\n{'='*80}")
    print("🔬 CHẨN ĐOÁN")
    print("="*80)
    
    if failed > 0:
        print(f"\n❌ CÓ {failed} TEST FAIL!")
        print("\nNguyên nhân có thể là:")
        print("1. LLM không hiểu system prompt về môn học")
        print("2. System prompt chưa đủ rõ ràng về khi nào dùng KG")
        print("3. LLM model không đủ tốt để phân tích")
        
        print("\nGiải pháp:")
        print("1. Cập nhật system prompt rõ ràng hơn")
        print("2. Thêm nhiều examples hơn trong prompt")
        print("3. Tăng temperature hoặc thử model khác")
    elif errors > 0:
        print(f"\n⚠️ CÓ {errors} TEST ERROR!")
        print("Kiểm tra lại kết nối LLM và API key")
    else:
        print(f"\n✅✅✅ ALL TESTS PASSED! ✅✅✅")
        print("\nLLM đang hoạt động đúng:")
        print("- Phát hiện câu hỏi về môn học")
        print("- Đánh dấu use_knowledge_graph=true")
        print("- Xác định đúng graph_query_type")
    
    return results


async def test_raw_llm_call():
    """Test gọi raw LLM API để xem response thô"""
    
    from app.adapters.openrouter_adapter import OpenRouterAdapter
    
    print(f"\n{'='*80}")
    print("TEST: RAW LLM API CALL")
    print("="*80)
    
    api_key = os.getenv("OPENROUTER_API_KEY")
    base_url = os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")
    
    llm_adapter = OpenRouterAdapter(
        api_key=api_key,
        base_url=base_url
    )
    
    # Simple system prompt
    system_prompt = """You are a Smart Query Analyzer for Chatbot-UIT.

Analyze this query and return JSON with:
- use_knowledge_graph: true if query is about courses (môn học, IT001, tiên quyết, etc.)
- graph_query_type: "local", "global", or "multi_hop"

Examples:
Query: "Môn IT001 có những môn tiên quyết nào?"
Output: {"use_knowledge_graph": true, "graph_query_type": "multi_hop"}

Query: "Học phí năm 2024?"
Output: {"use_knowledge_graph": false}

Return ONLY valid JSON."""
    
    test_query = "Môn IT001 có những môn tiên quyết nào?"
    
    print(f"\nQuery: {test_query}")
    print(f"Model: openai/gpt-4o-mini")
    print("\nCalling LLM...")
    
    try:
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": test_query}
        ]
        
        response_obj = await llm_adapter.generate(
            messages=messages,
            temperature=0.2,
            max_tokens=500
        )
        
        response = response_obj.content if hasattr(response_obj, 'content') else str(response_obj)
        
        print(f"\n✅ LLM Response:")
        print("-" * 80)
        print(response)
        print("-" * 80)
        
        # Try to parse JSON
        try:
            data = json.loads(response)
            print(f"\n✅ Parsed JSON:")
            print(json.dumps(data, indent=2, ensure_ascii=False))
            
            use_kg = data.get("use_knowledge_graph", False)
            graph_type = data.get("graph_query_type", None)
            
            print(f"\n✅ Extracted:")
            print(f"   - use_knowledge_graph: {use_kg}")
            print(f"   - graph_query_type: {graph_type}")
            
            if use_kg:
                print(f"\n✅✅✅ LLM CORRECTLY DETECTED COURSE QUERY! ✅✅✅")
            else:
                print(f"\n❌❌❌ LLM FAILED TO DETECT COURSE QUERY! ❌❌❌")
            
        except json.JSONDecodeError as e:
            print(f"\n❌ Failed to parse JSON: {e}")
            
    except Exception as e:
        print(f"\n❌ Error calling LLM: {e}")
        import traceback
        traceback.print_exc()


async def main():
    """Run all tests"""
    print("\n" + "="*80)
    print("🧪 TEST TRỰC TIẾP GỌI LLM")
    print("="*80)
    
    # Test 1: Through Smart Planner
    results = await test_llm_direct_call()
    
    # Test 2: Raw LLM call
    await test_raw_llm_call()
    
    print("\n" + "="*80)
    print("✅ TESTS COMPLETED")
    print("="*80)


if __name__ == "__main__":
    asyncio.run(main())
