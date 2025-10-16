#!/usr/bin/env python3
"""
Demo đơn giản: Test Agent gọi RAG trực tiếp (không qua HTTP API)
Tránh vấn đề dependency conflicts giữa các services
"""

import asyncio
import sys
from pathlib import Path

# Add paths
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root / "services" / "rag_services"))
sys.path.insert(0, str(project_root / "services" / "orchestrator"))

# ANSI colors
class Colors:
    GREEN = '\033[92m'
    BLUE = '\033[94m'
    YELLOW = '\033[93m'
    CYAN = '\033[96m'
    RED = '\033[91m'
    BOLD = '\033[1m'
    END = '\033[0m'

def print_header(text):
    print(f"\n{Colors.BOLD}{Colors.CYAN}{'='*80}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.CYAN}{text.center(80)}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.CYAN}{'='*80}{Colors.END}\n")

async def test_rag_direct():
    """Test RAG service trực tiếp."""
    print_header("TEST 1: RAG Service Trực Tiếp")
    
    try:
        # Import RAG components
        from infrastructure.container import get_search_service
        
        search_service = get_search_service()
        
        # Test query
        query = "Chương trình đào tạo Khoa học Máy tính 2024"
        print(f"{Colors.BLUE}🔍 Query:{Colors.END} {query}\n")
        
        # Search
        results = await search_service.search(
            query=query,
            top_k=3,
            search_mode="vector"
        )
        
        # Extract results
        if hasattr(results, 'results'):
            result_list = results.results
        elif isinstance(results, dict):
            result_list = results.get('results', [])
        else:
            result_list = results if isinstance(results, list) else []
        
        print(f"{Colors.GREEN}✅ RAG Search Successful!{Colors.END}")
        print(f"{Colors.YELLOW}Found {len(result_list)} results{Colors.END}\n")
        
        for i, result in enumerate(result_list, 1):
            metadata = result.get('metadata', {})
            print(f"{Colors.BOLD}[{i}] {metadata.get('title', 'N/A')}{Colors.END}")
            print(f"    Score: {result.get('score', 0):.4f}")
            print(f"    Preview: {result.get('text', '')[:150]}...\n")
        
        return True
        
    except Exception as e:
        print(f"{Colors.RED}❌ RAG Error: {e}{Colors.END}")
        import traceback
        traceback.print_exc()
        return False

async def test_agent_simple():
    """Test Orchestrator agent (simple mode)."""
    print_header("TEST 2: Orchestrator Agent (Simple Mode)")
    
    try:
        # Import orchestrator components
        from app.core.container import get_orchestration_service
        from app.core.domain import OrchestrationRequest
        
        service = get_orchestration_service()
        
        # Test query
        query = "Chương trình đào tạo Khoa học Máy tính 2024 có những gì?"
        print(f"{Colors.BLUE}👤 User Query:{Colors.END} {query}\n")
        
        # Create request
        request = OrchestrationRequest(
            user_query=query,
            session_id="demo-test",
            use_rag=True,
            rag_top_k=3
        )
        
        print(f"{Colors.CYAN}🤖 Agent processing...{Colors.END}\n")
        
        # Process
        response = await service.process_request(request)
        
        print(f"{Colors.GREEN}✅ Agent Response:{Colors.END}")
        print(f"{Colors.BOLD}{response.response}{Colors.END}\n")
        
        # Show RAG context if available
        if response.rag_context:
            docs = response.rag_context.retrieved_documents
            print(f"{Colors.YELLOW}📚 RAG Context: {len(docs)} documents used{Colors.END}")
            for i, doc in enumerate(docs, 1):
                print(f"  [{i}] {doc.get('metadata', {}).get('title', 'N/A')}")
        
        # Show stats
        print(f"\n{Colors.CYAN}📊 Stats:{Colors.END}")
        for key, value in response.processing_stats.items():
            if value is not None:
                print(f"  {key}: {value}")
        
        return True
        
    except Exception as e:
        print(f"{Colors.RED}❌ Agent Error: {e}{Colors.END}")
        import traceback
        traceback.print_exc()
        return False

async def main():
    """Main demo function."""
    print(f"\n{Colors.BOLD}{Colors.GREEN}")
    print("╔══════════════════════════════════════════════════════════════════════════════╗")
    print("║              DEMO: Agent + RAG Integration (Direct Test)                    ║")
    print("║                   No HTTP APIs - Direct Function Calls                      ║")
    print("╚══════════════════════════════════════════════════════════════════════════════╝")
    print(f"{Colors.END}")
    
    # Test RAG first
    rag_ok = await test_rag_direct()
    
    if not rag_ok:
        print(f"\n{Colors.RED}⚠️  RAG test failed. Skipping agent test.{Colors.END}")
        print(f"{Colors.YELLOW}Make sure Weaviate is running: docker ps | grep weaviate{Colors.END}\n")
        return
    
    # Then test agent
    agent_ok = await test_agent_simple()
    
    # Summary
    print_header("SUMMARY")
    
    print(f"RAG Service:        {Colors.GREEN}✅ OK{Colors.END}" if rag_ok else f"RAG Service:        {Colors.RED}❌ FAILED{Colors.END}")
    print(f"Agent Integration:  {Colors.GREEN}✅ OK{Colors.END}" if agent_ok else f"Agent Integration:  {Colors.RED}❌ FAILED{Colors.END}")
    
    if rag_ok and agent_ok:
        print(f"\n{Colors.BOLD}{Colors.GREEN}🎉 All tests passed! Agent can interact with RAG!{Colors.END}\n")
    else:
        print(f"\n{Colors.YELLOW}⚠️  Some tests failed. Check errors above.{Colors.END}\n")

if __name__ == "__main__":
    asyncio.run(main())
