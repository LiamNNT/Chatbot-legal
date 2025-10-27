#!/usr/bin/env python3
"""
Index file PDF quy định vào hệ thống RAG.

Script này xử lý file PDF quy định, trích xuất text, chia thành chunks
và index vào cả Weaviate (vector search) và OpenSearch (BM25 search).
"""

import os
import sys
import logging
import asyncio
import re
from pathlib import Path
from typing import List, Dict, Tuple
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


def extract_text_from_pdf(pdf_path: Path) -> Tuple[str, Dict]:
    """
    Trích xuất text từ file PDF.
    
    Args:
        pdf_path: Đường dẫn đến file PDF
        
    Returns:
        Tuple (text_content, metadata_dict)
    """
    try:
        import PyPDF2
    except ImportError:
        logger.error("PyPDF2 chưa được cài đặt. Vui lòng chạy: pip install PyPDF2")
        sys.exit(1)
    
    logger.info(f"Đang đọc file PDF: {pdf_path.name}")
    
    text_content = ""
    metadata = {
        'total_pages': 0,
        'filename': pdf_path.name,
        'file_size': pdf_path.stat().st_size,
    }
    
    try:
        with open(pdf_path, 'rb') as pdf_file:
            pdf_reader = PyPDF2.PdfReader(pdf_file)
            metadata['total_pages'] = len(pdf_reader.pages)
            
            # Trích xuất metadata từ PDF
            if pdf_reader.metadata:
                if pdf_reader.metadata.title:
                    metadata['pdf_title'] = pdf_reader.metadata.title
                if pdf_reader.metadata.author:
                    metadata['pdf_author'] = pdf_reader.metadata.author
                if pdf_reader.metadata.subject:
                    metadata['pdf_subject'] = pdf_reader.metadata.subject
            
            # Trích xuất text từ tất cả các trang
            for page_num, page in enumerate(pdf_reader.pages, start=1):
                page_text = page.extract_text()
                if page_text:
                    # Thêm số trang để theo dõi
                    text_content += f"\n\n[Trang {page_num}]\n{page_text}"
            
            logger.info(f"  ✓ Đã trích xuất {len(text_content)} ký tự từ {metadata['total_pages']} trang")
            
    except Exception as e:
        logger.error(f"Lỗi khi đọc file PDF: {e}")
        raise
    
    return text_content, metadata


def clean_text(text: str) -> str:
    """
    Làm sạch text từ PDF.
    
    Args:
        text: Text gốc
        
    Returns:
        Text đã được làm sạch
    """
    # Xóa các ký tự đặc biệt không cần thiết
    text = re.sub(r'\s+', ' ', text)  # Normalize whitespace
    text = re.sub(r'\n{3,}', '\n\n', text)  # Remove excessive newlines
    
    # Xóa các số trang đơn lẻ
    text = re.sub(r'\n\d+\n', '\n', text)
    
    return text.strip()


def chunk_text_by_page(text: str, chunk_size: int = 2000, overlap: int = 200) -> List[Tuple[str, int]]:
    """
    Chia text thành chunks, ưu tiên theo trang.
    
    Args:
        text: Text cần chia
        chunk_size: Kích thước chunk (ký tự)
        overlap: Kích thước overlap (ký tự)
        
    Returns:
        List of (chunk_text, page_number)
    """
    chunks = []
    
    # Tách theo marker trang
    page_pattern = r'\[Trang (\d+)\]'
    pages = re.split(page_pattern, text)
    
    current_chunk = ""
    current_page = 1
    
    i = 0
    while i < len(pages):
        if i == 0 and not re.match(r'^\d+$', pages[i]):
            # Text trước trang đầu tiên
            current_chunk = pages[i].strip()
            i += 1
            continue
            
        if i < len(pages) and re.match(r'^\d+$', pages[i]):
            # Đây là số trang
            page_num = int(pages[i])
            if i + 1 < len(pages):
                page_text = pages[i + 1].strip()
                
                # Nếu chunk hiện tại + trang mới > chunk_size, lưu chunk hiện tại
                if len(current_chunk) + len(page_text) > chunk_size and current_chunk:
                    chunks.append((current_chunk, current_page))
                    
                    # Bắt đầu chunk mới với overlap
                    if len(current_chunk) > overlap:
                        current_chunk = current_chunk[-overlap:] + "\n\n" + page_text
                    else:
                        current_chunk = page_text
                    current_page = page_num
                else:
                    # Thêm vào chunk hiện tại
                    if current_chunk:
                        current_chunk += "\n\n" + page_text
                    else:
                        current_chunk = page_text
                        current_page = page_num
                        
                i += 2
            else:
                i += 1
        else:
            i += 1
    
    # Thêm chunk cuối cùng
    if current_chunk:
        chunks.append((current_chunk, current_page))
    
    # Nếu không tìm thấy marker trang, chia theo paragraph
    if not chunks:
        paragraphs = text.split('\n\n')
        current_chunk = ""
        current_page = 1
        
        for para in paragraphs:
            para = para.strip()
            if not para:
                continue
                
            if len(current_chunk) + len(para) > chunk_size and current_chunk:
                chunks.append((current_chunk, current_page))
                
                if len(current_chunk) > overlap:
                    current_chunk = current_chunk[-overlap:] + "\n\n" + para
                else:
                    current_chunk = para
            else:
                if current_chunk:
                    current_chunk += "\n\n" + para
                else:
                    current_chunk = para
        
        if current_chunk:
            chunks.append((current_chunk, current_page))
    
    return chunks


def parse_quy_dinh_metadata(pdf_path: Path, pdf_metadata: Dict) -> Dict:
    """
    Parse metadata từ tên file và nội dung PDF quy định.
    
    Args:
        pdf_path: Đường dẫn file PDF
        pdf_metadata: Metadata từ PDF
        
    Returns:
        Dict chứa metadata
    """
    filename = pdf_path.stem  # 790-qd-dhcntt_28-9-22_quy_che_dao_tao
    
    metadata = {
        'doc_type': 'regulation',
        'faculty': 'UIT',
        'subject': 'Quy chế đào tạo',
        'year': None,
        'doc_number': None,
        'issue_date': None,
    }
    
    # Trích xuất số quyết định
    match = re.search(r'^(\d+)-qd', filename, re.IGNORECASE)
    if match:
        metadata['doc_number'] = match.group(1)
    
    # Trích xuất ngày ban hành từ filename: 28-9-22
    date_match = re.search(r'(\d{1,2})-(\d{1,2})-(\d{2,4})', filename)
    if date_match:
        day = date_match.group(1)
        month = date_match.group(2)
        year = date_match.group(3)
        
        # Chuyển đổi năm 2 chữ số thành 4 chữ số
        if len(year) == 2:
            year = f"20{year}"
        
        metadata['issue_date'] = f"{day}/{month}/{year}"
        metadata['year'] = int(year)
    
    # Trích xuất loại văn bản từ filename
    if 'quy_che' in filename or 'quy_dinh' in filename:
        metadata['subject'] = 'Quy chế đào tạo'
    elif 'huong_dan' in filename:
        metadata['subject'] = 'Hướng dẫn'
    elif 'thong_bao' in filename:
        metadata['subject'] = 'Thông báo'
    
    # Bổ sung từ PDF metadata
    if pdf_metadata.get('pdf_title'):
        metadata['title'] = pdf_metadata['pdf_title']
    else:
        # Tạo title từ filename
        metadata['title'] = filename.replace('_', ' ').replace('-', ' ').title()
    
    return metadata


def create_document_chunks(
    pdf_path: Path, 
    text_content: str, 
    pdf_metadata: Dict
) -> List[DocumentChunk]:
    """
    Tạo DocumentChunk objects từ PDF content.
    
    Args:
        pdf_path: Đường dẫn file PDF
        text_content: Text đã trích xuất
        pdf_metadata: Metadata từ PDF
        
    Returns:
        List of DocumentChunk
    """
    # Parse metadata
    doc_metadata = parse_quy_dinh_metadata(pdf_path, pdf_metadata)
    
    # Clean text
    cleaned_text = clean_text(text_content)
    
    # Chunk text
    text_chunks = chunk_text_by_page(cleaned_text, chunk_size=2000, overlap=200)
    
    logger.info(f"  ✓ Đã tạo {len(text_chunks)} chunks từ document")
    
    # Create DocumentChunk objects
    chunks = []
    doc_id = f"quy_dinh_{pdf_path.stem}"
    
    for i, (chunk_text, page_num) in enumerate(text_chunks):
        chunk_id = f"{doc_id}_chunk_{i}"
        
        metadata = DocumentMetadata(
            doc_id=doc_id,
            chunk_id=chunk_id,
            title=doc_metadata.get('title', pdf_path.name),
            page=page_num,
            doc_type=doc_metadata['doc_type'],
            faculty=doc_metadata['faculty'],
            year=doc_metadata.get('year'),
            subject=doc_metadata['subject'],
            language=DocumentLanguage.VIETNAMESE,
            section=f"page_{page_num}",
            subsection=f"chunk_{i}",
            extra={
                'source': 'pdf_upload',
                'filename': pdf_path.name,
                'doc_number': doc_metadata.get('doc_number'),
                'issue_date': doc_metadata.get('issue_date'),
                'total_chunks': len(text_chunks),
                'chunk_index': i,
                'total_pages': pdf_metadata['total_pages'],
                'file_size': pdf_metadata['file_size'],
            }
        )
        
        chunk = DocumentChunk(
            text=chunk_text,
            chunk_index=i,
            metadata=metadata
        )
        
        chunks.append(chunk)
    
    return chunks


async def index_to_weaviate(chunks: List[DocumentChunk]) -> bool:
    """Index chunks vào Weaviate."""
    logger.info(f"\n📊 Indexing {len(chunks)} chunks vào Weaviate...")
    
    try:
        container = DIContainer()
        vector_repo = container.get_vector_repository()
        
        success = await vector_repo.index_documents(chunks)
        
        if success:
            logger.info(f"  ✅ Đã index thành công vào Weaviate")
        else:
            logger.error(f"  ❌ Lỗi khi index vào Weaviate")
            
        return success
        
    except Exception as e:
        logger.error(f"  ❌ Lỗi khi index vào Weaviate: {e}")
        import traceback
        traceback.print_exc()
        return False


async def index_to_opensearch(chunks: List[DocumentChunk]) -> bool:
    """Index chunks vào OpenSearch."""
    logger.info(f"\n📊 Indexing {len(chunks)} chunks vào OpenSearch...")
    
    import requests
    
    try:
        # Chuẩn bị bulk documents cho OpenSearch
        bulk_docs = []
        
        for chunk in chunks:
            doc = {
                'doc_id': chunk.metadata.doc_id,
                'chunk_id': chunk.metadata.chunk_id,
                'text': chunk.text,
                'title': chunk.metadata.title or '',
                'doc_type': chunk.metadata.doc_type or 'regulation',
                'faculty': chunk.metadata.faculty or 'UIT',
                'year': chunk.metadata.year,
                'subject': chunk.metadata.subject or '',
                'language': 'vi',
                'metadata': {
                    'page': chunk.metadata.page,
                    'section': chunk.metadata.section,
                    'subsection': chunk.metadata.subsection,
                    **chunk.metadata.extra
                }
            }
            bulk_docs.append(doc)
        
        # Gọi API để bulk index
        response = requests.post(
            'http://localhost:8000/v1/opensearch/bulk-index',
            json={'documents': bulk_docs},
            timeout=60
        )
        
        if response.status_code == 200:
            result = response.json()
            logger.info(f"  ✅ Đã index {result['successful']} documents vào OpenSearch")
            if result['failed'] > 0:
                logger.warning(f"  ⚠️  {result['failed']} documents lỗi")
            return True
        else:
            logger.error(f"  ❌ Bulk indexing thất bại: {response.status_code}")
            logger.error(f"     {response.text}")
            return False
            
    except Exception as e:
        logger.error(f"  ❌ Lỗi khi index vào OpenSearch: {e}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    """Main function."""
    logger.info("="*80)
    logger.info("INDEX FILE PDF QUY ĐỊNH VÀO HỆ THỐNG RAG")
    logger.info("="*80)
    
    # Đường dẫn file PDF
    pdf_path = project_root / "data" / "quy_dinh" / "790-qd-dhcntt_28-9-22_quy_che_dao_tao.pdf"
    
    if not pdf_path.exists():
        logger.error(f"❌ Không tìm thấy file: {pdf_path}")
        return
    
    logger.info(f"\n📄 File: {pdf_path.name}")
    logger.info(f"   Size: {pdf_path.stat().st_size / 1024:.2f} KB")
    
    # Step 1: Trích xuất text từ PDF
    logger.info("\n📌 Step 1: Trích xuất text từ PDF")
    text_content, pdf_metadata = extract_text_from_pdf(pdf_path)
    
    if not text_content:
        logger.error("❌ Không trích xuất được text từ PDF")
        return
    
    # Step 2: Tạo document chunks
    logger.info("\n📌 Step 2: Tạo document chunks")
    chunks = create_document_chunks(pdf_path, text_content, pdf_metadata)
    
    logger.info(f"\n📋 Summary:")
    logger.info(f"   Document: {chunks[0].metadata.title}")
    logger.info(f"   Doc Type: {chunks[0].metadata.doc_type}")
    logger.info(f"   Faculty: {chunks[0].metadata.faculty}")
    logger.info(f"   Year: {chunks[0].metadata.year}")
    logger.info(f"   Subject: {chunks[0].metadata.subject}")
    logger.info(f"   Total Pages: {pdf_metadata['total_pages']}")
    logger.info(f"   Total Chunks: {len(chunks)}")
    
    # Show sample chunks
    logger.info(f"\n📝 Sample chunks:")
    for i in range(min(2, len(chunks))):
        logger.info(f"\n   Chunk {i+1} (Page {chunks[i].metadata.page}):")
        preview = chunks[i].text[:200].replace('\n', ' ')
        logger.info(f"   {preview}...")
    
    # Step 3: Index vào cả hai hệ thống
    logger.info("\n📌 Step 3: Index vào RAG system")
    logger.info("⚠️  Đang index vào cả Weaviate (vector) và OpenSearch (BM25)")
    
    # Index vào Weaviate
    weaviate_success = await index_to_weaviate(chunks)
    
    # Index vào OpenSearch
    opensearch_success = await index_to_opensearch(chunks)
    
    # Summary
    logger.info("\n" + "="*80)
    if weaviate_success and opensearch_success:
        logger.info("✅ INDEXING HOÀN THÀNH THÀNH CÔNG!")
        logger.info(f"   ✓ Weaviate: {len(chunks)} chunks")
        logger.info(f"   ✓ OpenSearch: {len(chunks)} chunks")
        logger.info(f"   Document: {chunks[0].metadata.title}")
        logger.info(f"   Total Pages: {pdf_metadata['total_pages']}")
    elif weaviate_success:
        logger.warning("⚠️  INDEXING HOÀN THÀNH MỘT PHẦN")
        logger.warning(f"   ✓ Weaviate: OK")
        logger.warning(f"   ✗ OpenSearch: FAILED")
    elif opensearch_success:
        logger.warning("⚠️  INDEXING HOÀN THÀNH MỘT PHẦN")
        logger.warning(f"   ✗ Weaviate: FAILED")
        logger.warning(f"   ✓ OpenSearch: OK")
    else:
        logger.error("❌ INDEXING THẤT BẠI!")
        logger.error("   Cả Weaviate và OpenSearch đều gặp lỗi")
    
    logger.info("="*80)
    
    logger.info("\n💡 Bước tiếp theo:")
    logger.info("   1. Test search với từ khóa: 'quy chế đào tạo'")
    logger.info("   2. Test search với: 'điều kiện tốt nghiệp'")
    logger.info("   3. Kiểm tra kết quả trong chatbot")


if __name__ == "__main__":
    asyncio.run(main())
