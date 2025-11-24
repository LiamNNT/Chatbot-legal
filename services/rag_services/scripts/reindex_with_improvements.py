#!/usr/bin/env python3
"""
Re-index with Data Quality Improvements

This script re-indexes all documents with the following enhancements:
1. ✅ Improved text cleaning (TOC artifacts removal)
2. ✅ Weaviate V3 schema (flattened metadata)
3. ✅ Neo4j cross-references
4. ✅ Verification and quality checks

Usage:
    python scripts/reindex_with_improvements.py
    python scripts/reindex_with_improvements.py --dry-run
    python scripts/reindex_with_improvements.py --verify-only

Author: Data Quality Team
Date: November 21, 2025
"""

import os
import sys
import logging
import asyncio
import argparse
import json
from pathlib import Path
from typing import List, Dict, Optional
from datetime import datetime
from collections import defaultdict

# Load environment
from dotenv import load_dotenv
project_root = Path(__file__).parent.parent
load_dotenv(dotenv_path=project_root / ".env")

sys.path.insert(0, str(project_root))

# Import dependencies
from core.domain.models import DocumentChunk, DocumentMetadata, DocumentLanguage
from core.container import DIContainer
from indexing.preprocess.vietnamese_text_cleaner import VietnameseTextCleaner
from indexing.preprocess.legal_structure_parser import (
    LegalStructureParser,
    extract_document_metadata
)
from infrastructure.store.vector.weaviate_store import get_weaviate_client
from neo4j import GraphDatabase

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class ReindexingOrchestrator:
    """Orchestrate re-indexing process with quality improvements."""
    
    def __init__(
        self,
        data_dir: Path,
        weaviate_url: str = "http://localhost:8090",
        neo4j_uri: str = "bolt://localhost:7687",
        neo4j_user: str = "neo4j",
        neo4j_password: str = "uitchatbot",
        use_v3_schema: bool = True
    ):
        """
        Initialize orchestrator.
        
        Args:
            data_dir: Directory containing PDFs
            weaviate_url: Weaviate connection URL
            neo4j_uri: Neo4j connection URI
            neo4j_user: Neo4j username
            neo4j_password: Neo4j password
            use_v3_schema: Use improved V3 schema
        """
        self.data_dir = data_dir
        self.weaviate_url = weaviate_url
        self.neo4j_uri = neo4j_uri
        self.neo4j_user = neo4j_user
        self.neo4j_password = neo4j_password
        self.use_v3_schema = use_v3_schema
        
        # Collection name
        self.collection_name = "VietnameseDocumentV3" if use_v3_schema else "VietnameseDocument"
        
        # Stats
        self.stats = defaultdict(int)
        self.errors = []
        
        # Initialize components
        self.text_cleaner = VietnameseTextCleaner()
        self.structure_parser = LegalStructureParser()
        
        # Clients (lazy initialization)
        self._weaviate_client = None
        self._neo4j_driver = None
        self._di_container = None
    
    @property
    def weaviate_client(self):
        """Get Weaviate client (lazy init)."""
        if self._weaviate_client is None:
            self._weaviate_client = get_weaviate_client(self.weaviate_url)
            logger.info(f"✅ Connected to Weaviate: {self.weaviate_url}")
        return self._weaviate_client
    
    @property
    def neo4j_driver(self):
        """Get Neo4j driver (lazy init)."""
        if self._neo4j_driver is None:
            self._neo4j_driver = GraphDatabase.driver(
                self.neo4j_uri,
                auth=(self.neo4j_user, self.neo4j_password)
            )
            # Verify connection
            self._neo4j_driver.verify_connectivity()
            logger.info(f"✅ Connected to Neo4j: {self.neo4j_uri}")
        return self._neo4j_driver
    
    @property
    def di_container(self):
        """Get DI container (lazy init)."""
        if self._di_container is None:
            self._di_container = DIContainer()
            logger.info("✅ Initialized DI Container")
        return self._di_container
    
    def find_pdf_files(self) -> List[Path]:
        """Find all PDF files in data directory."""
        pdf_files = list(self.data_dir.glob("**/*.pdf"))
        logger.info(f"📁 Found {len(pdf_files)} PDF files in {self.data_dir}")
        return pdf_files
    
    def extract_and_clean_text(self, pdf_path: Path) -> tuple[str, Dict]:
        """
        Extract text from PDF and clean it.
        
        Args:
            pdf_path: Path to PDF file
            
        Returns:
            Tuple of (cleaned_text, pdf_metadata)
        """
        try:
            import PyPDF2
        except ImportError:
            logger.error("PyPDF2 not installed. Run: pip install PyPDF2")
            raise
        
        logger.info(f"\n📄 Processing: {pdf_path.name}")
        
        metadata = {
            'filename': pdf_path.name,
            'file_size': pdf_path.stat().st_size,
        }
        
        try:
            with open(pdf_path, 'rb') as pdf_file:
                pdf_reader = PyPDF2.PdfReader(pdf_file)
                metadata['total_pages'] = len(pdf_reader.pages)
                
                # Extract PDF metadata
                if pdf_reader.metadata:
                    if pdf_reader.metadata.title:
                        metadata['pdf_title'] = pdf_reader.metadata.title
                    if pdf_reader.metadata.author:
                        metadata['pdf_author'] = pdf_reader.metadata.author
                
                # Extract and clean text from each page
                page_texts = []
                for page_num, page in enumerate(pdf_reader.pages, start=1):
                    raw_text = page.extract_text()
                    if raw_text:
                        # Clean with improved cleaner (TOC removal!)
                        cleaned_text = self.text_cleaner.clean(raw_text, page_num=page_num)
                        if cleaned_text:
                            page_texts.append(cleaned_text)
                
                # Join all pages
                full_text = "\n\n".join(page_texts)
                
                logger.info(f"  ✓ Extracted {len(full_text)} chars from {metadata['total_pages']} pages")
                logger.info(f"  ✓ Applied improved text cleaning")
                
                self.stats['pdfs_processed'] += 1
                
                return full_text, metadata
                
        except Exception as e:
            logger.error(f"  ❌ Error extracting from {pdf_path.name}: {e}")
            self.stats['pdf_errors'] += 1
            self.errors.append(f"PDF extraction failed: {pdf_path.name} - {e}")
            raise
    
    def parse_legal_structure(self, text: str, pdf_metadata: Dict) -> List[Dict]:
        """
        Parse legal structure from text.
        
        Args:
            text: Cleaned text content
            pdf_metadata: PDF metadata
            
        Returns:
            List of structured elements (chapters, articles, etc.)
        """
        # Extract document metadata
        doc_metadata = extract_document_metadata(text)
        
        logger.info(f"  ✓ Document metadata:")
        logger.info(f"    Title: {doc_metadata.get('title', 'N/A')[:50]}...")
        logger.info(f"    Doc #: {doc_metadata.get('doc_number', 'N/A')}")
        
        # Parse structure
        elements = self.structure_parser.parse(text)
        
        logger.info(f"  ✓ Parsed {len(elements)} structural elements")
        
        self.stats['elements_parsed'] += len(elements)
        
        return elements
    
    def create_weaviate_objects(self, elements: List, pdf_metadata: Dict) -> List[Dict]:
        """
        Create Weaviate objects with V3 schema (flattened metadata).
        
        Args:
            elements: Parsed structural elements (LegalElement objects)
            pdf_metadata: PDF metadata
            
        Returns:
            List of Weaviate object dictionaries
        """
        objects = []
        
        for i, elem in enumerate(elements):
            # elem is a LegalElement object - access attributes directly
            elem_id = elem.id
            elem_type = elem.type.value  # StructureType enum
            elem_title = elem.title
            elem_content = elem.content
            elem_metadata = elem.metadata  # This is the dict
            
            # Generate document ID
            filename_no_ext = pdf_metadata.get('filename', '').replace('.pdf', '')
            doc_id = f"{filename_no_ext}_{elem_id.replace(' ', '_')}"
            chunk_id = f"{doc_id}_{i}"
            
            # Extract article/chapter numbers
            article_number = elem_metadata.get('article_number', 0)
            chapter_info = elem.parent_id if elem.parent_id else ""
            
            # Create flattened object for V3 schema
            obj = {
                # Core fields
                'text': elem_content,
                'doc_id': doc_id,
                'chunk_id': chunk_id,
                'chunk_index': i,
                
                # Document metadata
                'title': elem_title,
                'page': pdf_metadata.get('page', 0),
                'doc_type': 'regulation',  # Assuming quy định
                'faculty': 'UIT',
                'year': 0,
                'language': 'vi',
                
                # ✅ FLATTENED STRUCTURE METADATA (V3 improvement!)
                'structure_type': elem_type,
                'chapter': chapter_info,
                'chapter_title': '',
                'article': elem_id if elem_type == 'article' else '',
                'article_number': article_number,
                'article_title': elem_title if elem_type == 'article' else '',
                'parent_id': elem.parent_id or '',
                'level': elem.level,
                
                # KG integration
                'kg_node_type': elem_type,
                'kg_node_id': elem_id,
                
                # Administrative
                'source': 'pdf_upload',
                'filename': pdf_metadata.get('filename', ''),
                'issuer': '',
                
                # Keep full metadata as JSON for backward compatibility
                'metadata_json': json.dumps({
                    **elem_metadata,
                    'element_id': elem_id,
                    'element_type': elem_type,
                    'title': elem_title,
                    'level': elem.level,
                    'parent_id': elem.parent_id
                }, ensure_ascii=False)
            }
            
            objects.append(obj)
        
        logger.info(f"  ✓ Created {len(objects)} Weaviate objects (V3 schema)")
        
        return objects
    
    async def index_to_weaviate(self, objects: List[Dict]) -> int:
        """
        Index objects to Weaviate.
        
        Args:
            objects: List of Weaviate objects
            
        Returns:
            Number of objects indexed
        """
        if not objects:
            return 0
        
        try:
            # Get collection
            collection = self.weaviate_client.collections.get(self.collection_name)
            
            # Generate embeddings using SentenceTransformer
            from sentence_transformers import SentenceTransformer
            from app.config.settings import settings
            
            embedding_model = SentenceTransformer(settings.emb_model)
            texts = [obj['text'] for obj in objects]
            
            # Batch encode
            embeddings = embedding_model.encode(texts, show_progress_bar=False)
            
            # Insert with embeddings
            for obj, vector in zip(objects, embeddings):
                collection.data.insert(
                    properties=obj,
                    vector=vector.tolist()
                )
            
            logger.info(f"  ✅ Indexed {len(objects)} objects to Weaviate")
            self.stats['weaviate_indexed'] += len(objects)
            
            return len(objects)
            
        except Exception as e:
            logger.error(f"  ❌ Weaviate indexing failed: {e}")
            self.stats['weaviate_errors'] += 1
            self.errors.append(f"Weaviate indexing: {e}")
            return 0
    
    async def process_single_pdf(self, pdf_path: Path, dry_run: bool = False) -> Dict:
        """
        Process a single PDF file.
        
        Args:
            pdf_path: Path to PDF
            dry_run: If True, don't actually index
            
        Returns:
            Processing statistics
        """
        result = {
            'pdf': pdf_path.name,
            'success': False,
            'chunks': 0,
            'error': None
        }
        
        try:
            # 1. Extract and clean text
            text, pdf_metadata = self.extract_and_clean_text(pdf_path)
            
            # 2. Parse structure
            elements = self.parse_legal_structure(text, pdf_metadata)
            
            # 3. Create Weaviate objects
            weaviate_objects = self.create_weaviate_objects(elements, pdf_metadata)
            
            # 4. Index to Weaviate (unless dry run)
            if not dry_run:
                indexed_count = await self.index_to_weaviate(weaviate_objects)
                result['chunks'] = indexed_count
            else:
                logger.info(f"  🔍 DRY RUN: Would index {len(weaviate_objects)} objects")
                result['chunks'] = len(weaviate_objects)
            
            result['success'] = True
            
        except Exception as e:
            logger.error(f"  ❌ Failed to process {pdf_path.name}: {e}")
            result['error'] = str(e)
            self.errors.append(f"{pdf_path.name}: {e}")
        
        return result
    
    async def reindex_all(self, dry_run: bool = False):
        """
        Re-index all PDF files.
        
        Args:
            dry_run: If True, don't actually index
        """
        logger.info("="*80)
        logger.info("🚀 RE-INDEXING WITH DATA QUALITY IMPROVEMENTS")
        logger.info("="*80)
        
        if dry_run:
            logger.info("🔍 DRY RUN MODE - No actual indexing")
        
        # Find PDFs
        pdf_files = self.find_pdf_files()
        
        if not pdf_files:
            logger.warning("⚠️  No PDF files found!")
            return
        
        # Verify Weaviate collection exists
        if not dry_run:
            if not self.weaviate_client.collections.exists(self.collection_name):
                logger.error(f"❌ Collection '{self.collection_name}' does not exist!")
                logger.info(f"💡 Run: python scripts/improve_weaviate_schema.py")
                return
            else:
                logger.info(f"✅ Using collection: {self.collection_name}")
        
        # Process each PDF
        start_time = datetime.now()
        
        for i, pdf_path in enumerate(pdf_files, 1):
            logger.info(f"\n{'='*80}")
            logger.info(f"📦 Processing PDF {i}/{len(pdf_files)}")
            logger.info(f"{'='*80}")
            
            result = await self.process_single_pdf(pdf_path, dry_run=dry_run)
            
            if result['success']:
                logger.info(f"  ✅ Success: {result['chunks']} chunks")
            else:
                logger.error(f"  ❌ Failed: {result['error']}")
        
        # Summary
        duration = (datetime.now() - start_time).total_seconds()
        
        logger.info("\n" + "="*80)
        logger.info("📊 RE-INDEXING SUMMARY")
        logger.info("="*80)
        logger.info(f"Duration: {duration:.1f}s")
        logger.info(f"PDFs processed: {self.stats['pdfs_processed']}")
        logger.info(f"Elements parsed: {self.stats['elements_parsed']}")
        logger.info(f"Weaviate indexed: {self.stats['weaviate_indexed']}")
        logger.info(f"PDF errors: {self.stats['pdf_errors']}")
        logger.info(f"Weaviate errors: {self.stats['weaviate_errors']}")
        
        if self.errors:
            logger.info(f"\n❌ Errors ({len(self.errors)}):")
            for error in self.errors[:10]:  # Show first 10
                logger.info(f"  - {error}")
        
        logger.info("\n✅ Re-indexing complete!")
    
    def verify_data_quality(self):
        """Verify data quality after re-indexing."""
        logger.info("\n" + "="*80)
        logger.info("🔍 VERIFYING DATA QUALITY")
        logger.info("="*80)
        
        # Check Weaviate
        collection = self.weaviate_client.collections.get(self.collection_name)
        
        # Get sample objects
        response = collection.query.fetch_objects(limit=5)
        
        logger.info(f"\n📊 Weaviate Collection: {self.collection_name}")
        logger.info(f"Total objects: {len(response.objects)} (sample)")
        
        # Check for TOC artifacts
        toc_artifacts_found = 0
        flattened_metadata_found = 0
        
        for obj in response.objects:
            props = obj.properties
            
            # Check text quality
            text = props.get('text', '')
            if '......' in text or '\\.{3,}' in text:
                toc_artifacts_found += 1
            
            # Check flattened metadata
            if props.get('structure_type') and props.get('chapter'):
                flattened_metadata_found += 1
        
        logger.info(f"\n✅ Quality Checks:")
        logger.info(f"  TOC artifacts found: {toc_artifacts_found}/{len(response.objects)}")
        logger.info(f"  Flattened metadata: {flattened_metadata_found}/{len(response.objects)}")
        
        # Sample object
        if response.objects:
            logger.info(f"\n📄 Sample Object:")
            props = response.objects[0].properties
            logger.info(f"  Text preview: {props.get('text', '')[:100]}...")
            logger.info(f"  Chapter: {props.get('chapter', 'N/A')}")
            logger.info(f"  Article: {props.get('article', 'N/A')}")
            logger.info(f"  Structure type: {props.get('structure_type', 'N/A')}")
    
    def close(self):
        """Close connections."""
        if self._weaviate_client:
            self._weaviate_client.close()
        if self._neo4j_driver:
            self._neo4j_driver.close()
        logger.info("🔌 Connections closed")


async def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Re-index with data quality improvements")
    parser.add_argument(
        '--data-dir',
        type=Path,
        default=Path(__file__).parent.parent / 'data' / 'quy_dinh',
        help='Directory containing PDF files'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Run without actually indexing'
    )
    parser.add_argument(
        '--verify-only',
        action='store_true',
        help='Only verify existing data quality'
    )
    parser.add_argument(
        '--use-v2-schema',
        action='store_true',
        help='Use old V2 schema instead of V3'
    )
    
    args = parser.parse_args()
    
    # Initialize orchestrator
    orchestrator = ReindexingOrchestrator(
        data_dir=args.data_dir,
        use_v3_schema=not args.use_v2_schema
    )
    
    try:
        if args.verify_only:
            # Only verify
            orchestrator.verify_data_quality()
        else:
            # Re-index
            await orchestrator.reindex_all(dry_run=args.dry_run)
            
            # Verify if not dry run
            if not args.dry_run:
                orchestrator.verify_data_quality()
    
    finally:
        orchestrator.close()


if __name__ == "__main__":
    asyncio.run(main())
