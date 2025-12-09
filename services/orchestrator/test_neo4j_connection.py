#!/usr/bin/env python3
"""Test Neo4j connection and Graph Adapter"""
import sys
import os
from pathlib import Path

# Add rag_services to path
orchestrator_path = Path(__file__).parent
rag_services_path = orchestrator_path.parent / "rag_services"
sys.path.insert(0, str(rag_services_path))

print(f"🔍 RAG Services Path: {rag_services_path}")
print(f"🔍 Path exists: {rag_services_path.exists()}")

try:
    from adapters.graph.neo4j_adapter import Neo4jGraphAdapter
    print("✅ Neo4jGraphAdapter imported successfully")
    
    # Try to connect
    neo4j_uri = os.getenv("NEO4J_URI", "bolt://localhost:7687")
    neo4j_user = os.getenv("NEO4J_USER", "neo4j")
    neo4j_password = os.getenv("NEO4J_PASSWORD", "uitchatbot")
    neo4j_database = os.getenv("NEO4J_DATABASE", "neo4j")
    
    print(f"\n🔗 Connecting to: {neo4j_uri}")
    print(f"   User: {neo4j_user}")
    print(f"   Database: {neo4j_database}")
    
    adapter = Neo4jGraphAdapter(
        uri=neo4j_uri,
        username=neo4j_user,
        password=neo4j_password,
        database=neo4j_database
    )
    
    print("✅ Neo4j connection successful!")
    print(f"   Adapter: {adapter}")
    
except ImportError as e:
    print(f"❌ Import Error: {e}")
    print(f"\n🔍 sys.path:")
    for p in sys.path[:10]:
        print(f"   - {p}")
except Exception as e:
    print(f"❌ Connection Error: {e}")
    import traceback
    traceback.print_exc()
