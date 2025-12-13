"""Check Điều 14 content and why it's not being found."""
from neo4j import GraphDatabase

uri = "bolt://localhost:7687"
username = "neo4j"
password = "uitchatbot"

driver = GraphDatabase.driver(uri, auth=(username, password))

print("="*70)
print("CHECKING Điều 14 CONTENT")
print("="*70)

with driver.session() as session:
    # Get Điều 14 original content
    result = session.run("""
        MATCH (a:Article)
        WHERE a.title CONTAINS 'Điều 14'
        RETURN a.title, a.full_text
    """)
    
    for record in result:
        title = record["a.title"]
        text = record["a.full_text"] or ""
        
        print(f"\n--- {title} ---")
        print(f"Full text length: {len(text)} chars")
        print(f"Contains 'học kỳ hè': {'học kỳ hè' in text.lower()}")
        print(f"Contains 'đăng ký': {'đăng ký' in text.lower()}")
        print("\nFirst 800 chars of text:")
        print(text[:800])

driver.close()
