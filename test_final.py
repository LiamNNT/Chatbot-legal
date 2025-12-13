"""
FINAL TEST: Verify amendment extraction is working correctly.
This simulates what the chatbot will return for "học kỳ hè" questions.
"""
import asyncio
import sys
sys.path.insert(0, r"c:\Users\admin\Downloads\Khiem\Chatbot-UIT\services\rag_services")

from adapters.graph.neo4j_adapter import Neo4jGraphAdapter

async def final_test():
    adapter = Neo4jGraphAdapter(
        uri="bolt://localhost:7687",
        username="neo4j",
        password="uitchatbot"
    )
    
    print("="*70)
    print("FINAL TEST: Searching for 'đăng ký học phần học kỳ hè'")
    print("="*70)
    
    # This is what the chatbot would search for
    results = await adapter.search_with_amendments(
        ["đăng ký", "học phần", "học kỳ hè"], 
        limit=5
    )
    
    print("\n📋 TOP RESULT (This is what chatbot should use):")
    print("-"*70)
    
    if results:
        r = results[0]
        print(f"📌 Title: {r.get('title')}")
        print(f"📌 Is Amended: {r.get('is_amended')}")
        print(f"\n📜 Content:")
        print(r.get('text', '')[:600])
        
        # Check content quality
        text = r.get('text', '')
        
        print("\n" + "="*70)
        print("✅ VERIFICATION CHECKLIST:")
        print("="*70)
        
        checks = [
            ("Contains '12 tín chỉ' (NEW)", "12 tín chỉ" in text),
            ("Contains 'đủ sĩ số' (NEW)", "đủ sĩ số" in text),
            ("Contains 'học mới, học lại' (NEW)", "học mới" in text and "học lại" in text),
            ("Does NOT contain 'ĐTBC' (OLD)", "ĐTBC" not in text),
            ("Does NOT contain '7,0' (OLD)", "7,0" not in text),
            ("Does NOT contain 'điểm trung bình' (OLD)", "điểm trung bình" not in text),
        ]
        
        all_pass = True
        for desc, passed in checks:
            status = "✓" if passed else "✗"
            print(f"  {status} {desc}")
            if not passed:
                all_pass = False
        
        print("\n" + "="*70)
        if all_pass:
            print("🎉 ALL CHECKS PASSED! Chatbot should now answer with NEW content!")
        else:
            print("⚠️ SOME CHECKS FAILED! Need further investigation.")
    
    adapter.close()

asyncio.run(final_test())
