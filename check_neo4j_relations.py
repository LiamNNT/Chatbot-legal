from neo4j import GraphDatabase

driver = GraphDatabase.driver('bolt://localhost:7687', auth=('neo4j', 'uitchatbot'))

with driver.session() as session:
    # Xem tất cả properties của Article node
    result = session.run('''
        MATCH (a:Article)
        RETURN keys(a) as props
        LIMIT 1
    ''')
    print('=== Article Properties ===')
    for r in result:
        print(r['props'])

    # Xem chi tiết AMENDS với tất cả properties
    result2 = session.run('''
        MATCH (a)-[r:AMENDS]->(b) 
        RETURN a.article_number as from_num, a.title as from_title, a.full_text as from_text,
               b.article_number as to_num, b.title as to_title,
               r.description as description
        LIMIT 5
    ''')
    print('\n=== AMENDS Details ===')
    for r in result2:
        print(f"\nFrom: Điều {r['from_num']} - {r['from_title']}")
        print(f"To: Điều {r['to_num']} - {r['to_title']}")
        print(f"Description: {r['description']}")
        if r['from_text']:
            print(f"Content preview: {r['from_text'][:200]}...")

driver.close()
