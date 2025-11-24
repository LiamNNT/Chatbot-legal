"""
LLM-Guided Relation Extraction for CatRAG.

This module implements relation extraction using LLMs (GPT-4, Gemini, etc.)
guided by the CatRAG schema and Vietnamese academic text patterns.

Week 2 - Task B1: LLM Relation Extraction
Priority: P0 (Critical - CatRAG Principle #2)

Key Features:
- Vietnamese-optimized prompts
- Schema-guided extraction (only valid relation types)
- Confidence scoring
- Evidence tracking
- Validation pipeline
"""

import json
import logging
import yaml
from pathlib import Path
from typing import List, Dict, Any, Optional
from dataclasses import dataclass

from core.domain.graph_models import (
    Entity,
    Relation,
    NodeCategory,
    RelationshipType,
)
from adapters.llm.llm_client import LLMClient, LLMResponse

logger = logging.getLogger(__name__)


@dataclass
class ExtractionResult:
    """Result of relation extraction"""
    relations: List[Relation]
    raw_response: str
    tokens_used: int
    cost_usd: float
    errors: List[str]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "relations_count": len(self.relations),
            "relations": [r.to_dict() for r in self.relations],
            "tokens_used": self.tokens_used,
            "cost_usd": round(self.cost_usd, 4),
            "error_count": len(self.errors),
        }


class LLMRelationExtractor:
    """
    LLM-guided relation extraction for CatRAG.
    
    Uses GPT-4 or other LLMs to extract relationships between entities
    from Vietnamese academic text, guided by the CatRAG schema.
    
    Example:
        ```python
        # Initialize with OpenAI client
        llm_client = OpenAIClient(api_key="sk-...")
        extractor = LLMRelationExtractor(llm_client)
        
        # Extract relations from text
        text = "Môn IT003 cần hoàn thành IT002 và IT001 trước"
        entities = [...]  # Extracted entities
        
        result = await extractor.extract_relations(text, entities)
        
        print(f"Found {len(result.relations)} relations")
        for rel in result.relations:
            print(f"{rel.source.text} --{rel.rel_type}--> {rel.target.text}")
        ```
    """
    
    def __init__(
        self,
        llm_client: LLMClient,
        prompts_path: Optional[Path] = None
    ):
        """
        Initialize LLM relation extractor.
        
        Args:
            llm_client: LLM client for API calls
            prompts_path: Path to prompts YAML file
        """
        self.llm_client = llm_client
        
        # Load prompts
        if prompts_path is None:
            prompts_path = Path(__file__).parent.parent / "config" / "prompts" / "relation_extraction.yaml"
        
        self.prompts = self._load_prompts(prompts_path)
        
        # Cache for parsed responses
        self._response_cache: Dict[str, List[Relation]] = {}
    
    def _load_prompts(self, path: Path) -> Dict[str, Any]:
        """Load prompts from YAML file"""
        try:
            with open(path, 'r', encoding='utf-8') as f:
                prompts = yaml.safe_load(f)
            logger.info(f"Loaded prompts from {path}")
            return prompts
        except Exception as e:
            logger.error(f"Failed to load prompts: {e}")
            # Return default prompts
            return {
                "relation_extraction_prompt": self._get_default_prompt()
            }
    
    def _get_default_prompt(self) -> str:
        """Get default extraction prompt (fallback if YAML not loaded)"""
        return """
You are an expert in analyzing academic documents.

Extract relationships from the following Vietnamese text:
{text}

Detected entities: {entities}

Return JSON array with format:
[{{"source_entity": "...", "source_category": "...", "relation_type": "...", "target_entity": "...", "target_category": "...", "confidence": 0.95, "evidence": "..."}}]
"""
    
    async def extract_relations(
        self,
        text: str,
        entities: List[Entity],
        use_few_shot: bool = True
    ) -> ExtractionResult:
        """
        Extract relations from text using LLM.
        
        Args:
            text: Input text to analyze
            entities: Entities already extracted from text
            use_few_shot: Whether to use few-shot examples
            
        Returns:
            ExtractionResult with extracted relations
        """
        # Check cache
        cache_key = self._make_cache_key(text)
        if cache_key in self._response_cache:
            logger.info("Using cached extraction result")
            return ExtractionResult(
                relations=self._response_cache[cache_key],
                raw_response="(cached)",
                tokens_used=0,
                cost_usd=0.0,
                errors=[]
            )
        
        # Build prompt
        prompt = self._build_prompt(text, entities, use_few_shot)
        
        # Call LLM
        try:
            logger.info(f"Calling LLM for relation extraction ({len(text)} chars, {len(entities)} entities)")
            
            response = await self.llm_client.complete(
                prompt=prompt,
                temperature=0.1,  # Low temp for deterministic extraction
                max_tokens=2000
            )
            
            logger.info(f"LLM response: {response.tokens_used} tokens, ${response.cost_usd:.4f}")
            
            # Parse response
            relations, errors = self._parse_llm_response(response.text, entities)
            
            # Validate relations
            validated_relations = [
                rel for rel in relations
                if self._validate_relation(rel)
            ]
            
            if len(validated_relations) < len(relations):
                logger.warning(
                    f"Filtered {len(relations) - len(validated_relations)} invalid relations"
                )
            
            # Cache result
            self._response_cache[cache_key] = validated_relations
            
            return ExtractionResult(
                relations=validated_relations,
                raw_response=response.text,
                tokens_used=response.tokens_used,
                cost_usd=response.cost_usd,
                errors=errors
            )
            
        except Exception as e:
            logger.error(f"LLM extraction failed: {e}")
            return ExtractionResult(
                relations=[],
                raw_response="",
                tokens_used=0,
                cost_usd=0.0,
                errors=[str(e)]
            )
    
    def _build_prompt(
        self,
        text: str,
        entities: List[Entity],
        use_few_shot: bool = True
    ) -> str:
        """
        Build extraction prompt.
        
        Args:
            text: Input text
            entities: Extracted entities
            use_few_shot: Include few-shot examples
            
        Returns:
            Complete prompt string
        """
        # Get base prompt
        base_prompt = self.prompts.get(
            "relation_extraction_prompt",
            self._get_default_prompt()
        )
        
        # Build entity context
        entity_context = self._build_entity_context(entities)
        
        # Fill in template
        prompt = base_prompt.format(
            text=text,
            entities=entity_context
        )
        
        # Add few-shot examples
        if use_few_shot and "few_shot_examples" in self.prompts:
            examples = self.prompts["few_shot_examples"]
            few_shot_text = "\n\n**FEW-SHOT EXAMPLES:**\n"
            
            for i, example in enumerate(examples[:2], 1):  # Limit to 2 examples
                few_shot_text += f"\nExample {i}:\n"
                few_shot_text += f"Input: {example['input']}\n"
                few_shot_text += f"Output: {example['output']}\n"
            
            # Insert examples before the text section
            prompt = prompt.replace(
                "**TEXT TO ANALYZE (Vietnamese):**",
                few_shot_text + "\n**TEXT TO ANALYZE (Vietnamese):**"
            )
        
        return prompt
    
    def _build_entity_context(self, entities: List[Entity]) -> str:
        """
        Build entity context string for prompt.
        
        Args:
            entities: List of entities
            
        Returns:
            Formatted entity context
        """
        if not entities:
            return "(No entities detected previously)"
        
        # Group by category
        by_category: Dict[str, List[Entity]] = {}
        for entity in entities:
            if entity.type not in by_category:
                by_category[entity.type] = []
            by_category[entity.type].append(entity)
        
        # Format
        lines = []
        for category, ents in by_category.items():
            entity_texts = [
                f"{e.text} (confidence: {e.confidence:.2f})"
                for e in ents
            ]
            lines.append(f"- {category}: {', '.join(entity_texts)}")
        
        return "\n".join(lines)
    
    def _parse_llm_response(
        self,
        response_text: str,
        entities: List[Entity]
    ) -> tuple[List[Relation], List[str]]:
        """
        Parse LLM JSON response into Relation objects.
        
        Args:
            response_text: Raw LLM response
            entities: Reference entities for linking
            
        Returns:
            (list of relations, list of errors)
        """
        errors = []
        
        try:
            # Extract JSON from response (handle markdown code blocks)
            json_text = self._extract_json(response_text)
            
            # Parse JSON
            data = json.loads(json_text)
            
            if not isinstance(data, list):
                errors.append("Response is not a JSON array")
                return [], errors
            
            # Convert to Relation objects
            relations = []
            
            for item in data:
                try:
                    relation = self._json_to_relation(item, entities)
                    if relation:
                        relations.append(relation)
                except Exception as e:
                    errors.append(f"Failed to parse relation: {item} - {e}")
            
            return relations, errors
            
        except json.JSONDecodeError as e:
            errors.append(f"JSON parse error: {e}")
            logger.error(f"Invalid JSON response: {response_text[:200]}")
            return [], errors
        except Exception as e:
            errors.append(f"Unexpected error: {e}")
            return [], errors
    
    def _extract_json(self, text: str) -> str:
        """Extract JSON from text (handle markdown code blocks)"""
        # Remove markdown code blocks
        if "```json" in text:
            start = text.find("```json") + 7
            end = text.find("```", start)
            return text[start:end].strip()
        elif "```" in text:
            start = text.find("```") + 3
            end = text.find("```", start)
            return text[start:end].strip()
        else:
            # Find JSON array
            start = text.find("[")
            end = text.rfind("]") + 1
            if start >= 0 and end > start:
                return text[start:end]
            return text.strip()
    
    def _json_to_relation(
        self,
        data: Dict[str, Any],
        entities: List[Entity]
    ) -> Optional[Relation]:
        """
        Convert JSON dict to Relation object.
        
        Args:
            data: JSON data
            entities: Reference entities
            
        Returns:
            Relation object or None if invalid
        """
        # Find or create source entity
        source = self._find_or_create_entity(
            data.get("source_entity"),
            data.get("source_category"),
            entities
        )
        
        # Find or create target entity
        target = self._find_or_create_entity(
            data.get("target_entity"),
            data.get("target_category"),
            entities
        )
        
        if not source or not target:
            logger.warning(f"Cannot create relation: missing entities")
            return None
        
        # Create relation
        return Relation(
            source=source,
            target=target,
            rel_type=data.get("relation_type", "LIEN_QUAN"),
            confidence=float(data.get("confidence", 0.7)),
            metadata={
                "evidence": data.get("evidence", ""),
                "extracted_by": "llm",
                "model": self.llm_client.config.model,
            }
        )
    
    def _find_or_create_entity(
        self,
        text: str,
        category: str,
        entities: List[Entity]
    ) -> Optional[Entity]:
        """
        Find entity in list or create new one.
        
        Args:
            text: Entity text
            category: Entity category
            entities: List of existing entities
            
        Returns:
            Entity or None
        """
        if not text or not category:
            return None
        
        # Try to find exact match
        for entity in entities:
            if entity.text == text and entity.type == category:
                return entity
        
        # Try fuzzy match
        for entity in entities:
            if entity.type == category:
                # Normalize and compare
                if text.lower() in entity.text.lower() or entity.text.lower() in text.lower():
                    return entity
        
        # Create new entity
        return Entity(
            text=text,
            type=category,
            start=0,
            end=len(text),
            confidence=0.8,  # Medium confidence for LLM-extracted
            metadata={"created_by": "llm_extractor"}
        )
    
    def _validate_relation(self, relation: Relation) -> bool:
        """
        Validate extracted relation with strict type checking.
        
        Checks:
        - Confidence >= threshold
        - Valid relation type
        - Valid entity categories
        - Relationship type matches entity types (e.g., DIEU_KIEN_TIEN_QUYET only between MON_HOC)
        - Has evidence
        - Not self-referencing
        
        Args:
            relation: Relation to validate
            
        Returns:
            True if valid, False otherwise
        """
        # Check confidence
        if relation.confidence < 0.7:
            logger.debug(f"Relation rejected: low confidence {relation.confidence}")
            return False
        
        # Check relation type
        try:
            rel_type_enum = RelationshipType(relation.rel_type)
        except ValueError:
            logger.warning(f"Invalid relation type: {relation.rel_type}")
            return False
        
        # Check entity categories (convert from UPPER_SNAKE_CASE to enum name)
        try:
            # Try direct lookup by name (e.g., "MON_HOC" -> NodeCategory.MON_HOC)
            if hasattr(NodeCategory, relation.source.type):
                source_category = getattr(NodeCategory, relation.source.type)
            else:
                # Try by value (e.g., "MON_HOC" -> NodeCategory.MON_HOC)
                source_category = NodeCategory(relation.source.type)
            
            if hasattr(NodeCategory, relation.target.type):
                target_category = getattr(NodeCategory, relation.target.type)
            else:
                target_category = NodeCategory(relation.target.type)
        except (ValueError, AttributeError) as e:
            logger.warning(f"Invalid entity category: {e}")
            return False
        
        # STRICT TYPE CHECKING based on relationship type
        # This prevents logic errors like "KHOA -> DIEU_KIEN_TIEN_QUYET -> MON_HOC"
        
        if relation.rel_type == "DIEU_KIEN_TIEN_QUYET":
            # Prerequisite: MUST be MON_HOC -> MON_HOC only
            if relation.source.type != "MON_HOC" or relation.target.type != "MON_HOC":
                logger.warning(
                    f"Invalid prerequisite relation: {relation.source.type} -> {relation.target.type}. "
                    f"DIEU_KIEN_TIEN_QUYET only allowed between MON_HOC nodes. "
                    f"Consider using THUOC_KHOA or QUAN_LY instead."
                )
                return False
        
        elif relation.rel_type == "THUOC_KHOA":
            # Belongs to department: MON_HOC/NGANH -> KHOA
            if relation.target.type != "KHOA":
                logger.warning(
                    f"Invalid THUOC_KHOA relation: target must be KHOA, got {relation.target.type}"
                )
                return False
            if relation.source.type not in ["MON_HOC", "NGANH"]:
                logger.warning(
                    f"Invalid THUOC_KHOA relation: source must be MON_HOC or NGANH, got {relation.source.type}"
                )
                return False
        
        elif relation.rel_type == "QUAN_LY":
            # Management: KHOA -> NGANH/MON_HOC
            if relation.source.type != "KHOA":
                logger.warning(
                    f"Invalid QUAN_LY relation: source must be KHOA, got {relation.source.type}"
                )
                return False
            if relation.target.type not in ["NGANH", "MON_HOC"]:
                logger.warning(
                    f"Invalid QUAN_LY relation: target must be NGANH or MON_HOC, got {relation.target.type}"
                )
                return False
        
        elif relation.rel_type == "CUA_NGANH":
            # Belongs to major: MON_HOC -> NGANH
            if relation.source.type != "MON_HOC" or relation.target.type != "NGANH":
                logger.warning(
                    f"Invalid CUA_NGANH relation: must be MON_HOC -> NGANH, got {relation.source.type} -> {relation.target.type}"
                )
                return False
        
        elif relation.rel_type == "AP_DUNG_CHO":
            # Applies to: QUY_DINH -> (SINH_VIEN/NGANH/KHOA)
            if relation.source.type != "QUY_DINH":
                logger.warning(
                    f"Invalid AP_DUNG_CHO relation: source must be QUY_DINH, got {relation.source.type}"
                )
                return False
            if relation.target.type not in ["SINH_VIEN", "NGANH", "KHOA"]:
                logger.warning(
                    f"Invalid AP_DUNG_CHO relation: target must be SINH_VIEN/NGANH/KHOA, got {relation.target.type}"
                )
                return False
        
        elif relation.rel_type in ["LIEN_QUAN_NOI_DUNG", "THAY_THE", "BO_SUNG"]:
            # Content relations: MON_HOC -> MON_HOC only
            if relation.source.type != "MON_HOC" or relation.target.type != "MON_HOC":
                logger.warning(
                    f"Invalid {relation.rel_type} relation: must be MON_HOC -> MON_HOC, got {relation.source.type} -> {relation.target.type}"
                )
                return False
        
        # Check evidence
        evidence = relation.metadata.get("evidence", "")
        if len(evidence) < 10:
            logger.debug(f"Relation rejected: insufficient evidence")
            return False
        
        # Check self-referencing
        if (relation.source.text == relation.target.text and
            relation.source.type == relation.target.type):
            logger.debug(f"Relation rejected: self-referencing")
            return False
        
        return True
    
    def _make_cache_key(self, text: str) -> str:
        """Create cache key from text"""
        import hashlib
        return hashlib.md5(text.encode()).hexdigest()
    
    def clear_cache(self):
        """Clear response cache"""
        self._response_cache.clear()
        logger.info("Cleared extraction cache")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get extraction statistics"""
        return {
            "cache_size": len(self._response_cache),
            **self.llm_client.get_usage_stats()
        }
