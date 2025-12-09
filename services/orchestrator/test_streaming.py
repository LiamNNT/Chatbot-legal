"""
Test script for streaming chat endpoint.

This script demonstrates how to use the new streaming functionality
from the orchestrator service.
"""

import asyncio
import aiohttp
import json


async def test_streaming_chat():
    """Test the streaming chat endpoint."""
    url = "http://localhost:8000/chat"
    
    # Prepare request
    request_data = {
        "query": "UIT là gì? Giới thiệu về trường Đại học Công nghệ Thông tin",
        "session_id": "test_session",
        "use_rag": True,
        "rag_top_k": 3,
        "stream": True,  # Enable streaming
        "temperature": 0.7,
        "max_tokens": 1000
    }
    
    print("Sending streaming request to orchestrator...")
    print(f"Query: {request_data['query']}\n")
    
    async with aiohttp.ClientSession() as session:
        async with session.post(url, json=request_data) as response:
            print(f"Response status: {response.status}\n")
            
            if response.status == 200:
                print("Streaming response:\n")
                print("-" * 80)
                
                async for line in response.content:
                    line_str = line.decode('utf-8').strip()
                    
                    if line_str.startswith('data: '):
                        data_str = line_str[6:]  # Remove 'data: ' prefix
                        
                        try:
                            data = json.loads(data_str)
                            event_type = data.get('type', 'unknown')
                            content = data.get('content', '')
                            
                            if event_type == 'status':
                                print(f"\n[STATUS] {content}")
                            elif event_type == 'planning':
                                print(f"\n[PLANNING] {content}")
                            elif event_type == 'warning':
                                print(f"\n[WARNING] {content}")
                            elif event_type == 'content':
                                print(content, end='', flush=True)
                            elif event_type == 'done':
                                print(f"\n\n[DONE] {content}")
                            elif event_type == 'error':
                                print(f"\n[ERROR] {content}")
                        
                        except json.JSONDecodeError:
                            print(f"Failed to parse: {data_str}")
                
                print("-" * 80)
                print("\nStreaming completed!")
            else:
                error_text = await response.text()
                print(f"Error: {error_text}")


async def test_non_streaming_chat():
    """Test the non-streaming chat endpoint for comparison."""
    url = "http://localhost:8000/chat"
    
    # Prepare request
    request_data = {
        "query": "UIT là gì? Giới thiệu về trường Đại học Công nghệ Thông tin",
        "session_id": "test_session",
        "use_rag": True,
        "rag_top_k": 3,
        "stream": False,  # Disable streaming
        "temperature": 0.7,
        "max_tokens": 1000
    }
    
    print("Sending non-streaming request to orchestrator...")
    print(f"Query: {request_data['query']}\n")
    
    async with aiohttp.ClientSession() as session:
        async with session.post(url, json=request_data) as response:
            print(f"Response status: {response.status}\n")
            
            if response.status == 200:
                data = await response.json()
                print("Response:\n")
                print("-" * 80)
                print(data.get('response', 'No response'))
                print("-" * 80)
                print(f"\nProcessing time: {data.get('processing_stats', {}).get('total_time', 0):.2f}s")
                print(f"Model used: {data.get('model_used', 'unknown')}")
            else:
                error_text = await response.text()
                print(f"Error: {error_text}")


async def main():
    """Main test function."""
    print("=" * 80)
    print("STREAMING CHAT TEST")
    print("=" * 80)
    print()
    
    # Test 1: Streaming
    print("TEST 1: STREAMING MODE")
    print("=" * 80)
    await test_streaming_chat()
    
    print("\n\n")
    
    # Test 2: Non-streaming
    print("TEST 2: NON-STREAMING MODE (for comparison)")
    print("=" * 80)
    await test_non_streaming_chat()
    
    print("\n\n")
    print("=" * 80)
    print("ALL TESTS COMPLETED")
    print("=" * 80)


if __name__ == "__main__":
    # Note: Make sure the orchestrator service is running on http://localhost:8000
    # Start it with: python services/orchestrator/app/main.py
    asyncio.run(main())
