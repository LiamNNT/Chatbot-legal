"""Debug why Điều 14 is not in search results."""
from neo4j import GraphDatabase

uri = "bolt://localhost:7687"
username = "neo4j"
password = "uitchatbot"

driver = GraphDatabase.driver(uri, auth=(username, password))

keywords = ["học kỳ hè", "đăng ký"]

print("="*70)
print(f"SEARCHING with keywords: {keywords}")
print("="*70)

with driver.session() as session:
    # Count how many articles match
    result = session.run("""
        MATCH (a:Article)
        WHERE any(kw IN $keywords WHERE 
            toLower(a.full_text) CONTAINS toLower(kw) OR
            toLower(a.title) CONTAINS toLower(kw)
        )
        RETURN a.title as title, 
               a.id as id,
               SIZE(a.full_text) as text_length
        ORDER BY a.id
    """, keywords=keywords)
    
    articles = list(result)
    
    print(f"\nTotal matching articles: {len(articles)}")
    print("\nAll matching articles:")
    for i, r in enumerate(articles):
        title = r["title"]
        is_14 = "Điều 14" in title
        marker = "  <<<< THIS IS ĐIỀU 14!" if is_14 else ""
        print(f"  {i+1}. {title}{marker}")
    
    # Check if Điều 14 is in there
    has_14 = any("Điều 14" in r["title"] for r in articles)
    print(f"\nĐiều 14 found in results: {has_14}")

driver.close()
