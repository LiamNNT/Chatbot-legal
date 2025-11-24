#!/usr/bin/env python3
"""Build Neo4j graph with LLM extraction (Tier 2: Entities, Tier 3: Rules)."""
import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from infrastructure.store.vector.weaviate_store import get_weaviate_client
from neo4j import GraphDatabase
from config.three_tier_extraction_config import ThreeTierConfigLoader
from weaviate.classes.query import Filter
from openai import OpenAI
import os
import json

print("\n" + "="*80)
print("🧠 BUILD NEO4J GRAPH WITH LLM EXTRACTION (TIER 2 + TIER 3)")
print("="*80)

# Load config
config = ThreeTierConfigLoader()
tier2_model = config.get_tier2_model_id()
tier3_model = config.get_tier3_model_id()
tier2_config = config.get_tier2_model_config()
tier3_config = config.get_tier3_model_config()

print(f"\n⚙️  Configuration:")
print(f"   Tier 2 (Entities): {tier2_model}")
print(f"   Tier 2 Cost: ${tier2_config.cost_per_1m_input}/1M input, ${tier2_config.cost_per_1m_output}/1M output")
print(f"   Tier 3 (Rules): {tier3_model}")
print(f"   Tier 3 Cost: ${tier3_config.cost_per_1m_input}/1M input, ${tier3_config.cost_per_1m_output}/1M output")

# Connect
print("\n📡 Connecting...")
weaviate = get_weaviate_client("http://localhost:8090")
neo4j_driver = GraphDatabase.driver("bolt://localhost:7687", auth=("neo4j", "uitchatbot"))
collection = weaviate.collections.get("VietnameseDocumentV3")

# Setup OpenRouter client
openrouter_client = OpenAI(
    api_key=os.getenv("OPENROUTER_API_KEY"),
    base_url="https://openrouter.ai/api/v1"
)

def extract_entities_tier2(text: str, article_title: str, chapter_title: str = "") -> dict:
    """Extract entities using Tier 2 LLM with prompts from YAML."""
    # Get prompts from config
    system_prompt = config.get_tier2_system_prompt()
    user_prompt = config.format_tier2_user_prompt(
        chapter_title=chapter_title,
        article_title=article_title,
        clause_text=text
    )
    
    try:
        response = openrouter_client.chat.completions.create(
            model=tier2_model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=tier2_config.temperature,
            max_tokens=tier2_config.max_tokens
        )
        content = response.choices[0].message.content.strip()
        # Remove markdown code blocks if present
        if content.startswith("```"):
            content = content.split("```")[1]
            if content.startswith("json"):
                content = content[4:]
        return json.loads(content)
    except Exception as e:
        print(f"   ⚠️  Tier 2 error: {e}")
        return {"entities": [], "relationships": []}

def extract_rules_tier3(text: str, article_title: str, chapter_title: str = "", clause_no: str = "1") -> dict:
    """Extract rules using Tier 3 LLM with prompts from YAML."""
    # Get prompts from config
    system_prompt = config.get_tier3_system_prompt()
    user_prompt = config.format_tier3_user_prompt(
        chapter_title=chapter_title,
        article_title=article_title,
        clause_no=clause_no,
        clause_text=text
    )
    
    try:
        response = openrouter_client.chat.completions.create(
            model=tier3_model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=tier3_config.temperature,
            max_tokens=tier3_config.max_tokens
        )
        content = response.choices[0].message.content.strip()
        # Remove markdown code blocks
        if content.startswith("```"):
            content = content.split("```")[1]
            if content.startswith("json"):
                content = content[4:]
        return json.loads(content)
    except Exception as e:
        print(f"   ⚠️  Tier 3 error: {e}")
        return {"rules": [], "conditions": []}

# Get articles from Weaviate V3
print("\n📥 Fetching articles from Weaviate V3...")
all_docs = []
offset = 0
while True:
    response = collection.query.fetch_objects(
        limit=50, 
        offset=offset,
        filters=Filter.by_property("structure_type").equal("article")
    )
    if not response.objects:
        break
    all_docs.extend(response.objects)
    offset += 50

articles = [obj for obj in all_docs if obj.properties.get('structure_type') == 'article']
print(f"✅ Found {len(articles)} articles to process")

# Process articles with LLM
print(f"\n🧠 Processing with LLM extraction...")
total_entities = 0
total_rules = 0
total_tokens_input = 0
total_tokens_output = 0

with neo4j_driver.session() as session:
    for idx, obj in enumerate(articles, 1):  # Process ALL articles
        p = obj.properties
        article_id = p.get('article', 'Unknown')
        text = p.get('text', '')
        title = p.get('title', '')
        
        print(f"\n[{idx}/{len(articles)}] Processing: {article_id}")
        
        # Create Article node (Tier 1 - already done)
        session.run("""
            MERGE (a:Article {id: $article_id})
            SET a.title = $title,
                a.text = $text,
                a.article_number = $article_number,
                a.chapter = $chapter,
                a.filename = $filename
        """, {
            'article_id': article_id,
            'title': title,
            'text': text,
            'article_number': p.get('article_number', 0),
            'chapter': p.get('chapter', ''),
            'filename': p.get('filename', '')
        })
        
        # TIER 2: Extract Entities
        print(f"   🔍 Tier 2: Extracting entities...")
        entities_data = extract_entities_tier2(
            text=text,
            article_title=title,
            chapter_title=p.get('chapter', '')
        )
        
        for entity in entities_data.get('entities', []):
            session.run("""
                MERGE (e:Entity {name: $name, type: $type})
                SET e.role = $role,
                    e.responsibilities = $responsibilities,
                    e.definition = $definition,
                    e.description = $description
                MERGE (a:Article {id: $article_id})
                MERGE (a)-[:MENTIONS]->(e)
            """, {
                'name': entity.get('name', ''),
                'type': entity.get('type', 'UNKNOWN'),
                'role': entity.get('role', ''),
                'responsibilities': entity.get('responsibilities', ''),
                'definition': entity.get('definition', ''),
                'description': entity.get('description', ''),
                'article_id': article_id
            })
            total_entities += 1
        
        print(f"      ✅ Created {len(entities_data.get('entities', []))} entities")
        
        # TIER 3: Extract Rules
        print(f"   📋 Tier 3: Extracting rules...")
        rules_data = extract_rules_tier3(
            text=text,
            article_title=title,
            chapter_title=p.get('chapter', ''),
            clause_no="1"
        )
        
        for rule in rules_data.get('rules', []):
            session.run("""
                MERGE (r:Rule {id: $rule_id})
                SET r.type = $type,
                    r.description = $description,
                    r.applies_to = $applies_to,
                    r.penalty = $penalty
                MERGE (a:Article {id: $article_id})
                MERGE (a)-[:DEFINES_RULE]->(r)
            """, {
                'rule_id': f"{article_id}_{rule.get('id', '')}",
                'type': rule.get('type', 'UNKNOWN'),
                'description': rule.get('description', ''),
                'applies_to': rule.get('applies_to', ''),
                'penalty': rule.get('penalty', ''),
                'article_id': article_id
            })
            total_rules += 1
        
        print(f"      ✅ Created {len(rules_data.get('rules', []))} rules")

# Statistics
print(f"\n" + "="*80)
print(f"✅ LLM EXTRACTION COMPLETE")
print(f"="*80)
print(f"📊 Statistics:")
print(f"   Articles processed: {len(articles)}")
print(f"   Total entities: {total_entities}")
print(f"   Total rules: {total_rules}")
print(f"\n💰 Estimated cost:")
print(f"   (Check OpenRouter dashboard for exact usage)")
print(f"   Tier 2 (Entities): ~{len(articles)} * 500 tokens = ${len(articles) * 500 * tier2_config.cost_per_1m_input / 1_000_000:.4f}")
print(f"   Tier 3 (Rules): ~{len(articles)} * 500 tokens = ${len(articles) * 500 * tier3_config.cost_per_1m_input / 1_000_000:.4f}")

neo4j_driver.close()
weaviate.close()
print("\n🎉 Done!\n")
