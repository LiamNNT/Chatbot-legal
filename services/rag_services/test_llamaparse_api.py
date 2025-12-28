#!/usr/bin/env python3
"""
Test LlamaParse API Integration

This script tests the LlamaParse API with a sample PDF document.
"""

import asyncio
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Check for API key
api_key = os.getenv("LLAMA_CLOUD_API_KEY")
if not api_key:
    print("❌ ERROR: LLAMA_CLOUD_API_KEY not found in environment")
    print("   Please set it in .env file")
    sys.exit(1)

print(f"✅ API Key found: {api_key[:10]}...{api_key[-4:]}")

async def test_llamaparse_connection():
    """Test basic LlamaParse API connection."""
    try:
        from llama_parse import LlamaParse
        
        parser = LlamaParse(
            api_key=api_key,
            result_type="markdown",
            verbose=True,
        )
        
        print("✅ LlamaParse initialized successfully")
        return True
    except ImportError:
        print("❌ llama-parse package not installed")
        print("   Run: pip install llama-parse")
        return False
    except Exception as e:
        print(f"❌ Failed to initialize LlamaParse: {e}")
        return False


async def test_parse_sample_pdf():
    """Test parsing a sample PDF file."""
    try:
        from llama_parse import LlamaParse
        
        # Look for a sample PDF in the data directory
        data_dir = Path("data")
        pdf_files = list(data_dir.glob("**/*.pdf")) if data_dir.exists() else []
        
        if not pdf_files:
            print("⚠️  No PDF files found in data/ directory")
            print("   Creating a simple test with text file instead...")
            
            # Create a simple text file to test API connection
            test_file = Path("test_sample.txt")
            test_file.write_text("""
# Sample Document for Testing

## Section 1: Introduction
This is a test document to verify LlamaParse API connection.

## Section 2: Content
- Item 1: Testing
- Item 2: Verification
- Item 3: Validation

## Table Example
| STT | Nội dung | Ghi chú |
|-----|----------|---------|
| 1   | Test 1   | OK      |
| 2   | Test 2   | OK      |
""")
            
            parser = LlamaParse(
                api_key=api_key,
                result_type="markdown",
                verbose=True,
            )
            
            print(f"\n📄 Parsing test file: {test_file}")
            documents = await parser.aload_data(str(test_file))
            
            # Clean up
            test_file.unlink()
            
            if documents:
                print(f"\n✅ Successfully parsed! Got {len(documents)} document(s)")
                print("\n📝 Content preview:")
                print("-" * 50)
                content = documents[0].text[:500] if documents[0].text else "No content"
                print(content)
                print("-" * 50)
                return True
            else:
                print("❌ No documents returned from parser")
                return False
        else:
            # Use first PDF found
            pdf_file = pdf_files[0]
            print(f"\n📄 Found PDF: {pdf_file}")
            
            # Check if gpt4o mode is enabled
            gpt4o_mode = os.getenv("LLAMA_PARSE_GPT4O_MODE", "false").lower() == "true"
            
            parser = LlamaParse(
                api_key=api_key,
                result_type="markdown",
                verbose=True,
                gpt4o_mode=gpt4o_mode,
                gpt4o_api_key=os.getenv("OPENAI_API_KEY") if gpt4o_mode else None,
            )
            
            print(f"   GPT-4o mode: {'enabled' if gpt4o_mode else 'disabled'}")
            print(f"\n🔄 Parsing PDF (this may take a moment)...")
            
            documents = await parser.aload_data(str(pdf_file))
            
            if documents:
                print(f"\n✅ Successfully parsed! Got {len(documents)} document(s)")
                print(f"   Total characters: {sum(len(d.text) for d in documents)}")
                
                print("\n📝 Content preview (first 1000 chars):")
                print("-" * 50)
                content = documents[0].text[:1000] if documents[0].text else "No content"
                print(content)
                print("-" * 50)
                
                # Check for tables
                if "| " in documents[0].text:
                    print("\n✅ Tables detected in parsed content!")
                
                return True
            else:
                print("❌ No documents returned from parser")
                return False
                
    except Exception as e:
        print(f"❌ Error during parsing: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_extraction_service():
    """Test the full LlamaIndexExtractionService."""
    try:
        from app.core.extraction.llamaindex_extractor import (
            LlamaIndexExtractionService,
            ExtractionConfig,
        )
        
        config = ExtractionConfig.from_env()
        print(f"\n🔧 ExtractionConfig loaded:")
        print(f"   - LlamaParse API Key: {config.llama_cloud_api_key[:10]}...")
        print(f"   - GPT-4o mode: {config.use_gpt4o_mode}")
        print(f"   - Extract tables JSON: {config.extract_tables_as_json}")
        print(f"   - Chunk size: {config.chunk_size}")
        print(f"   - Chunk overlap: {config.chunk_overlap}")
        
        service = LlamaIndexExtractionService(config)
        print("✅ LlamaIndexExtractionService initialized successfully")
        
        return True
    except ImportError as e:
        print(f"❌ Import error: {e}")
        return False
    except Exception as e:
        print(f"❌ Error initializing service: {e}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    """Run all tests."""
    print("=" * 60)
    print("🧪 LLAMAPARSE API INTEGRATION TEST")
    print("=" * 60)
    
    results = []
    
    # Test 1: Basic connection
    print("\n📋 Test 1: LlamaParse Connection")
    print("-" * 40)
    results.append(await test_llamaparse_connection())
    
    # Test 2: Parse sample
    print("\n📋 Test 2: Parse Sample Document")
    print("-" * 40)
    results.append(await test_parse_sample_pdf())
    
    # Test 3: Extraction service
    print("\n📋 Test 3: Extraction Service")
    print("-" * 40)
    results.append(await test_extraction_service())
    
    # Summary
    print("\n" + "=" * 60)
    print("📊 TEST SUMMARY")
    print("=" * 60)
    passed = sum(results)
    total = len(results)
    print(f"   Passed: {passed}/{total}")
    
    if passed == total:
        print("\n✅ ALL TESTS PASSED!")
        print("   LlamaParse API is working correctly.")
    else:
        print(f"\n⚠️  {total - passed} test(s) failed")
        print("   Please check the errors above.")
    
    return 0 if passed == total else 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
