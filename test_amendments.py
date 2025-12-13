"""Test search_with_amendments method"""
import asyncio
import sys
import os

# Add rag_services to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'services', 'rag_services'))

from neo4j import GraphDatabase

def check_dieu_1_structure():
    driver = GraphDatabase.driver('bolt://localhost:7687', auth=('neo4j', 'uitchatbot'))
    
    with driver.session() as session:
        # Check Điều 1 content
        print("=== Điều 1 (văn bản sửa đổi) ===")
        result = session.run('''
            MATCH (a:Article)
            WHERE a.title = "Điều 1"
            RETURN a.title, a.full_text
        ''')
        for r in result:
            print(f"Title: {r['a.title']}")
            text = r['a.full_text'] or ""
            print(f"Full text:\n{text[:2000]}...")
            print(f"\n=== Tìm 'Điều 14' trong text ===")
            if "Điều 14" in text:
                # Find the section about Điều 14
                idx = text.find("Điều 14")
                print(f"Found at position {idx}")
                print(f"Context: ...{text[idx:idx+500]}...")
    
    driver.close()

if __name__ == "__main__":
    check_dieu_1_structure()
