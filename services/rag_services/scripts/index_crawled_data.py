#!/usr/bin/env python3
"""
Index crawled program data into Weaviate.

This script processes raw crawled data from data/crawled_programs
and indexes it into the Weaviate vector database for RAG.
"""

import os
import sys
import logging
import asyncio
import re
from pathlib import Path
from typing import List, Dict
from datetime import datetime

# Load environment variables
from dotenv import load_dotenv
project_root = Path(__file__).parent.parent
load_dotenv(dotenv_path=project_root / ".env")

sys.path.insert(0, str(project_root))

from core.domain.models import DocumentChunk, DocumentMetadata, DocumentLanguage
from core.container import DIContainer

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def parse_crawled_file(file_path: Path) -> Dict:
    """
    Parse a crawled text file and extract metadata + content.
    
    Expected format:
    URL: <url>
    Title: <title>
    Crawled: <timestamp>
    Length: <chars> characters
    ====================================
    <content>
    
    Returns:
        Dict with parsed data
    """
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    lines = content.split('\n')
    
    # Parse header
    url = ""
    title = ""
    crawled_date = ""
    length = 0
    content_start = 0
    
    for i, line in enumerate(lines):
        if line.startswith("URL:"):
            url = line.replace("URL:", "").strip()
        elif line.startswith("Title:"):
            title = line.replace("Title:", "").strip()
            # Remove " | Cổng thông tin đào tạo" suffix
            title = re.sub(r'\s*\|\s*Cổng thông tin đào tạo\s*$', '', title)
        elif line.startswith("Crawled:"):
            crawled_date = line.replace("Crawled:", "").strip()
        elif line.startswith("Length:"):
            length_str = line.replace("Length:", "").strip()
            # Extract number from "22,598 characters"
            match = re.search(r'([\d,]+)', length_str)
            if match:
                length = int(match.group(1).replace(',', ''))
        elif '=' * 20 in line:
            content_start = i + 1
            break
    
    # Extract actual content (skip header lines)
    actual_content = '\n'.join(lines[content_start:]).strip()
    
    # Extract metadata from URL and title
    program_info = extract_program_info(url, title, file_path.stem)
    
    return {
        'url': url,
        'title': title,
        'crawled_date': crawled_date,
        'length': length,
        'content': actual_content,
        'program_info': program_info,
        'filename': file_path.name
    }


def extract_program_info(url: str, title: str, filename: str) -> Dict:
    """
    Extract program metadata from URL, title, and filename.
    
    Examples:
    - URL: https://student.uit.edu.vn/content/cu-nhan-nganh-khoa-hoc-may-tinh-ap-dung-tu-khoa-19-2024
    - Title: Cử nhân ngành Khoa học Máy tính (Áp dụng từ khóa 19 - 2024)
    - Filename: cu-nhan-nganh-khoa-hoc-may-tinh-ap-dung-tu-khoa-19-2024.txt
    """
    info = {
        'level': 'undergraduate',  # Default
        'subject': 'Unknown',
        'cohort': None,
        'year': None,
        'program_id': filename.replace('.txt', '')
    }
    
    # Extract year from title or filename
    year_match = re.search(r'(\d{4})', title)
    if year_match:
        info['year'] = int(year_match.group(1))
    
    # Extract cohort (khóa)
    cohort_match = re.search(r'khóa\s*(\d+)', title, re.IGNORECASE)
    if cohort_match:
        info['cohort'] = int(cohort_match.group(1))
    
    # Extract subject from title
    subject_patterns = {
        'Khoa học Máy tính': r'khoa\s*học\s*máy\s*tính',
        'Hệ thống Thông tin': r'hệ\s*thống\s*thông\s*tin',
        'Mạng máy tính': r'mạng\s*máy\s*tính',
        'Kỹ thuật Phần mềm': r'kỹ\s*thuật\s*phần\s*mềm',
        'An toàn Thông tin': r'an\s*toàn\s*thông\s*tin',
        'Khoa học Dữ liệu': r'khoa\s*học\s*dữ\s*liệu',
        'Trí tuệ Nhân tạo': r'trí\s*tuệ\s*nhân\s*tạo'
    }
    
    for subject, pattern in subject_patterns.items():
        if re.search(pattern, title, re.IGNORECASE):
            info['subject'] = subject
            break
    
    # Determine level
    if 'văn bằng 2' in title.lower() or 'van-bang-2' in url:
        info['level'] = 'second_degree'
    elif 'từ xa' in title.lower() or 'tu-xa' in url:
        info['level'] = 'distance_learning'
    elif 'cao đẳng' in title.lower():
        info['level'] = 'associate'
    elif 'thạc sĩ' in title.lower() or 'master' in url:
        info['level'] = 'master'
    else:
        info['level'] = 'undergraduate'
    
    return info


def chunk_content(content: str, chunk_size: int = 2000, overlap: int = 200) -> List[str]:
    """
    Split content into overlapping chunks.
    
    Simple sentence-based chunking to preserve meaning.
    """
    # Split by double newlines first (paragraphs)
    paragraphs = content.split('\n\n')
    
    chunks = []
    current_chunk = ""
    
    for para in paragraphs:
        para = para.strip()
        if not para:
            continue
        
        # If adding this paragraph exceeds chunk size, save current chunk
        if len(current_chunk) + len(para) > chunk_size and current_chunk:
            chunks.append(current_chunk)
            
            # Start new chunk with overlap
            # Take last 'overlap' chars from previous chunk
            if len(current_chunk) > overlap:
                current_chunk = current_chunk[-overlap:] + "\n\n" + para
            else:
                current_chunk = para
        else:
            if current_chunk:
                current_chunk += "\n\n" + para
            else:
                current_chunk = para
    
    # Add final chunk
    if current_chunk:
        chunks.append(current_chunk)
    
    return chunks


def create_document_chunks(parsed_data: Dict) -> List[DocumentChunk]:
    """
    Create DocumentChunk objects from parsed crawled data.
    
    Splits content into manageable chunks with metadata.
    """
    program_info = parsed_data['program_info']
    content = parsed_data['content']
    
    # Create chunks
    text_chunks = chunk_content(content, chunk_size=2000, overlap=200)
    
    chunks = []
    doc_id = f"crawled_{program_info['program_id']}"
    
    for i, text in enumerate(text_chunks):
        chunk_id = f"{doc_id}_chunk_{i}"
        
        metadata = DocumentMetadata(
            doc_id=doc_id,
            chunk_id=chunk_id,
            title=parsed_data['title'],
            page=i + 1,
            doc_type='curriculum',
            faculty='UIT',
            year=program_info.get('year'),
            subject=program_info.get('subject', 'Unknown'),
            language=DocumentLanguage.VIETNAMESE,
            section=program_info.get('level', 'undergraduate'),
            subsection=f"chunk_{i}",
            extra={
                'source': 'student.uit.edu.vn',
                'url': parsed_data['url'],
                'crawled_date': parsed_data['crawled_date'],
                'filename': parsed_data['filename'],
                'cohort': program_info.get('cohort'),
                'program_id': program_info['program_id'],
                'total_chunks': len(text_chunks),
                'chunk_index': i
            }
        )
        
        chunk = DocumentChunk(
            text=text,
            chunk_index=i,
            metadata=metadata
        )
        
        chunks.append(chunk)
    
    return chunks


def load_all_crawled_files(crawled_dir: Path) -> List[Dict]:
    """
    Load all .txt files from crawled_programs directory.
    """
    if not crawled_dir.exists():
        logger.error(f"Directory not found: {crawled_dir}")
        return []
    
    files = list(crawled_dir.glob("*.txt"))
    logger.info(f"Found {len(files)} crawled files in {crawled_dir}")
    
    parsed_files = []
    
    for file_path in files:
        try:
            logger.info(f"  Parsing: {file_path.name}")
            data = parse_crawled_file(file_path)
            parsed_files.append(data)
            logger.info(f"    ✓ Title: {data['title']}")
            logger.info(f"    ✓ Length: {data['length']} chars")
            logger.info(f"    ✓ Subject: {data['program_info']['subject']}, Year: {data['program_info']['year']}")
        except Exception as e:
            logger.error(f"    ✗ Error parsing {file_path.name}: {e}")
            import traceback
            traceback.print_exc()
    
    return parsed_files


async def index_chunks(chunks: List[DocumentChunk]):
    """Index chunks into Weaviate."""
    logger.info(f"\nIndexing {len(chunks)} document chunks into Weaviate...")
    
    try:
        # Get vector repository from container
        container = DIContainer()
        vector_repo = container.get_vector_repository()
        
        # Index documents
        success = await vector_repo.index_documents(chunks)
        
        if success:
            logger.info(f"✅ Successfully indexed {len(chunks)} document chunks")
        else:
            logger.error("❌ Failed to index documents")
            
        return success
        
    except Exception as e:
        logger.error(f"❌ Error during indexing: {e}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    """Main function."""
    logger.info("="*80)
    logger.info("INDEX CRAWLED PROGRAM DATA")
    logger.info("="*80)
    
    # Step 1: Load crawled files
    logger.info("\n📌 Step 1: Load crawled program files")
    crawled_dir = project_root / "data" / "crawled_programs"
    
    parsed_files = load_all_crawled_files(crawled_dir)
    
    if not parsed_files:
        logger.error("No files loaded")
        return
    
    logger.info(f"\n✓ Loaded {len(parsed_files)} files")
    
    # Step 2: Create document chunks
    logger.info("\n📌 Step 2: Create document chunks")
    all_chunks = []
    
    for data in parsed_files:
        chunks = create_document_chunks(data)
        all_chunks.extend(chunks)
        logger.info(f"  {data['filename']}: {len(chunks)} chunks")
    
    logger.info(f"\n✓ Created {len(all_chunks)} total chunks from {len(parsed_files)} files")
    
    # Show summary
    logger.info("\n📋 Summary:")
    for data in parsed_files:
        info = data['program_info']
        logger.info(f"  • {data['title']}")
        logger.info(f"      Subject: {info['subject']}, Year: {info['year']}, Cohort: {info.get('cohort', 'N/A')}")
    
    # Step 3: Index into Weaviate
    logger.info("\n📌 Step 3: Index into Weaviate")
    logger.info("⚠️  This will ADD to existing data (not replace)")
    
    success = await index_chunks(all_chunks)
    
    if success:
        logger.info("\n" + "="*80)
        logger.info("✅ INDEXING COMPLETE!")
        logger.info(f"   Indexed: {len(all_chunks)} chunks from {len(parsed_files)} files")
        logger.info(f"   Collection: {os.getenv('WEAVIATE_CLASS_NAME', 'ChatbotUit')}")
        logger.info("="*80)
        
        logger.info("\n💡 Next steps:")
        logger.info("   1. Test search with crawled data")
        logger.info("   2. Query about curriculum information")
    else:
        logger.error("\n" + "="*80)
        logger.error("❌ INDEXING FAILED!")
        logger.error("="*80)


if __name__ == "__main__":
    asyncio.run(main())
