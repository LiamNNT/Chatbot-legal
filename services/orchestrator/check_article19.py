#!/usr/bin/env python3
"""Check Article 19 in Neo4j"""
from neo4j import GraphDatabase

driver = GraphDatabase.driver('bolt://localhost:7687', auth=('neo4j', 'uitchatbot'))
session = driver.session()

result = session.run('MATCH (a:Article {id: "dieu_19"}) RETURN a.title, a.full_text')
record = result.single()

if record:
    print('Title:', record['a.title'])
    print('\nFull text:')
    print(record['a.full_text'])
else:
    print('Article 19 not found')

session.close()
driver.close()
