#!/usr/bin/env python3
"""
Test script để kiểm tra xem Agent có truy xuất RAG không
và in ra chi tiết những gì được retrieve
"""

import requests
import json
from datetime import datetime

# Colors for output
class Colors:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    END = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'

def print_header(text):
    print(f"\n{Colors.BOLD}{Colors.CYAN}{'='*100}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.CYAN}{text.center(100)}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.CYAN}{'='*100}{Colors.END}\n")

def print_section(text):
    print(f"\n{Colors.BOLD}{Colors.BLUE}{'─'*100}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.BLUE}{text}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.BLUE}{'─'*100}{Colors.END}\n")

def test_rag_retrieval(query: str):
    """Test RAG retrieval với query cụ thể"""
    
    print_header("TEST RAG RETRIEVAL - CHATBOT UIT")
    
    print(f"{Colors.BOLD}Query to test:{Colors.END}")
    print(f"  {Colors.YELLOW}\"{query}\"{Colors.END}\n")
    
    # API endpoints
    ORCHESTRATOR_URL = "http://localhost:8001/api/v1/chat"
    RAG_URL = "http://localhost:8000/v1/search"
    
    print(f"{Colors.CYAN}Endpoints:{Colors.END}")
    print(f"  Orchestrator: {ORCHESTRATOR_URL}")
    print(f"  RAG Service:  {RAG_URL}\n")
    
    # Step 1: Test RAG service directly
    print_section("STEP 1: TEST RAG SERVICE DIRECTLY")
    
    try:
        rag_request = {
            "query": query,
            "top_k": 5,
            "mode": "vector"  # vector, bm25, or hybrid
        }
        
        print(f"{Colors.CYAN}Sending request to RAG service...{Colors.END}")
        print(f"Request payload: {json.dumps(rag_request, ensure_ascii=False, indent=2)}\n")

        rag_response = requests.post(RAG_URL, json=rag_request, timeout=None)

        if rag_response.status_code == 200:
            rag_data = rag_response.json()
            
            print(f"{Colors.GREEN}✅ RAG Service Response: SUCCESS{Colors.END}\n")
            
            hits = rag_data.get('hits', [])
            latency = rag_data.get('latency_ms', 0)
            total = rag_data.get('total_hits', 0)
            
            print(f"{Colors.BOLD}RAG Results:{Colors.END}")
            print(f"  Total hits: {total}")
            print(f"  Returned: {len(hits)} documents")
            print(f"  Latency: {latency:.2f} ms\n")
            
            if hits:
                print(f"{Colors.BOLD}Retrieved Documents:{Colors.END}\n")
                for i, hit in enumerate(hits, 1):
                    score = hit.get('score', 0)
                    content = hit.get('text', hit.get('content', ''))  # Try 'text' first, then 'content'
                    title = hit.get('title', 'No title')
                    meta = hit.get('meta', {})
                    
                    print(f"{Colors.YELLOW}[Document {i}]{Colors.END}")
                    print(f"  Score: {Colors.GREEN}{score:.4f}{Colors.END}")
                    print(f"  Title: {title}")
                    print(f"  Content length: {len(content)} chars")
                    print(f"  Content preview:")
                    print(f"    {Colors.CYAN}{content[:300]}...{Colors.END}")
                    
                    if meta:
                        print(f"  Doc ID: {meta.get('doc_id', 'N/A')}")
                        print(f"  Chunk ID: {meta.get('chunk_id', 'N/A')}")
                    print()
            else:
                print(f"{Colors.RED}⚠️  No documents retrieved from RAG{Colors.END}\n")
        else:
            print(f"{Colors.RED}❌ RAG Service Error: {rag_response.status_code}{Colors.END}")
            print(f"Response: {rag_response.text}\n")
            
    except Exception as e:
        print(f"{Colors.RED}❌ Error testing RAG service: {e}{Colors.END}\n")
    
    # Step 2: Test through Orchestrator with RAG enabled
    print_section("STEP 2: TEST THROUGH ORCHESTRATOR (WITH RAG)")
    
    try:
        orchestrator_request = {
            "query": query,
            "session_id": f"test-rag-{datetime.now().strftime('%Y%m%d-%H%M%S')}",
            "use_rag": True,  # Enable RAG
            "rag_top_k": 5,
            "stream": False
        }
        
        print(f"{Colors.CYAN}Sending request to Orchestrator...{Colors.END}")
        print(f"Request payload: {json.dumps(orchestrator_request, ensure_ascii=False, indent=2)}\n")
        
        orch_response = requests.post(ORCHESTRATOR_URL, json=orchestrator_request, timeout=120)
        
        if orch_response.status_code == 200:
            orch_data = orch_response.json()
            
            print(f"{Colors.GREEN}✅ Orchestrator Response: SUCCESS{Colors.END}\n")
            
            # Extract information
            response_text = orch_data.get('response', '')
            rag_context = orch_data.get('rag_context')
            processing_stats = orch_data.get('processing_stats', {})
            model_used = orch_data.get('model_used', 'Unknown')
            
            # Print processing stats
            print(f"{Colors.BOLD}Processing Statistics:{Colors.END}")
            total_time = processing_stats.get('total_time', 0)
            rag_time = processing_stats.get('rag_time')
            agent_time = processing_stats.get('agent_time')
            
            print(f"  Total time: {total_time:.2f}s" if total_time else "  Total time: N/A")
            print(f"  RAG time: {rag_time:.2f}s" if rag_time else "  RAG time: N/A")
            print(f"  Agent time: {agent_time:.2f}s" if agent_time else "  Agent time: N/A")
            print(f"  Documents retrieved: {processing_stats.get('documents_retrieved', 0)}")
            print(f"  Model used: {model_used}\n")
            
            # Check if RAG was actually used
            if rag_context:
                print(f"{Colors.GREEN}✅ RAG WAS USED!{Colors.END}\n")
                
                documents = rag_context.get('documents', [])
                search_mode = rag_context.get('search_mode', 'Unknown')
                
                print(f"{Colors.BOLD}RAG Context Details:{Colors.END}")
                print(f"  Query: {rag_context.get('query', '')}")
                print(f"  Search mode: {search_mode}")
                print(f"  Total documents: {len(documents)}\n")
                
                if documents:
                    print(f"{Colors.BOLD}Documents Retrieved by Orchestrator:{Colors.END}\n")
                    for i, doc in enumerate(documents, 1):
                        title = doc.get('title', 'No title')
                        content = doc.get('content', doc.get('text', ''))  # Try both 'content' and 'text'
                        score = doc.get('score', 0)
                        metadata = doc.get('metadata', {})
                        
                        print(f"{Colors.YELLOW}[RAG Document {i}]{Colors.END}")
                        print(f"  Score: {Colors.GREEN}{score:.4f}{Colors.END}")
                        print(f"  Title: {title}")
                        print(f"  Content length: {len(content)} chars")
                        print(f"  Content preview:")
                        print(f"    {Colors.CYAN}{content[:300]}...{Colors.END}")
                        
                        if metadata:
                            print(f"  Metadata:")
                            for key, value in metadata.items():
                                print(f"    - {key}: {value}")
                        print()
                else:
                    print(f"{Colors.YELLOW}⚠️  RAG context exists but no documents{Colors.END}\n")
            else:
                print(f"{Colors.RED}❌ RAG WAS NOT USED (rag_context is None){Colors.END}\n")
            
            # Print agent response
            print(f"{Colors.BOLD}Agent Response:{Colors.END}")
            print(f"{Colors.GREEN}{'─'*100}{Colors.END}")
            print(response_text)
            print(f"{Colors.GREEN}{'─'*100}{Colors.END}\n")
            
            # Analysis
            print_section("ANALYSIS")
            
            # Check if response uses context
            if rag_context and documents:
                print(f"{Colors.GREEN}✅ RAG retrieval: SUCCESSFUL{Colors.END}")
                print(f"   - Retrieved {len(documents)} documents")
                print(f"   - Average score: {sum(d.get('score', 0) for d in documents) / len(documents):.4f}")
                
                # Check if agent seems to use the context
                keywords = ['công nghệ thông tin', 'đào tạo', 'mạng', 'ứng dụng', 'tổ chức']
                used_keywords = [kw for kw in keywords if kw.lower() in response_text.lower()]
                
                if used_keywords:
                    print(f"{Colors.GREEN}✅ Agent appears to use context{Colors.END}")
                    print(f"   - Found keywords: {', '.join(used_keywords)}")
                else:
                    print(f"{Colors.YELLOW}⚠️  Hard to determine if agent used context{Colors.END}")
                
                # Check response length
                if len(response_text) > 100:
                    print(f"{Colors.GREEN}✅ Response is detailed ({len(response_text)} chars){Colors.END}")
                else:
                    print(f"{Colors.YELLOW}⚠️  Response might be too short{Colors.END}")
            else:
                print(f"{Colors.RED}❌ RAG retrieval: FAILED or NOT USED{Colors.END}")
                print(f"   - No documents were retrieved or used")
            
        else:
            print(f"{Colors.RED}❌ Orchestrator Error: {orch_response.status_code}{Colors.END}")
            print(f"Response: {orch_response.text}\n")
            
    except Exception as e:
        print(f"{Colors.RED}❌ Error testing orchestrator: {e}{Colors.END}\n")
        import traceback
        traceback.print_exc()
    
    # Final summary
    print_section("TEST COMPLETE")
    print(f"{Colors.BOLD}Timestamp:{Colors.END} {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

if __name__ == "__main__":
    # Test query
    test_query = "Sinh viên chương trình chuẩn được làm khóa luận tốt nghiệp khi thỏa các yêu cầu nào"
    
    test_rag_retrieval(test_query)
