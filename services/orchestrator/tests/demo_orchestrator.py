#!/usr/bin/env python3
"""
Demo script for testing orchestrator integration.

This script demonstrates the orchestrator functionality by testing
various scenarios and endpoints.
"""

import asyncio
import aiohttp
import json
import os
import time
from typing import Dict, Any

# Configuration
ORCHESTRATOR_URL = "http://localhost:8002"
RAG_SERVICE_URL = "http://localhost:8001"


class OrchestatorDemo:
    """Demo class for testing orchestrator functionality."""
    
    def __init__(self, orchestrator_url: str = ORCHESTRATOR_URL):
        self.orchestrator_url = orchestrator_url.rstrip('/')
        self.session: aiohttp.ClientSession = None
    
    async def __aenter__(self):
        """Async context manager entry."""
        self.session = aiohttp.ClientSession()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self.session:
            await self.session.close()
    
    async def test_health_check(self) -> Dict[str, Any]:
        """Test health check endpoint."""
        print("🏥 Testing health check...")
        
        try:
            async with self.session.get(f"{self.orchestrator_url}/api/v1/health") as response:
                if response.status == 200:
                    data = await response.json()
                    print("✅ Health check passed")
                    return data
                else:
                    print(f"❌ Health check failed: {response.status}")
                    return {"error": f"HTTP {response.status}"}
        except Exception as e:
            print(f"❌ Health check error: {str(e)}")
            return {"error": str(e)}
    
    async def test_simple_chat(self) -> Dict[str, Any]:
        """Test simple chat without RAG."""
        print("\n💬 Testing simple chat (no RAG)...")
        
        payload = {
            "query": "Xin chào! Bạn có thể giúp gì cho tôi?",
            "use_rag": False,
            "session_id": "demo_session_simple"
        }
        
        try:
            async with self.session.post(
                f"{self.orchestrator_url}/api/v1/chat",
                json=payload
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    print("✅ Simple chat successful")
                    print(f"Response: {data['response'][:100]}...")
                    return data
                else:
                    error_text = await response.text()
                    print(f"❌ Simple chat failed: {response.status} - {error_text}")
                    return {"error": f"HTTP {response.status}: {error_text}"}
        except Exception as e:
            print(f"❌ Simple chat error: {str(e)}")
            return {"error": str(e)}
    
    async def test_rag_chat(self) -> Dict[str, Any]:
        """Test chat with RAG integration."""
        print("\n🔍 Testing RAG-enhanced chat...")
        
        payload = {
            "query": "Hướng dẫn đăng ký học phần tại UIT như thế nào?",
            "use_rag": True,
            "rag_top_k": 3,
            "session_id": "demo_session_rag"
        }
        
        try:
            async with self.session.post(
                f"{self.orchestrator_url}/api/v1/chat",
                json=payload
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    print("✅ RAG chat successful")
                    print(f"Response: {data['response'][:100]}...")
                    
                    if data.get('rag_context'):
                        docs_count = len(data['rag_context']['documents'])
                        print(f"📚 Retrieved {docs_count} documents")
                    
                    stats = data.get('processing_stats', {})
                    print(f"⏱️  Processing time: {stats.get('total_time', 0):.2f}s")
                    
                    return data
                else:
                    error_text = await response.text()
                    print(f"❌ RAG chat failed: {response.status} - {error_text}")
                    return {"error": f"HTTP {response.status}: {error_text}"}
        except Exception as e:
            print(f"❌ RAG chat error: {str(e)}")
            return {"error": str(e)}
    
    async def test_conversation_flow(self) -> Dict[str, Any]:
        """Test conversation flow with multiple messages."""
        print("\n💭 Testing conversation flow...")
        
        session_id = "demo_session_conversation"
        messages = [
            "Xin chào, tôi muốn biết về quy trình đăng ký học phần tại UIT.",
            "Còn về học phí thì sao? Chi phí học tại UIT như thế nào?",
            "Cảm ơn bạn! Thông tin rất hữu ích."
        ]
        
        responses = []
        
        for i, message in enumerate(messages, 1):
            print(f"\n📨 Message {i}: {message}")
            
            payload = {
                "query": message,
                "use_rag": True,
                "session_id": session_id,
                "rag_top_k": 3
            }
            
            try:
                async with self.session.post(
                    f"{self.orchestrator_url}/api/v1/chat",
                    json=payload
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        print(f"🤖 Response {i}: {data['response'][:100]}...")
                        responses.append(data)
                    else:
                        error_text = await response.text()
                        print(f"❌ Message {i} failed: {response.status} - {error_text}")
                        responses.append({"error": f"HTTP {response.status}: {error_text}"})
            except Exception as e:
                print(f"❌ Message {i} error: {str(e)}")
                responses.append({"error": str(e)})
            
            # Small delay between messages
            await asyncio.sleep(1)
        
        return {"conversation_responses": responses}
    
    async def test_stream_chat(self) -> Dict[str, Any]:
        """Test streaming chat endpoint."""
        print("\n🌊 Testing streaming chat...")
        
        payload = {
            "query": "Hãy giải thích chi tiết về quy trình nhập học tại UIT.",
            "use_rag": True,
            "stream": True,
            "session_id": "demo_session_stream"
        }
        
        try:
            async with self.session.post(
                f"{self.orchestrator_url}/api/v1/chat/stream",
                json=payload
            ) as response:
                if response.status == 200:
                    print("✅ Stream started")
                    print("📡 Streaming response: ", end="", flush=True)
                    
                    full_response = ""
                    async for line in response.content:
                        line_str = line.decode('utf-8').strip()
                        
                        if line_str.startswith('data: '):
                            data_str = line_str[6:]
                            
                            try:
                                data = json.loads(data_str)
                                
                                if 'content' in data:
                                    content = data['content']
                                    print(content, end="", flush=True)
                                    full_response += content
                                elif 'done' in data:
                                    print("\n✅ Stream completed")
                                    break
                                elif 'error' in data:
                                    print(f"\n❌ Stream error: {data['error']}")
                                    return {"error": data['error']}
                            
                            except json.JSONDecodeError:
                                continue
                    
                    return {"streamed_response": full_response}
                else:
                    error_text = await response.text()
                    print(f"❌ Stream failed: {response.status} - {error_text}")
                    return {"error": f"HTTP {response.status}: {error_text}"}
        
        except Exception as e:
            print(f"❌ Stream error: {str(e)}")
            return {"error": str(e)}
    
    async def test_conversations_management(self) -> Dict[str, Any]:
        """Test conversation management endpoints."""
        print("\n📋 Testing conversation management...")
        
        # List conversations
        try:
            async with self.session.get(
                f"{self.orchestrator_url}/api/v1/conversations"
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    print(f"✅ Found {data['total_count']} active conversations")
                    
                    # Try to delete a demo conversation
                    if data['conversations']:
                        session_to_delete = data['conversations'][0]['session_id']
                        
                        async with self.session.delete(
                            f"{self.orchestrator_url}/api/v1/conversations/{session_to_delete}"
                        ) as delete_response:
                            if delete_response.status == 200:
                                delete_data = await delete_response.json()
                                print(f"✅ Deleted conversation: {delete_data['message']}")
                            else:
                                print(f"❌ Delete failed: {delete_response.status}")
                    
                    return data
                else:
                    error_text = await response.text()
                    print(f"❌ List conversations failed: {response.status} - {error_text}")
                    return {"error": f"HTTP {response.status}: {error_text}"}
        
        except Exception as e:
            print(f"❌ Conversations management error: {str(e)}")
            return {"error": str(e)}
    
    async def run_all_tests(self) -> Dict[str, Any]:
        """Run all demo tests."""
        print("🚀 Starting Orchestrator Demo Tests\n")
        print("=" * 50)
        
        results = {}
        
        # Test health check
        results['health'] = await self.test_health_check()
        
        # Only continue if health check passes
        if 'error' not in results['health']:
            results['simple_chat'] = await self.test_simple_chat()
            results['rag_chat'] = await self.test_rag_chat()
            results['conversation_flow'] = await self.test_conversation_flow()
            results['stream_chat'] = await self.test_stream_chat()
            results['conversations_management'] = await self.test_conversations_management()
        else:
            print("\n❌ Health check failed, skipping other tests")
        
        print("\n" + "=" * 50)
        print("🏁 Demo tests completed!")
        
        return results


async def main():
    """Main demo function."""
    print("Orchestrator Integration Demo")
    print("============================")
    
    # Check if environment variables are set
    if not os.getenv("OPENROUTER_API_KEY"):
        print("⚠️  Warning: OPENROUTER_API_KEY not set")
        print("Set this environment variable to test with real OpenRouter API")
    
    async with OrchestatorDemo() as demo:
        results = await demo.run_all_tests()
        
        # Print summary
        print("\n📊 Test Results Summary:")
        for test_name, result in results.items():
            if isinstance(result, dict) and 'error' in result:
                print(f"❌ {test_name}: FAILED - {result['error']}")
            else:
                print(f"✅ {test_name}: PASSED")


if __name__ == "__main__":
    asyncio.run(main())