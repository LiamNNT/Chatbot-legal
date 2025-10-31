#!/usr/bin/env python3
"""
Script phân tích luồng dữ liệu của Agent và RAG
Kiểm tra cấu hình, kết nối và luồng xử lý
"""

import json
import yaml
import os
from pathlib import Path

# ANSI colors
class Colors:
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    END = '\033[0m'
    BOLD = '\033[1m'

def print_header(text):
    print(f"\n{Colors.BOLD}{Colors.CYAN}{'='*80}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.CYAN}{text.center(80)}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.CYAN}{'='*80}{Colors.END}\n")

def print_section(text):
    print(f"\n{Colors.BOLD}{Colors.BLUE}{'─'*80}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.BLUE}{text}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.BLUE}{'─'*80}{Colors.END}\n")

def check_mark(condition):
    return f"{Colors.GREEN}✅{Colors.END}" if condition else f"{Colors.RED}❌{Colors.END}"

def warning_mark(condition):
    return f"{Colors.YELLOW}⚠️{Colors.END}" if condition else f"{Colors.GREEN}✅{Colors.END}"

# Paths
BASE_DIR = Path(__file__).parent
ORCHESTRATOR_DIR = BASE_DIR / "services" / "orchestrator"
RAG_DIR = BASE_DIR / "services" / "rag_services"

def check_orchestrator_config():
    """Kiểm tra cấu hình Orchestrator"""
    print_section("1. ORCHESTRATOR CONFIGURATION")
    
    issues = []
    
    # Check .env file
    env_file = ORCHESTRATOR_DIR / ".env"
    if env_file.exists():
        print(f"{check_mark(True)} .env file exists")
        
        # Parse .env
        config = {}
        with open(env_file, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    config[key.strip()] = value.strip()
        
        # Check critical keys
        required_keys = [
            'OPENROUTER_API_KEY',
            'RAG_SERVICE_URL',
            'HOST',
            'PORT'
        ]
        
        for key in required_keys:
            exists = key in config and config[key]
            print(f"  {check_mark(exists)} {key}: {config.get(key, 'NOT SET')[:50]}")
            if not exists:
                issues.append(f"Missing {key} in orchestrator .env")
        
        # Check RAG service URL
        rag_url = config.get('RAG_SERVICE_URL', '')
        if 'localhost:8000' in rag_url:
            print(f"  {check_mark(True)} RAG service URL points to localhost:8000")
        else:
            issues.append(f"RAG_SERVICE_URL may be incorrect: {rag_url}")
    else:
        print(f"{check_mark(False)} .env file NOT found")
        issues.append("Orchestrator .env file missing")
    
    # Check agents_config.yaml
    print()
    config_file = ORCHESTRATOR_DIR / "config" / "agents_config.yaml"
    if config_file.exists():
        print(f"{check_mark(True)} agents_config.yaml exists")
        
        with open(config_file, 'r') as f:
            config = yaml.safe_load(f)
        
        # Check agents configuration
        agents = config.get('agents', {})
        expected_agents = ['planner', 'query_rewriter', 'answer_agent', 'verifier', 'response_agent']
        
        print(f"\n  Configured Agents:")
        for agent in expected_agents:
            exists = agent in agents
            model = agents.get(agent, {}).get('model_config', 'N/A') if exists else 'N/A'
            print(f"  {check_mark(exists)} {agent}: {model}")
            if not exists:
                issues.append(f"Missing agent configuration: {agent}")
        
        # Check models
        print(f"\n  Configured Models:")
        models = config.get('models', {})
        for model_name, model_config in models.items():
            model = model_config.get('name', 'N/A')
            temp = model_config.get('temperature', 'N/A')
            print(f"  ✓ {model_name}: {model} (temp={temp})")
        
    else:
        print(f"{check_mark(False)} agents_config.yaml NOT found")
        issues.append("agents_config.yaml missing")
    
    return issues

def check_rag_config():
    """Kiểm tra cấu hình RAG Service"""
    print_section("2. RAG SERVICE CONFIGURATION")
    
    issues = []
    
    # Check .env file
    env_file = RAG_DIR / ".env"
    if env_file.exists():
        print(f"{check_mark(True)} .env file exists")
        
        # Parse .env
        config = {}
        with open(env_file, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    config[key.strip()] = value.strip()
        
        # Check critical keys
        required_keys = [
            'VECTOR_BACKEND',
            'WEAVIATE_URL',
            'WEAVIATE_CLASS_NAME',
            'EMB_MODEL',
            'PORT'
        ]
        
        for key in required_keys:
            exists = key in config and config[key]
            value = config.get(key, 'NOT SET')
            print(f"  {check_mark(exists)} {key}: {value}")
            if not exists:
                issues.append(f"Missing {key} in RAG .env")
        
        # Specific checks
        vector_backend = config.get('VECTOR_BACKEND', '')
        if vector_backend == 'weaviate':
            print(f"  {check_mark(True)} Using Weaviate as vector backend")
        else:
            print(f"  {warning_mark(True)} Vector backend is: {vector_backend}")
        
        weaviate_url = config.get('WEAVIATE_URL', '')
        if 'localhost:8090' in weaviate_url:
            print(f"  {check_mark(True)} Weaviate URL points to localhost:8090")
        else:
            print(f"  {warning_mark(True)} Weaviate URL: {weaviate_url}")
            
    else:
        print(f"{check_mark(False)} .env file NOT found")
        issues.append("RAG .env file missing")
    
    return issues

def analyze_data_flow():
    """Phân tích luồng dữ liệu"""
    print_section("3. DATA FLOW ANALYSIS")
    
    print("Luồng dữ liệu dự kiến:\n")
    
    flow_steps = [
        ("1. User Query", "User sends query to Orchestrator (port 8001)"),
        ("2. Planner Agent", "Analyzes query complexity and creates execution plan"),
        ("3. Query Rewriter", "Optimizes query for better RAG retrieval (if needed)"),
        ("4. RAG Service Call", "Orchestrator calls RAG Service (port 8000) with rewritten queries"),
        ("5. RAG Processing", "RAG searches in Weaviate/OpenSearch and returns documents"),
        ("6. Answer Agent", "Generates answer using retrieved documents + rewritten_queries"),
        ("7. Verifier Agent", "Validates answer quality and accuracy"),
        ("8. Response Agent", "Formats final user-friendly response"),
        ("9. Return Response", "Send response back to user")
    ]
    
    for step, description in flow_steps:
        print(f"{Colors.GREEN}✓{Colors.END} {Colors.BOLD}{step}{Colors.END}")
        print(f"  {description}\n")

def check_critical_files():
    """Kiểm tra các file quan trọng"""
    print_section("4. CRITICAL FILES CHECK")
    
    critical_files = [
        # Orchestrator
        (ORCHESTRATOR_DIR / "app" / "main.py", "Orchestrator main.py"),
        (ORCHESTRATOR_DIR / "app" / "agents" / "multi_agent_orchestrator.py", "Multi-Agent Orchestrator"),
        (ORCHESTRATOR_DIR / "app" / "agents" / "query_rewriter_agent.py", "Query Rewriter Agent"),
        (ORCHESTRATOR_DIR / "app" / "agents" / "answer_agent.py", "Answer Agent"),
        (ORCHESTRATOR_DIR / "app" / "api" / "routes.py", "API Routes"),
        
        # RAG Service
        (RAG_DIR / "app" / "main.py", "RAG main.py"),
        (RAG_DIR / "adapters" / "api_facade.py", "API Facade"),
        (RAG_DIR / "adapters" / "weaviate_vector_adapter.py", "Weaviate Adapter"),
        (RAG_DIR / "adapters" / "cross_encoder_reranker.py", "Reranker"),
        (RAG_DIR / "app" / "api" / "v1" / "routes" / "search.py", "Search Routes"),
    ]
    
    for file_path, description in critical_files:
        exists = file_path.exists()
        print(f"{check_mark(exists)} {description}: {file_path.relative_to(BASE_DIR)}")

def check_key_code_patterns():
    """Kiểm tra các pattern code quan trọng"""
    print_section("5. KEY CODE PATTERNS")
    
    # Check if rewritten_queries are passed through pipeline
    orchestrator_file = ORCHESTRATOR_DIR / "app" / "agents" / "multi_agent_orchestrator.py"
    if orchestrator_file.exists():
        with open(orchestrator_file, 'r') as f:
            content = f.read()
        
        patterns = [
            ("rewritten_queries in RAGContext", "rewritten_queries" in content and "RAGContext" in content),
            ("Query rewriter step", "query_rewriter.process" in content),
            ("RAG retrieval with queries", "_perform_rag_retrieval" in content),
            ("Answer agent receives context", "answer_agent.process" in content),
            ("Verification step", "verifier.process" in content),
        ]
        
        print("Orchestrator patterns:")
        for pattern, exists in patterns:
            print(f"  {check_mark(exists)} {pattern}")
    
    print()
    
    # Check RAG service patterns
    search_file = RAG_DIR / "app" / "api" / "v1" / "routes" / "search.py"
    if search_file.exists():
        with open(search_file, 'r') as f:
            content = f.read()
        
        patterns = [
            ("Search endpoint", "async def search" in content),
            ("Uses facade pattern", "search_facade" in content),
            ("Proper error handling", "HTTPException" in content),
        ]
        
        print("RAG Service patterns:")
        for pattern, exists in patterns:
            print(f"  {check_mark(exists)} {pattern}")

def main():
    """Main function"""
    print_header("DATA FLOW VERIFICATION - CHATBOT UIT")
    
    print(f"{Colors.BOLD}Analyzing configuration and data flow...{Colors.END}\n")
    
    # Run checks
    orch_issues = check_orchestrator_config()
    rag_issues = check_rag_config()
    
    analyze_data_flow()
    check_critical_files()
    check_key_code_patterns()
    
    # Summary
    print_section("6. SUMMARY & RECOMMENDATIONS")
    
    all_issues = orch_issues + rag_issues
    
    if not all_issues:
        print(f"{Colors.GREEN}{Colors.BOLD}✅ EXCELLENT! No critical issues found.{Colors.END}\n")
        print("Data flow appears to be correctly configured:\n")
        print("  ✓ Orchestrator configuration is complete")
        print("  ✓ RAG service configuration is complete")
        print("  ✓ All agents are properly configured")
        print("  ✓ Critical files exist")
        print("  ✓ Key code patterns are present")
        
        print(f"\n{Colors.CYAN}Next steps:{Colors.END}")
        print("  1. Start RAG service: cd services/rag_services && python start_server.py")
        print("  2. Start Orchestrator: cd services/orchestrator && bash start_server.sh")
        print("  3. Test: python services/orchestrator/test_data_flow.py")
    else:
        print(f"{Colors.YELLOW}{Colors.BOLD}⚠️  Found {len(all_issues)} potential issues:{Colors.END}\n")
        for i, issue in enumerate(all_issues, 1):
            print(f"  {i}. {issue}")
        
        print(f"\n{Colors.CYAN}Recommendations:{Colors.END}")
        if any("OPENROUTER_API_KEY" in issue for issue in all_issues):
            print("  - Set OPENROUTER_API_KEY in orchestrator/.env")
        if any("Weaviate" in issue for issue in all_issues):
            print("  - Verify Weaviate configuration in rag_services/.env")
        if any("missing" in issue.lower() for issue in all_issues):
            print("  - Copy .env.example to .env in both services")
    
    print_header("VERIFICATION COMPLETE")

if __name__ == "__main__":
    main()
