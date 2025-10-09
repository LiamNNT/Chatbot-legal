#!/usr/bin/env python3
"""
Comprehensive test for all agents with free models.
"""

import asyncio
import sys
import os

# Add the app directory to Python path
sys.path.append('/home/kien/Kien/study/SE363.Q11/Chatbot-UIT/services/orchestrator')

from app.adapters.openrouter_adapter import OpenRouterAdapter
from app.core.domain import AgentRequest, ConversationContext


async def test_planner_agent():
    """Test Planner Agent with DeepSeek free model."""
    print("🧠 Testing Planner Agent...")
    
    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        print("❌ API key not found!")
        return False
    
    try:
        adapter = OpenRouterAdapter(api_key=api_key, timeout=None)
        
        context = ConversationContext(
            session_id="test-planner",
            messages=[],
            system_prompt="""Bạn là một AI Planner Agent chuyên nghiệp cho hệ thống Chatbot-UIT. 
Nhiệm vụ của bạn là phân tích câu hỏi của người dùng và tạo ra kế hoạch xử lý tối ưu.
Hãy trả lời bằng JSON format với các bước cụ thể."""
        )
        
        request = AgentRequest(
            prompt="Tôi muốn tìm hiểu về học phí và cách đăng ký học phần tại UIT",
            context=context,
            model="mistralai/mistral-7b-instruct:free",  # Free model
            temperature=0.1,
            max_tokens=500
        )
        
        response = await adapter.generate_response(request)
        
        print(f"✅ Planner Agent Response:")
        print(f"Model: {response.model_used}")
        print(f"Content: {response.content[:300]}...")
        print(f"Tokens: {response.tokens_used}")
        
        await adapter.close()
        return True
        
    except Exception as e:
        print(f"❌ Planner Agent Error: {e}")
        return False


async def test_query_rewriter_agent():
    """Test Query Rewriter Agent with Mistral free model."""
    print("\n✏️ Testing Query Rewriter Agent...")
    
    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        print("❌ API key not found!")
        return False
    
    try:
        adapter = OpenRouterAdapter(api_key=api_key, timeout=None)
        
        context = ConversationContext(
            session_id="test-rewriter",
            messages=[],
            system_prompt="""Bạn là một Query Rewriter Agent chuyên tối ưu hóa câu hỏi tìm kiếm.
Hãy viết lại câu hỏi để tìm kiếm hiệu quả hơn trong hệ thống RAG."""
        )
        
        request = AgentRequest(
            prompt="học phí UIT bao nhiêu tiền vậy?",
            context=context,
            model="mistralai/mistral-7b-instruct:free",  # Free model
            temperature=0.3,
            max_tokens=200
        )
        
        response = await adapter.generate_response(request)
        
        print(f"✅ Query Rewriter Agent Response:")
        print(f"Model: {response.model_used}")
        print(f"Original: học phí UIT bao nhiêu tiền vậy?")
        print(f"Rewritten: {response.content.strip()}")
        print(f"Tokens: {response.tokens_used}")
        
        await adapter.close()
        return True
        
    except Exception as e:
        print(f"❌ Query Rewriter Agent Error: {e}")
        return False


async def test_answer_agent():
    """Test Answer Agent with Gemma free model."""
    print("\n💬 Testing Answer Agent...")
    
    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        print("❌ API key not found!")
        return False
    
    try:
        adapter = OpenRouterAdapter(api_key=api_key, timeout=None)
        
        # Simulate RAG context
        rag_context = [
            "Học phí tại Đại học Công nghệ Thông tin (UIT) năm 2024: Sinh viên công lập: 756.000 VNĐ/tín chỉ.",
            "Thời gian đăng ký học phần: Thường vào tháng 7-8 cho học kỳ 1, tháng 12-1 cho học kỳ 2.",
            "Sinh viên cần đăng nhập vào hệ thống Portal để đăng ký học phần trực tuyến."
        ]
        
        context = ConversationContext(
            session_id="test-answer",
            messages=[],
            system_prompt=f"""Bạn là một Answer Agent chuyên trả lời câu hỏi dựa trên context được cung cấp.
Hãy sử dụng thông tin sau để trả lời câu hỏi một cách chính xác và hữu ích:

CONTEXT:
{chr(10).join(rag_context)}

Hãy trả lời bằng tiếng Việt một cách tự nhiên và thân thiện."""
        )
        
        request = AgentRequest(
            prompt="Học phí UIT bao nhiêu tiền? Và làm thế nào để đăng ký học phần?",
            context=context,
            model="google/gemma-2-9b-it:free",  # Free model
            temperature=0.7,
            max_tokens=400
        )
        
        response = await adapter.generate_response(request)
        
        print(f"✅ Answer Agent Response:")
        print(f"Model: {response.model_used}")
        print(f"Answer: {response.content}")
        print(f"Tokens: {response.tokens_used}")
        
        await adapter.close()
        return True
        
    except Exception as e:
        print(f"❌ Answer Agent Error: {e}")
        return False


async def test_verifier_agent():
    """Test Verifier Agent with DeepSeek R1 free model."""
    print("\n🔍 Testing Verifier Agent...")
    
    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        print("❌ API key not found!")
        return False
    
    try:
        adapter = OpenRouterAdapter(api_key=api_key, timeout=None)
        
        answer_to_verify = """Học phí tại UIT năm 2024 là 756.000 VNĐ/tín chỉ cho sinh viên công lập. 
Để đăng ký học phần, sinh viên cần đăng nhập vào hệ thống Portal vào thời gian quy định 
(tháng 7-8 cho học kỳ 1, tháng 12-1 cho học kỳ 2)."""
        
        context = ConversationContext(
            session_id="test-verifier",
            messages=[],
            system_prompt=f"""Bạn là một Verifier Agent chuyên kiểm tra độ chính xác của câu trả lời.
Hãy đánh giá câu trả lời sau và cho điểm từ 1-10:

ANSWER TO VERIFY:
{answer_to_verify}

Hãy đánh giá về: độ chính xác, tính đầy đủ, độ rõ ràng và trả lời bằng JSON format."""
        )
        
        request = AgentRequest(
            prompt="Đánh giá câu trả lời về học phí và đăng ký học phần UIT",
            context=context,
            model="deepseek/deepseek-r1:free",  # Free model
            temperature=0.2,
            max_tokens=300
        )
        
        response = await adapter.generate_response(request)
        
        print(f"✅ Verifier Agent Response:")
        print(f"Model: {response.model_used}")
        print(f"Verification: {response.content}")
        print(f"Tokens: {response.tokens_used}")
        
        await adapter.close()
        return True
        
    except Exception as e:
        print(f"❌ Verifier Agent Error: {e}")
        return False


async def test_response_agent():
    """Test Response Agent with LongCat free model."""
    print("\n📝 Testing Response Agent...")
    
    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        print("❌ API key not found!")
        return False
    
    try:
        adapter = OpenRouterAdapter(api_key=api_key, timeout=None)
        
        raw_answer = """Học phí tại UIT năm 2024 là 756.000 VNĐ/tín chỉ cho sinh viên công lập. 
Để đăng ký học phần, sinh viên cần đăng nhập vào hệ thống Portal vào thời gian quy định."""
        
        context = ConversationContext(
            session_id="test-response",
            messages=[],
            system_prompt=f"""Bạn là một Response Agent chuyên tạo phản hồi cuối cùng thân thiện với người dùng.
Hãy chỉnh sửa câu trả lời sau để làm cho nó thân thiện, dễ hiểu và hữu ích hơn:

RAW ANSWER:
{raw_answer}

Hãy tạo response cuối cùng với tone thân thiện và cung cấp thêm gợi ý hữu ích."""
        )
        
        request = AgentRequest(
            prompt="Tạo response cuối cùng về học phí UIT",
            context=context,
            model="meituan/longcat-flash-chat:free",  # Free model  
            temperature=0.8,
            max_tokens=400
        )
        
        response = await adapter.generate_response(request)
        
        print(f"✅ Response Agent Response:")
        print(f"Model: {response.model_used}")
        print(f"Final Response: {response.content}")
        print(f"Tokens: {response.tokens_used}")
        
        await adapter.close()
        return True
        
    except Exception as e:
        print(f"❌ Response Agent Error: {e}")
        return False


async def main():
    """Run all agent tests."""
    print("🚀 Testing All Agents with Free Models")
    print("=" * 60)
    
    tests = [
        ("Planner Agent", test_planner_agent),
        ("Query Rewriter Agent", test_query_rewriter_agent), 
        ("Answer Agent", test_answer_agent),
        ("Verifier Agent", test_verifier_agent),
        ("Response Agent", test_response_agent)
    ]
    
    results = []
    
    for name, test_func in tests:
        try:
            print(f"\n{'='*20} {name} {'='*20}")
            result = await test_func()
            results.append((name, result))
        except Exception as e:
            print(f"❌ {name} failed with exception: {e}")
            results.append((name, False))
    
    print("\n" + "=" * 60)
    print("📊 FINAL RESULTS:")
    print("=" * 60)
    
    passed = 0
    for name, result in results:
        status = "✅ PASSED" if result else "❌ FAILED"
        print(f"{name}: {status}")
        if result:
            passed += 1
    
    print(f"\nOverall: {passed}/{len(results)} agents working correctly")
    
    if passed == len(results):
        print("🎉 ALL AGENTS WORKING PERFECTLY!")
    else:
        print("⚠️  Some agents need attention.")


if __name__ == "__main__":
    asyncio.run(main())