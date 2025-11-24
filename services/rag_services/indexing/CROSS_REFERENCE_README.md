# Cross-Reference Detector - Quick Start

Automatically detect and link cross-references in legal documents.

## 🚀 Quick Start

### Option 1: Interactive CLI

```bash
cd services/rag_services
python indexing/cross_reference_detector.py
```

Output:
```
🔍 DRY RUN: Detecting cross-references...
📊 Detection Results:
   Articles scanned: 34
   Clauses scanned: 70
   Cross-references found: 33

❓ Create 33 REFERENCES relationships? (yes/no): yes

✅ COMPLETE!
   Relationships created: 29
   Failed: 4
```

### Option 2: Programmatic

```python
from indexing.cross_reference_detector import CrossReferenceDetector

detector = CrossReferenceDetector()

# Process document
stats = detector.process_document("QD_790_2022")
print(f"Created {stats['relationships_created']} links")

# Get statistics
top_refs = detector.find_most_referenced_articles(limit=10)
for article in top_refs:
    print(f"Article {article['article_no']}: {article['reference_count']} refs")

detector.close()
```

## 📊 Results on QĐ 790/2022

- **Scanned**: 34 Articles + 70 Clauses
- **Detected**: 33 cross-references
- **Created**: 29 REFERENCES relationships
- **Performance**: ~2 seconds

**Most Referenced Articles**:
1. Article 6 (Khoá học): **17 references**
2. Article 16 (Buộc thôi học): 5 references
3. Article 21 (Đánh giá kết quả): 2 references

## 🔍 Query Examples

### Find what Article 16 references:
```cypher
MATCH (a:Article {article_no: 16})-[r:REFERENCES]->(target)
RETURN target.article_no, target.title_vi, r.reference_text
```

### Find who references Article 6:
```cypher
MATCH (source)-[:REFERENCES]->(a:Article {article_no: 6})
RETURN source.article_no, source.title_vi, count(*) as ref_count
ORDER BY ref_count DESC
```

### Find citation chains (A → B → C):
```cypher
MATCH path = (a:Article)-[:REFERENCES*1..3]->(target)
WHERE a.article_no = 18
RETURN [n in nodes(path) | n.article_no] as chain
```

### Compliance check - who depends on Article 6:
```cypher
MATCH (a:Article {article_no: 6})<-[:REFERENCES*1..2]-(dependent)
RETURN DISTINCT dependent.article_no, dependent.title_vi
```

## 📝 Patterns Detected

| Pattern | Example | Type |
|---------|---------|------|
| `theo Điều X` | "theo Điều 6" | article |
| `Điều X của Quy chế` | "Điều 16 của Quy chế này" | article |
| `quy định tại Điều X` | "quy định tại Điều 14" | article |
| `Khoản X Điều Y` | "Khoản 2 Điều 6" | article_clause |
| `theo Khoản X` | "theo Khoản 3" | clause |
| `tại Điều X` | "tại Điều 21" | article |
| `căn cứ Điều X` | "căn cứ Điều 5" | article |

## 🎯 Use Cases

### 1. Smart Context Expansion
When user asks about Article 16, auto-include referenced articles.

### 2. Compliance Impact Analysis
If Article 6 changes, find all 17 dependent articles for review.

### 3. Knowledge Graph Visualization
Use Neo4j Bloom to visualize regulation network.

### 4. Citation Analysis
Find most/least referenced articles, orphan regulations, citation clusters.

## 🔧 Advanced Usage

### Dry Run (Preview Only)
```python
stats = detector.process_document("QD_790_2022", dry_run=True)
# Detects but doesn't create relationships
```

### Get Detailed Stats
```python
stats = detector.get_cross_reference_stats()
print(stats['articles']['total_references_from_articles'])
print(stats['clauses']['avg_references_per_clause'])
```

### Re-run After Graph Changes
```bash
# If you rebuild Phase 1, re-run cross-reference detection
python indexing/cross_reference_detector.py
```

## ⚠️ Known Issues

- **4 references failed**: Target Clause nodes not found in graph
  - These clauses may not have been parsed correctly
  - Check: Article 16 Clause 2, Article 18 Clause 2

## 📚 Documentation

Full documentation: `docs/ENHANCEMENT_PDF_TABLES_CROSSREFS.md`
