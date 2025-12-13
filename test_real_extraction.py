"""Test extraction with REAL Neo4j data."""
from neo4j import GraphDatabase
import re

uri = "bolt://localhost:7687"
username = "neo4j"
password = "uitchatbot"

def extract_amendment_section(amending_text: str, original_title: str) -> str:
    """Extract the specific amendment section for an article."""
    
    if not amending_text or not original_title:
        return None
        
    # Extract the article number from title
    article_match = re.search(r'Điều\s*(\d+)', original_title, re.IGNORECASE)
    if not article_match:
        return None
        
    article_number = article_match.group(1)
    
    # Pattern to find section markers
    section_pattern = rf'---[^-]*Điều\s*{article_number}\s*---\s*(.*?)(?=---|\Z)'
    
    match = re.search(section_pattern, amending_text, re.DOTALL | re.IGNORECASE)
    
    if match:
        extracted = match.group(1).strip()
        if extracted:
            return extracted
    
    return None

driver = GraphDatabase.driver(uri, auth=(username, password))

print("="*70)
print("TESTING WITH REAL NEO4J DATA")
print("="*70)

# Get Điều 1's full text and see what articles it amends
with driver.session() as session:
    # Get Điều 1 content
    result = session.run("""
        MATCH (d1:Article)-[r:AMENDS]->(target:Article)
        WHERE d1.title CONTAINS 'Điều 1'
        RETURN d1.title as amending_title,
               d1.full_text as amending_text,
               target.title as target_title,
               r.description as desc
    """)
    
    dieu_1_text = None
    amendments = []
    
    for record in result:
        dieu_1_text = record["amending_text"]
        amendments.append({
            "target": record["target_title"],
            "desc": record["desc"]
        })
    
    print(f"\nĐiều 1 amends {len(amendments)} articles:")
    for a in amendments:
        print(f"  - {a['target']}: {a['desc']}")
    
    print("\n" + "="*70)
    print("TESTING EXTRACTION FOR EACH AMENDED ARTICLE:")
    print("="*70)
    
    for a in amendments:
        target_title = a["target"]
        print(f"\n--- {target_title} ---")
        
        extracted = extract_amendment_section(dieu_1_text, target_title)
        
        if extracted:
            print(f"✓ EXTRACTED ({len(extracted)} chars):")
            print("-" * 40)
            # Show first 300 chars
            print(extracted[:300] + "..." if len(extracted) > 300 else extracted)
        else:
            print("✗ Could NOT extract specific section")
            print("Looking for pattern in text...")
            
            # Try to find any mention
            if target_title:
                article_match = re.search(r'Điều\s*(\d+)', target_title)
                if article_match:
                    num = article_match.group(1)
                    pattern = rf'Điều\s*{num}'
                    if re.search(pattern, dieu_1_text or "", re.IGNORECASE):
                        print(f"  Found 'Điều {num}' in text but couldn't extract section")
                    else:
                        print(f"  'Điều {num}' NOT found in amending text")

driver.close()
print("\n" + "="*70)
print("DONE")
