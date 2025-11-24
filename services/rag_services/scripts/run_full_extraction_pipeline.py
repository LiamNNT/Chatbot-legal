#!/usr/bin/env python3
"""
🚀 COMPLETE 3-TIER KNOWLEDGE GRAPH EXTRACTION PIPELINE
=======================================================

This pipeline runs all necessary steps in order:

1. ✅ Clear Neo4j (optional - fresh start)
2. 📊 Build Graph Structure (Chapter -> Article -> relationships)
3. 🔗 Create Cross-References (theo Điều X, căn cứ Điều Y)
4. 🧠 LLM Extraction (Tier 2: Entities, Tier 3: Rules)
5. 📈 Verify Results

Usage:
    python scripts/run_full_extraction_pipeline.py [--clear]
    
    --clear: Clear Neo4j database before starting (default: False)
"""

import sys
import os
import argparse
import subprocess
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from neo4j import GraphDatabase

NEO4J_URI = "bolt://localhost:7687"
NEO4J_USER = "neo4j"
NEO4J_PASSWORD = "uitchatbot"


def print_header(title: str):
    """Print formatted section header"""
    print("\n" + "="*80)
    print(f"🚀 {title}")
    print("="*80 + "\n")


def run_script(script_name: str, description: str) -> bool:
    """
    Run a Python script and check if it succeeded.
    
    Args:
        script_name: Name of script file
        description: Description for logging
        
    Returns:
        True if successful
    """
    script_path = Path(__file__).parent / script_name
    
    if not script_path.exists():
        print(f"❌ Script not found: {script_path}")
        return False
    
    print(f"▶️  Running: {description}")
    print(f"   Script: {script_name}")
    
    try:
        result = subprocess.run(
            [sys.executable, str(script_path)],
            check=True,
            capture_output=True,
            text=True
        )
        print(f"✅ {description} completed successfully")
        return True
        
    except subprocess.CalledProcessError as e:
        print(f"❌ {description} failed!")
        print(f"   Error: {e.stderr}")
        return False


def clear_neo4j():
    """Clear Neo4j database"""
    print_header("STEP 0: Clear Neo4j Database")
    
    response = input("⚠️  Delete ALL existing data in Neo4j? (yes/no): ")
    if response.lower() != 'yes':
        print("Skipping clear step...")
        return True
    
    driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
    
    try:
        with driver.session() as session:
            result = session.run("MATCH (n) RETURN count(n) as count")
            total = result.single()["count"]
            print(f"   Current nodes: {total}")
            
            if total > 0:
                print("   Deleting all nodes and relationships...")
                session.run("MATCH (n) DETACH DELETE n")
                print(f"✅ Deleted {total} nodes")
            else:
                print("✅ Database already empty")
                
        return True
        
    except Exception as e:
        print(f"❌ Error clearing Neo4j: {e}")
        return False
        
    finally:
        driver.close()


def verify_neo4j():
    """Verify Neo4j database status"""
    print_header("VERIFICATION: Neo4j Knowledge Graph")
    
    driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
    
    try:
        with driver.session() as session:
            # Count nodes by type
            print("📊 Node Counts:")
            
            result = session.run("MATCH (n:Article) RETURN count(n) as count")
            articles = result.single()["count"]
            print(f"   Articles: {articles}")
            
            result = session.run("MATCH (n:Entity) RETURN count(n) as count")
            entities = result.single()["count"]
            print(f"   Entities: {entities}")
            
            result = session.run("MATCH (n:Rule) RETURN count(n) as count")
            rules = result.single()["count"]
            print(f"   Rules: {rules}")
            
            result = session.run("MATCH (n:Chapter) RETURN count(n) as count")
            chapters = result.single()["count"]
            print(f"   Chapters: {chapters}")
            
            # Count relationships
            print("\n🔗 Relationship Counts:")
            
            result = session.run("MATCH ()-[r:MENTIONS]->() RETURN count(r) as count")
            mentions = result.single()["count"]
            print(f"   MENTIONS: {mentions}")
            
            result = session.run("MATCH ()-[r:DEFINES_RULE]->() RETURN count(r) as count")
            defines = result.single()["count"]
            print(f"   DEFINES_RULE: {defines}")
            
            result = session.run("MATCH ()-[r:REFERENCES]->() RETURN count(r) as count")
            refs = result.single()["count"]
            print(f"   REFERENCES: {refs}")
            
            result = session.run("MATCH ()-[r:HAS_ARTICLE]->() RETURN count(r) as count")
            has_article = result.single()["count"]
            print(f"   HAS_ARTICLE: {has_article}")
            
            result = session.run("MATCH ()-[r:NEXT_ARTICLE]->() RETURN count(r) as count")
            next_art = result.single()["count"]
            print(f"   NEXT_ARTICLE: {next_art}")
            
            # Success criteria
            print("\n✅ Success Criteria:")
            success = True
            
            if articles < 50:
                print(f"   ⚠️  Low article count: {articles} (expected 80+)")
                success = False
            else:
                print(f"   ✓ Articles: {articles}")
            
            if entities < 30:
                print(f"   ⚠️  Low entity count: {entities} (expected 40+)")
                success = False
            else:
                print(f"   ✓ Entities: {entities}")
            
            if rules < 50:
                print(f"   ⚠️  Low rule count: {rules} (expected 80+)")
                success = False
            else:
                print(f"   ✓ Rules: {rules}")
            
            if refs == 0:
                print(f"   ⚠️  No cross-references found")
                success = False
            else:
                print(f"   ✓ Cross-references: {refs}")
            
            return success
            
    except Exception as e:
        print(f"❌ Error verifying Neo4j: {e}")
        return False
        
    finally:
        driver.close()


def main():
    """Run the complete extraction pipeline"""
    parser = argparse.ArgumentParser(description='Run complete 3-tier extraction pipeline')
    parser.add_argument('--clear', action='store_true', help='Clear Neo4j before starting')
    args = parser.parse_args()
    
    print("="*80)
    print("🚀 3-TIER KNOWLEDGE GRAPH EXTRACTION PIPELINE")
    print("="*80)
    print("\nThis will run:")
    print("  1. Build graph structure (Chapter -> Article)")
    print("  2. Create cross-references (theo Điều X)")
    print("  3. LLM extraction (Entities & Rules)")
    print("  4. Verify results")
    print()
    
    # Step 0: Clear Neo4j (optional)
    if args.clear:
        if not clear_neo4j():
            print("\n❌ Pipeline failed at: Clear Neo4j")
            return 1
    
    # Step 1: Build Graph Structure
    print_header("STEP 1: Build Graph Structure")
    if not run_script("build_graph_from_indexed_data.py", "Graph structure building"):
        print("\n❌ Pipeline failed at: Build graph structure")
        return 1
    
    # Step 2: Create Cross-References
    print_header("STEP 2: Create Cross-References")
    if not run_script("create_cross_references.py", "Cross-reference extraction"):
        print("\n⚠️  Cross-reference step failed, but continuing...")
        # Don't fail pipeline if this step fails
    
    # Step 3: LLM Extraction
    print_header("STEP 3: LLM Extraction (Entities & Rules)")
    print("⚠️  This step may take 5-10 minutes and cost ~$0.10")
    print("   Using: Grok 4.1 Fast (Tier 2 & 3)")
    
    response = input("\nProceed with LLM extraction? (yes/no): ")
    if response.lower() == 'yes':
        if not run_script("build_neo4j_with_llm.py", "LLM entity & rule extraction"):
            print("\n❌ Pipeline failed at: LLM extraction")
            return 1
    else:
        print("⏭️  Skipping LLM extraction")
    
    # Step 4: Verify
    success = verify_neo4j()
    
    # Final summary
    print("\n" + "="*80)
    if success:
        print("✅ PIPELINE COMPLETED SUCCESSFULLY!")
        print("="*80)
        print("\n📊 Next steps:")
        print("   1. View graph: http://localhost:7474")
        print("   2. Run queries:")
        print("      MATCH (n) RETURN n LIMIT 100")
        print("      MATCH (a:Article)-[r]->(e:Entity) RETURN a, r, e LIMIT 25")
        print("   3. Test RAG system with knowledge graph")
    else:
        print("⚠️  PIPELINE COMPLETED WITH WARNINGS")
        print("="*80)
        print("\nSome metrics are below expected values.")
        print("Check the verification output above for details.")
    
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
