"""
Category-Guided Entity Extractor - POC Implementation

This module implements entity extraction following CatRAG approach:
- Guided by predefined categories from schema
- Top-down extraction instead of bottom-up
- Aligned with Neo4j graph categories

Team B - Week 1 POC
"""

import re
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
from core.domain.graph_models import Entity, NodeCategory


# Category-specific patterns (Vietnamese)
ENTITY_PATTERNS = {
    "MON_HOC": [
        # Course codes: IT001, CS101, etc.
        (r'\b([A-Z]{2}\d{3})\b', 0.95),
        # Vietnamese course names with common keywords
        (r'(Nhập môn|Lập trình|Cấu trúc|Cơ sở|Giải thuật|Mạng|Hệ điều hành)[\s\w]+', 0.85),
        # Pattern: "môn X"
        (r'môn\s+([\w\s]{3,30}?)(?=\s*[,.]|\s+là|\s+của)', 0.80),
    ],
    
    "KHOA": [
        # Faculty codes
        (r'\b(CNTT|KHTN|KHMT|KTMT|KTĐT|ĐTVT)\b', 0.95),
        # "Khoa X"
        (r'Khoa\s+([\w\s]+?)(?=\s*[,.]|$)', 0.90),
        # Full names
        (r'(Công nghệ thông tin|Khoa học máy tính|Khoa học tự nhiên)', 0.90),
    ],
    
    "NGANH": [
        # Major names (often similar to KHOA but more specific)
        (r'ngành\s+([\w\s]+?)(?=\s*[,.]|$)', 0.85),
        (r'(Công nghệ thông tin|Khoa học máy tính|An toàn thông tin|Mạng máy tính)', 0.85),
    ],
    
    "QUY_DINH": [
        # Regulation patterns
        (r'Quy\s+chế\s+\d+/\d{4}', 0.95),
        (r'Quy\s+định\s+số\s+\d+', 0.90),
        (r'(Quy chế|Quy định)\s+([\w\s]+?)(?=\s*[,.]|$)', 0.85),
    ],
    
    "DIEU_KIEN": [
        # GPA requirements
        (r'GPA\s+(?:tối thiểu\s+)?(\d+\.?\d*)', 0.90),
        (r'điểm trung bình\s+(?:tích lũy\s+)?(?:tối thiểu\s+)?(\d+\.?\d*)', 0.85),
        # Credit requirements
        (r'(\d+)\s+tín chỉ', 0.90),
        # General requirements
        (r'điều kiện\s+([\w\s]+?)(?=\s*[,.]|$)', 0.80),
    ],
    
    "SINH_VIEN": [
        # Student cohorts
        (r'\b(K\d{4})\b', 0.95),
        # Student types
        (r'(sinh viên\s+)?( chính quy|liên thông|chất lượng cao)', 0.85),
    ],
    
    "NAM_HOC": [
        # Academic years
        (r'năm học\s+(\d{4}(?:-\d{4})?)', 0.95),
        (r'\b(\d{4}-\d{4})\b', 0.85),
        (r'\b(20\d{2})\b', 0.70),  # Year only
    ],
    
    "KY_HOC": [
        # Semesters
        (r'\b(HK[123])\b', 0.95),
        (r'học kỳ\s+([123])', 0.90),
        (r'(kỳ\s+[123]|học kỳ\s+hè)', 0.85),
    ],
}


# Normalization mappings
NORMALIZATION_MAP = {
    "CNTT": "Công nghệ thông tin",
    "KHMT": "Khoa học máy tính",
    "KHTN": "Khoa học tự nhiên",
    "CTDL": "Cấu trúc dữ liệu",
    "GT": "Giải thuật",
    "CSDL": "Cơ sở dữ liệu",
    "MMT": "Mạng máy tính",
    "NMLT": "Nhập môn lập trình",
    "OOP": "Lập trình hướng đối tượng",
}


class CategoryGuidedEntityExtractor:
    """
    Category-guided entity extractor for CatRAG.
    
    Instead of generic NER, this extractor:
    1. Uses predefined categories from graph schema
    2. Applies category-specific patterns
    3. Normalizes entities to match graph nodes
    4. Returns entities ready for graph population
    """
    
    def __init__(
        self,
        categories: Optional[List[str]] = None,
        confidence_threshold: float = 0.7
    ):
        """
        Initialize extractor.
        
        Args:
            categories: Categories to extract (default: all)
            confidence_threshold: Minimum confidence for entity
        """
        self.categories = categories or list(ENTITY_PATTERNS.keys())
        self.confidence_threshold = confidence_threshold
        self.patterns = {cat: ENTITY_PATTERNS[cat] for cat in self.categories}
    
    def extract(self, text: str) -> Dict[str, List[Entity]]:
        """
        Extract entities from text grouped by category.
        
        This is the main method aligned with CatRAG approach.
        
        Args:
            text: Input text
            
        Returns:
            Dictionary mapping category to list of entities
            
        Example:
            >>> extractor = CategoryGuidedEntityExtractor()
            >>> entities = extractor.extract("Môn IT001 - Nhập môn lập trình thuộc khoa CNTT")
            >>> entities["MON_HOC"]
            [Entity(text="IT001", type="MON_HOC", ...)]
        """
        results = {}
        
        for category in self.categories:
            entities = self._extract_category(text, category)
            if entities:
                results[category] = entities
        
        return results
    
    def extract_by_category(
        self,
        text: str,
        target_categories: List[str]
    ) -> Dict[str, List[Entity]]:
        """
        Extract only specific categories.
        
        Useful for intent-based extraction:
        - TIEN_QUYET intent → extract only MON_HOC
        - DIEU_KIEN_TOT_NGHIEP intent → extract MON_HOC + DIEU_KIEN
        
        Args:
            text: Input text
            target_categories: Categories to extract
            
        Returns:
            Dictionary of entities by category
        """
        results = {}
        
        for category in target_categories:
            if category in self.patterns:
                entities = self._extract_category(text, category)
                if entities:
                    results[category] = entities
        
        return results
    
    def _extract_category(self, text: str, category: str) -> List[Entity]:
        """Extract entities for a specific category"""
        entities = []
        seen_texts = set()  # Avoid duplicates
        
        if category not in self.patterns:
            return entities
        
        for pattern, confidence in self.patterns[category]:
            for match in re.finditer(pattern, text, re.IGNORECASE):
                entity_text = match.group(1) if match.groups() else match.group(0)
                entity_text = entity_text.strip()
                
                # Skip if too short or already seen
                if len(entity_text) < 2 or entity_text in seen_texts:
                    continue
                
                # Apply normalization
                normalized = self._normalize(entity_text, category)
                
                # Create entity
                entity = Entity(
                    text=entity_text,
                    type=category,
                    start=match.start(),
                    end=match.end(),
                    confidence=confidence,
                    normalized=normalized,
                    metadata={"pattern": pattern}
                )
                
                # Filter by confidence
                if entity.confidence >= self.confidence_threshold:
                    entities.append(entity)
                    seen_texts.add(entity_text)
        
        return entities
    
    def _normalize(self, text: str, category: str) -> Optional[str]:
        """Normalize entity text"""
        # Direct mapping
        if text in NORMALIZATION_MAP:
            return NORMALIZATION_MAP[text]
        
        # Category-specific normalization
        if category == "MON_HOC":
            # Course codes are already normalized
            if re.match(r'^[A-Z]{2}\d{3}$', text):
                return text.upper()
        
        elif category == "KHOA":
            # Normalize faculty codes
            return text.upper() if len(text) <= 6 else text
        
        elif category == "SINH_VIEN":
            # Normalize cohorts
            if re.match(r'^K\d{4}$', text):
                return text.upper()
        
        return None
    
    def extract_for_intent(
        self,
        text: str,
        intent: str
    ) -> Dict[str, List[Entity]]:
        """
        Extract entities based on query intent.
        
        Maps intents to relevant categories:
        - TIEN_QUYET → MON_HOC
        - DIEU_KIEN_TOT_NGHIEP → MON_HOC, NGANH, DIEU_KIEN
        - QUY_DINH_HOC_VU → QUY_DINH, SINH_VIEN
        
        This is CRITICAL for CatRAG routing!
        
        Args:
            text: Query text
            intent: Query intent (from Router Agent)
            
        Returns:
            Relevant entities for the intent
        """
        intent_category_map = {
            "tien_quyet": ["MON_HOC"],
            "mo_ta_mon_hoc": ["MON_HOC"],
            "dieu_kien_tot_nghiep": ["MON_HOC", "NGANH", "DIEU_KIEN"],
            "chuong_trinh_dao_tao": ["MON_HOC", "NGANH", "KHOA"],
            "quy_dinh_hoc_vu": ["QUY_DINH", "SINH_VIEN"],
            "hoc_phi": ["NGANH", "SINH_VIEN"],
        }
        
        target_categories = intent_category_map.get(intent, self.categories)
        
        return self.extract_by_category(text, target_categories)


# POC Demo
def demo_category_guided_extraction():
    """
    Demonstrate category-guided extraction.
    """
    print("=" * 60)
    print("🏷️  Category-Guided Entity Extraction - POC Demo")
    print("=" * 60)
    print()
    
    extractor = CategoryGuidedEntityExtractor()
    
    # Test cases
    test_cases = [
        {
            "text": "Môn IT001 - Nhập môn lập trình là môn cơ bản của ngành CNTT.",
            "intent": "mo_ta_mon_hoc"
        },
        {
            "text": "Để học IT003 bạn cần học IT002 trước. IT002 cần IT001 là điều kiện tiên quyết.",
            "intent": "tien_quyet"
        },
        {
            "text": "Quy chế 43/2024 quy định sinh viên K2024 cần GPA tối thiểu 2.0 và 120 tín chỉ để tốt nghiệp.",
            "intent": "dieu_kien_tot_nghiep"
        },
        {
            "text": "Khoa CNTT có các ngành Công nghệ thông tin và An toàn thông tin.",
            "intent": "chuong_trinh_dao_tao"
        }
    ]
    
    for i, test_case in enumerate(test_cases, 1):
        text = test_case["text"]
        intent = test_case["intent"]
        
        print(f"Test Case {i}:")
        print(f"  Query: \"{text}\"")
        print(f"  Intent: {intent}")
        print()
        
        # Extract entities
        entities = extractor.extract_for_intent(text, intent)
        
        print(f"  Extracted Entities:")
        for category, entity_list in entities.items():
            print(f"\n    {category}:")
            for entity in entity_list:
                normalized = f" → {entity.normalized}" if entity.normalized else ""
                print(f"      - \"{entity.text}\"{normalized} (confidence: {entity.confidence:.2f})")
        
        print("\n" + "-" * 60 + "\n")
    
    print("✅ Demo Complete!")
    print()
    print("💡 CatRAG Insights:")
    print("  1. Extraction is guided by predefined categories")
    print("  2. Different intents extract different entity types")
    print("  3. Entities are normalized to match graph nodes")
    print("  4. Ready for LLM-guided relation extraction (Week 2)")
    print()


if __name__ == "__main__":
    demo_category_guided_extraction()
