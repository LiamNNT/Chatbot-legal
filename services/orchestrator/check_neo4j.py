#!/usr/bin/env python3
"""
Check Neo4j database - xem có dữ liệu Article không
"""
import sys
import os
from pathlib import Path

# Add orchestrator to path
sys.path.insert(0, str(Path(__file__).parent))

# Load environment
try:
    from dotenv import load_dotenv
    env_path = Path(__file__).parent / '.env'
    load_dotenv(env_path)
except:
    pass

# Import Neo4j
try:
    from neo4j import GraphDatabase
except ImportError:
    print("❌ neo4j module not installed!")
    print("Run: pip install neo4j")
    sys.exit(1)


def check_neo4j():
    """Check Neo4j database content"""
    
    print("=" * 80)
    print("CHECKING NEO4J DATABASE")
    print("=" * 80)
    
    # Get Neo4j credentials from environment
    uri = os.getenv("NEO4J_URI", "bolt://localhost:7687")
    username = os.getenv("NEO4J_USER", "neo4j")
    password = os.getenv("NEO4J_PASSWORD", "uitchatbot")
    
    print(f"\n📍 Connecting to: {uri}")
    print(f"👤 Username: {username}")
    
    try:
        driver = GraphDatabase.driver(uri, auth=(username, password))
        
        with driver.session() as session:
            # Check database connection
            result = session.run("RETURN 1 as test")
            if result.single():
                print("✅ Connected to Neo4j successfully!")
            
            # Count all nodes
            print("\n" + "=" * 80)
            print("DATABASE STATISTICS")
            print("=" * 80)
            
            result = session.run("MATCH (n) RETURN count(n) as total")
            total_nodes = result.single()["total"]
            print(f"\n📊 Total nodes: {total_nodes}")
            
            # Count nodes by label
            print("\n📋 Nodes by label:")
            result = session.run("""
                MATCH (n)
                RETURN labels(n)[0] as label, count(n) as count
                ORDER BY count DESC
            """)
            for record in result:
                label = record["label"] or "No Label"
                count = record["count"]
                print(f"   - {label}: {count}")
            
            # Check Article nodes specifically
            print("\n" + "=" * 80)
            print("ARTICLE NODES CHECK")
            print("=" * 80)
            
            result = session.run("MATCH (a:Article) RETURN count(a) as count")
            article_count = result.single()["count"]
            print(f"\n📄 Total Article nodes: {article_count}")
            
            if article_count > 0:
                # Get sample Article node
                print("\n🔍 Sample Article nodes:")
                result = session.run("""
                    MATCH (a:Article)
                    RETURN a
                    LIMIT 3
                """)
                
                for idx, record in enumerate(result, 1):
                    node = record["a"]
                    print(f"\n  [{idx}] Article Node:")
                    print(f"      Properties: {list(node.keys())}")
                    for key in node.keys():
                        value = node[key]
                        if isinstance(value, str) and len(value) > 100:
                            print(f"      - {key}: {value[:100]}...")
                        else:
                            print(f"      - {key}: {value}")
                
                # Check what properties actually exist
                print("\n📋 Properties found in Article nodes:")
                result = session.run("""
                    MATCH (a:Article)
                    UNWIND keys(a) as key
                    RETURN DISTINCT key
                    ORDER BY key
                """)
                properties = [record["key"] for record in result]
                for prop in properties:
                    print(f"   - {prop}")
                
            else:
                print("⚠️  No Article nodes found!")
                print("\nℹ️  You need to import Article data into Neo4j.")
                print("   Check if you have a script to import quy chế data.")
            
            # Check indexes
            print("\n" + "=" * 80)
            print("INDEXES CHECK")
            print("=" * 80)
            
            result = session.run("SHOW INDEXES")
            indexes = list(result)
            if indexes:
                print(f"\n📑 Found {len(indexes)} indexes:")
                for idx, record in enumerate(indexes, 1):
                    print(f"   [{idx}] {dict(record)}")
            else:
                print("\n⚠️  No indexes found!")
            
            # Count relationships
            print("\n" + "=" * 80)
            print("RELATIONSHIPS CHECK")
            print("=" * 80)
            
            result = session.run("MATCH ()-[r]->() RETURN count(r) as total")
            total_rels = result.single()["total"]
            print(f"\n🔗 Total relationships: {total_rels}")
            
            if total_rels > 0:
                result = session.run("""
                    MATCH ()-[r]->()
                    RETURN type(r) as type, count(r) as count
                    ORDER BY count DESC
                """)
                print("\n📋 Relationships by type:")
                for record in result:
                    print(f"   - {record['type']}: {record['count']}")
            
        driver.close()
        print("\n" + "=" * 80)
        print("CHECK COMPLETED")
        print("=" * 80)
        
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        
        print("\n💡 Common issues:")
        print("   1. Neo4j is not running")
        print("   2. Wrong credentials in .env file")
        print("   3. Wrong URI/port")


if __name__ == "__main__":
    print("\n🚀 Starting Neo4j Database Check\n")
    check_neo4j()
