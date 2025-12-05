"""
Test full Two-Stage Pipeline với debugging.
"""

import sys
import logging
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Configure DEBUG logging
logging.basicConfig(
    level=logging.DEBUG,
    format="%(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

from dotenv import load_dotenv
load_dotenv()

import os
print(f"\n=== ENV CHECK ===")
api_key = os.getenv("OPENAI_API_KEY") or os.getenv("OPENROUTER_API_KEY")
print(f"API Key found: {bool(api_key)}, length: {len(api_key) if api_key else 0}")
print(f"Base URL: {os.getenv('OPENAI_BASE_URL')}")

# Import các class từ hybrid_extractor
from hybrid_extractor import (
    VLMConfig, VLMProvider, StructureExtractor, 
    StructureExtractionResult, PageContext
)

def test_single_page():
    """Test extraction với một page duy nhất."""
    print("\n" + "="*60)
    print("TEST: Single page structure extraction")
    print("="*60)
    
    # Setup config
    config = VLMConfig.from_env(VLMProvider.OPENROUTER)
    # Override model to use GPT-4.1 which works
    config.model = "openai/gpt-4.1"
    print(f"Config: provider={config.provider.value}, model={config.model}")
    
    # Create extractor
    extractor = StructureExtractor(config)
    
    # Find image
    data_dir = Path(__file__).parent.parent / "data" / "quy_dinh"
    image_dir = data_dir / "1393-qd-dhcntt_29-12-2023_cap_nhat_quy_che_dao_tao_theo_hoc_che_tin_chi_cho_he_dai_hoc_chinh_quy_images"
    
    if not image_dir.exists():
        print(f"ERROR: Image directory not found: {image_dir}")
        return
    
    images = sorted(image_dir.glob("*.png"))
    if not images:
        print("ERROR: No PNG images found")
        return
    
    print(f"Found {len(images)} images")
    
    # Test với page 1
    test_image = images[0]
    print(f"\nProcessing: {test_image.name}")
    
    prev_context = PageContext()
    
    try:
        nodes, relations, next_context = extractor._process_single_page(
            test_image, prev_context, page_number=1
        )
        
        print(f"\n=== RESULTS ===")
        print(f"Nodes extracted: {len(nodes)}")
        for node in nodes:
            print(f"  - {node.id}: {node.type.value} - {node.title[:50]}...")
        
        print(f"\nRelations extracted: {len(relations)}")
        for rel in relations:
            print(f"  - {rel.source} -> {rel.target} ({rel.type})")
        
        print(f"\nNext context: {next_context.model_dump_json(indent=2)}")
        
    except Exception as e:
        import traceback
        print(f"\n=== ERROR ===")
        print(f"Type: {type(e).__name__}")
        print(f"Message: {e}")
        print(f"Traceback:\n{traceback.format_exc()}")


def test_multi_page():
    """Test extraction với nhiều pages."""
    print("\n" + "="*60)
    print("TEST: Multi-page structure extraction")
    print("="*60)
    
    # Setup config
    config = VLMConfig.from_env(VLMProvider.OPENROUTER)
    config.model = "openai/gpt-4.1"
    
    # Create extractor
    extractor = StructureExtractor(config)
    
    # Find images
    data_dir = Path(__file__).parent.parent / "data" / "quy_dinh"
    image_dir = data_dir / "1393-qd-dhcntt_29-12-2023_cap_nhat_quy_che_dao_tao_theo_hoc_che_tin_chi_cho_he_dai_hoc_chinh_quy_images"
    
    if not image_dir.exists():
        print(f"ERROR: Image directory not found: {image_dir}")
        return
    
    images = sorted(image_dir.glob("*.png"))[:3]  # Test với 3 pages đầu
    print(f"Testing with {len(images)} images")
    
    # Process all pages
    result = extractor.extract_from_images(images)
    
    print(f"\n=== FINAL RESULTS ===")
    print(f"Total pages: {result.page_count}")
    print(f"Articles: {len(result.articles)}")
    print(f"Chapters: {len(result.chapters)}")
    print(f"Clauses: {len(result.clauses)}")
    print(f"Relations: {len(result.relations)}")
    print(f"Errors: {len(result.errors)}")
    
    for article in result.articles[:5]:
        print(f"\n  Article: {article.title}")
        print(f"  Text: {article.full_text[:200]}...")


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "multi":
        test_multi_page()
    else:
        test_single_page()
