"""
Post-processing module for extraction results.

This module handles:
1. Content Truncation Detection & Repair
2. Self-referencing Relations Removal
3. Chapter-Article Relations Validation
4. Chapter full_text Deduplication
5. Data Quality Validation

Author: AI Assistant
Date: 2025-12-28
"""

import re
import logging
from typing import Dict, Any, List, Tuple, Optional
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


# =============================================================================
# Constants
# =============================================================================

# Patterns that indicate truncated content
TRUNCATION_PATTERNS = [
    r',\s*$',                           # Ends with comma
    r'tại\s+[Kk]hoản\s*$',              # "tại Khoản" without number
    r'tại\s+[Đđ]iều\s*$',               # "tại Điều" without number
    r'theo\s+[Qq]uy\s+định\s*$',        # "theo quy định" incomplete
    r'như\s+sau\s*:\s*$',               # "như sau:" without content
    r'bao\s+gồm\s*:\s*$',               # "bao gồm:" without content
    r'[;:]\s*$',                         # Ends with semicolon or colon
    r'\.\.\.\s*$',                       # Ends with ellipsis
    r'và\s*$',                           # Ends with "và"
    r'hoặc\s*$',                         # Ends with "hoặc"
    r'gồm\s*$',                          # Ends with "gồm"
    r'có\s*$',                           # Ends with "có"
    r'là\s*$',                           # Ends with "là"
    r'được\s*$',                         # Ends with "được"
    r'phải\s*$',                         # Ends with "phải"
]

# Standard chapter-article mapping for Quy chế Đào tạo UIT
CHAPTER_ARTICLE_MAPPING = {
    1: list(range(1, 10)),      # Chương 1: Điều 1-9
    2: list(range(10, 20)),     # Chương 2: Điều 10-19  
    3: list(range(20, 28)),     # Chương 3: Điều 20-27
    4: list(range(28, 31)),     # Chương 4: Điều 28-30
    5: list(range(31, 35)),     # Chương 5: Điều 31-34
    6: list(range(35, 40)),     # Chương 6: Điều 35+ (điều khoản thi hành)
}


@dataclass
class PostProcessingStats:
    """Statistics from post-processing."""
    truncated_nodes_detected: int = 0
    truncated_nodes_fixed: int = 0
    self_relations_removed: int = 0
    invalid_relations_fixed: int = 0
    chapter_text_cleaned: int = 0
    duplicate_relations_removed: int = 0
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)


class ExtractionPostProcessor:
    """
    Post-processor for extraction results.
    
    Fixes common issues:
    - Content truncation
    - Self-referencing relations
    - Invalid chapter-article mappings
    - Duplicate content in chapters
    """
    
    def __init__(self):
        self.stats = PostProcessingStats()
    
    def process(self, extraction_result: Dict[str, Any]) -> Tuple[Dict[str, Any], PostProcessingStats]:
        """
        Main entry point for post-processing.
        
        Args:
            extraction_result: Raw extraction result dict
            
        Returns:
            Tuple of (cleaned result, processing stats)
        """
        self.stats = PostProcessingStats()
        
        structure = extraction_result.get("structure", extraction_result)
        
        # Step 1: Detect and report truncation issues
        logger.info("📝 Step 1: Detecting truncated content...")
        self._detect_truncation(structure)
        
        # Step 2: Remove self-referencing relations
        logger.info("🔗 Step 2: Removing self-referencing relations...")
        structure = self._remove_self_relations(structure)
        
        # Step 3: Fix chapter-article relations
        logger.info("🔧 Step 3: Fixing chapter-article relations...")
        structure = self._fix_chapter_article_relations(structure)
        
        # Step 4: Clean chapter full_text (remove duplicate article content)
        logger.info("🧹 Step 4: Cleaning chapter full_text...")
        structure = self._clean_chapter_fulltext(structure)
        
        # Step 5: Remove duplicate relations
        logger.info("🗑️ Step 5: Removing duplicate relations...")
        structure = self._remove_duplicate_relations(structure)
        
        # Update structure in result
        if "structure" in extraction_result:
            extraction_result["structure"] = structure
        else:
            extraction_result = structure
        
        # Add post-processing stats
        extraction_result["post_processing_stats"] = {
            "truncated_nodes_detected": self.stats.truncated_nodes_detected,
            "truncated_nodes_fixed": self.stats.truncated_nodes_fixed,
            "self_relations_removed": self.stats.self_relations_removed,
            "invalid_relations_fixed": self.stats.invalid_relations_fixed,
            "chapter_text_cleaned": self.stats.chapter_text_cleaned,
            "duplicate_relations_removed": self.stats.duplicate_relations_removed,
            "errors": self.stats.errors,
            "warnings": self.stats.warnings
        }
        
        logger.info(f"✅ Post-processing complete: "
                   f"{self.stats.self_relations_removed} self-refs removed, "
                   f"{self.stats.invalid_relations_fixed} relations fixed, "
                   f"{self.stats.truncated_nodes_detected} truncations detected")
        
        return extraction_result, self.stats
    
    def _detect_truncation(self, structure: Dict[str, Any]) -> None:
        """Detect nodes with truncated content."""
        
        for node_type in ["articles", "clauses", "chapters"]:
            nodes = structure.get(node_type, [])
            
            for node in nodes:
                full_text = node.get("full_text", "")
                node_id = node.get("id", "unknown")
                
                # Check for truncation patterns
                for pattern in TRUNCATION_PATTERNS:
                    if re.search(pattern, full_text):
                        self.stats.truncated_nodes_detected += 1
                        self.stats.warnings.append(
                            f"Truncated content in {node_id}: ends with pattern '{pattern}'"
                        )
                        
                        # Mark node as truncated
                        if "metadata" not in node:
                            node["metadata"] = {}
                        node["metadata"]["is_truncated"] = True
                        node["metadata"]["truncation_pattern"] = pattern
                        break
    
    def _remove_self_relations(self, structure: Dict[str, Any]) -> Dict[str, Any]:
        """Remove relations where source == target."""
        
        relations = structure.get("relations", [])
        cleaned_relations = []
        
        for rel in relations:
            source = rel.get("source", "")
            target = rel.get("target", "")
            
            if source == target:
                self.stats.self_relations_removed += 1
                logger.debug(f"Removed self-relation: {source} -> {target}")
            else:
                cleaned_relations.append(rel)
        
        structure["relations"] = cleaned_relations
        return structure
    
    def _fix_chapter_article_relations(self, structure: Dict[str, Any]) -> Dict[str, Any]:
        """Fix chapter-article relations based on article numbers."""
        
        relations = structure.get("relations", [])
        articles = structure.get("articles", [])
        
        # Build article number -> article id map
        article_map = {}
        for article in articles:
            article_num = article.get("metadata", {}).get("article_number")
            if article_num:
                article_map[article_num] = article.get("id")
        
        # Check and fix relations
        fixed_relations = []
        existing_relations = set()
        
        for rel in relations:
            source = rel.get("source", "")
            target = rel.get("target", "")
            rel_type = rel.get("type", "")
            
            # Skip non-CONTAINS relations
            if rel_type != "CONTAINS":
                fixed_relations.append(rel)
                continue
            
            # Check if this is a chapter -> article relation
            if source.startswith("chuong_") and target.startswith("dieu_"):
                # Extract article number
                article_match = re.search(r'dieu_(\d+)', target)
                if article_match:
                    article_num = int(article_match.group(1))
                    
                    # Determine correct chapter
                    correct_chapter = self._get_chapter_for_article(article_num)
                    correct_chapter_id = f"chuong_{correct_chapter}"
                    
                    if source != correct_chapter_id:
                        # Fix the relation
                        self.stats.invalid_relations_fixed += 1
                        logger.debug(f"Fixed relation: {source} -> {target} should be {correct_chapter_id} -> {target}")
                        source = correct_chapter_id
                        rel["source"] = source
            
            # Deduplicate
            rel_key = (source, target, rel_type)
            if rel_key not in existing_relations:
                existing_relations.add(rel_key)
                fixed_relations.append(rel)
        
        structure["relations"] = fixed_relations
        return structure
    
    def _get_chapter_for_article(self, article_num: int) -> int:
        """Determine which chapter an article belongs to."""
        
        for chapter_num, article_range in CHAPTER_ARTICLE_MAPPING.items():
            if article_num in article_range:
                return chapter_num
        
        # Default: use heuristic based on article number
        if article_num <= 9:
            return 1
        elif article_num <= 19:
            return 2
        elif article_num <= 27:
            return 3
        elif article_num <= 30:
            return 4
        elif article_num <= 34:
            return 5
        else:
            return 6
    
    def _clean_chapter_fulltext(self, structure: Dict[str, Any]) -> Dict[str, Any]:
        """
        Clean chapter full_text to only contain chapter title and introduction,
        not the full content of articles.
        """
        
        chapters = structure.get("chapters", [])
        
        for chapter in chapters:
            full_text = chapter.get("full_text", "")
            chapter_id = chapter.get("id", "")
            
            if not full_text:
                continue
            
            # Find where first article starts
            first_article_match = re.search(r'Điều\s+\d+', full_text)
            
            if first_article_match:
                # Keep only content before first article
                intro_text = full_text[:first_article_match.start()].strip()
                
                # If intro is too short, keep a summary
                if len(intro_text) < 50:
                    intro_text = chapter.get("title", chapter_id)
                
                # Limit length
                if len(intro_text) > 500:
                    intro_text = intro_text[:500] + "..."
                
                chapter["full_text"] = intro_text
                self.stats.chapter_text_cleaned += 1
                logger.debug(f"Cleaned {chapter_id} full_text: {len(full_text)} -> {len(intro_text)} chars")
        
        structure["chapters"] = chapters
        return structure
    
    def _remove_duplicate_relations(self, structure: Dict[str, Any]) -> Dict[str, Any]:
        """Remove duplicate relations."""
        
        relations = structure.get("relations", [])
        seen = set()
        unique_relations = []
        
        for rel in relations:
            key = (rel.get("source"), rel.get("target"), rel.get("type"))
            
            if key not in seen:
                seen.add(key)
                unique_relations.append(rel)
            else:
                self.stats.duplicate_relations_removed += 1
        
        structure["relations"] = unique_relations
        return structure


# =============================================================================
# Convenience function
# =============================================================================

def post_process_extraction(extraction_result: Dict[str, Any]) -> Tuple[Dict[str, Any], PostProcessingStats]:
    """
    Convenience function to post-process extraction results.
    
    Args:
        extraction_result: Raw extraction result
        
    Returns:
        Tuple of (cleaned result, stats)
    """
    processor = ExtractionPostProcessor()
    return processor.process(extraction_result)
