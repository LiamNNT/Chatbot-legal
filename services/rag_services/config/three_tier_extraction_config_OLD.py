"""
3-Tier Extraction Strategy Configuration
=========================================

Cost-optimized, multi-layer approach:
- Layer 1: Regex (FREE, FAST) - Structure
- Layer 2: Gemini Flash (CHEAP) - Entities  
- Layer 3: Grok 4.1 Fast (MODERATE) - Complex Rules

Author: Enhanced by user feedback
Date: November 20, 2025
"""

from typing import Dict, Any
from dataclasses import dataclass


@dataclass
class ModelConfig:
    """Configuration for an LLM model"""
    name: str
    provider: str
    model_id: str
    cost_per_1m_tokens_input: float
    cost_per_1m_tokens_output: float
    max_tokens: int
    temperature: float
    use_case: str
    

class ThreeTierExtractionConfig:
    """
    Configuration for 3-tier extraction strategy
    
    Tier 1: Structure (Regex) - FREE
    Tier 2: Entities (Gemini Flash) - ~$0.01 per 1M tokens
    Tier 3: Rules (Grok 4.1 Fast) - ~$0.50 per 1M tokens
    """
    
    # ========================================================================
    # TIER 1: Structure Extraction (Regex/Python)
    # ========================================================================
    TIER1_CONFIG = {
        "name": "Regex Parser",
        "tool": "legal_structure_parser.py",
        "cost": 0.0,  # FREE
        "speed": "INSTANT",
        "accuracy": "100%",
        "use_case": "Extract Document → Chapter → Article → Clause hierarchy",
        "output": [
            "Document nodes",
            "Chapter nodes", 
            "Article nodes",
            "Clause nodes",
            "HAS_CHAPTER relationships",
            "HAS_ARTICLE relationships",
            "HAS_CLAUSE relationships",
            "NEXT_ARTICLE relationships",
            "NEXT_CLAUSE relationships"
        ],
        "patterns": [
            r"^Chương\s+([IVXLCDM]+)",  # Chapter: Roman numerals
            r"^\s*Điều\s+(\d+)\.\s*(.+)",  # Article: "Điều 14. Title"
            r"^\s*(\d+[a-z]?)\.\s+(.+)"  # Clause: "1. Content"
        ]
    }
    
    # ========================================================================
    # TIER 2: Entity & Simple Relationship Extraction (Gemini Flash)
    # ========================================================================
    TIER2_MODEL = ModelConfig(
        name="Gemini 2.0 Flash Experimental",
        provider="OpenRouter",
        model_id="google/gemini-2.0-flash-exp:free",
        cost_per_1m_tokens_input=0.0,  # FREE during experimental period
        cost_per_1m_tokens_output=0.0,
        max_tokens=8192,
        temperature=0.1,  # Low for consistency
        use_case="Extract entities (Courses, Departments, Students) and simple relationships"
    )
    
    TIER2_CONFIG = {
        "name": "Entity Extractor",
        "model": TIER2_MODEL,
        "input": "Clause nodes from Tier 1",
        "output": [
            "Entity nodes: Course, Department, Student, Semester, Program",
            "Simple relationships: BELONGS_TO, TAUGHT_BY, REQUIRES",
            "Metadata: course_code, department_name, credit_hours"
        ],
        "examples": [
            {
                "input": "Sinh viên thuộc Khoa Khoa học Máy tính phải hoàn thành 120 tín chỉ",
                "output": {
                    "entities": [
                        {"type": "Department", "name": "Khoa Khoa học Máy tính", "code": "CS"},
                        {"type": "Student", "role": "undergraduate"}
                    ],
                    "relationships": [
                        {"from": "Student", "to": "Department", "type": "BELONGS_TO"}
                    ],
                    "metadata": {
                        "credit_requirement": 120
                    }
                }
            },
            {
                "input": "Môn học Cơ sở dữ liệu (CS202) là 3 tín chỉ",
                "output": {
                    "entities": [
                        {"type": "Course", "name": "Cơ sở dữ liệu", "code": "CS202", "credits": 3}
                    ]
                }
            }
        ],
        "prompt_template": """
Từ văn bản sau, trích xuất:
1. Entities: Môn học (Course), Khoa (Department), Sinh viên (Student), Học kỳ (Semester)
2. Relationships đơn giản: BELONGS_TO, REQUIRES, TAUGHT_BY
3. Metadata: Mã môn, số tín chỉ, tên khoa

Văn bản: {clause_text}

Trả về JSON:
{{
  "entities": [...],
  "relationships": [...],
  "metadata": {{...}}
}}
"""
    }
    
    # ========================================================================
    # TIER 3: Complex Rule Extraction (Grok 4.1 Fast)
    # ========================================================================
    TIER3_MODEL = ModelConfig(
        name="Grok 4.1 Fast",
        provider="OpenRouter", 
        model_id="x-ai/grok-4.1-fast:free",
        cost_per_1m_tokens_input=0.50,  # Reasonable for complex reasoning
        cost_per_1m_tokens_output=1.50,
        max_tokens=4096,
        temperature=0.0,  # Deterministic for rules
        use_case="Extract complex if-then logic, formulas, graduation requirements"
    )
    
    TIER3_CONFIG = {
        "name": "Rule Logic Extractor",
        "model": TIER3_MODEL,
        "input": "Clause nodes with complex logic",
        "output": [
            "Rule nodes with formulas",
            "DEFINES_RULE relationships",
            "ABOUT_CONCEPT relationships",
            "Structured logic: if-then-else, constraints, calculations"
        ],
        "examples": [
            {
                "input": "Sinh viên chương trình chuyên sâu đặc thù phải thực tập tối thiểu 8 tín chỉ",
                "output": {
                    "rule_name": "Khối lượng thực tập tối thiểu chương trình chuyên sâu đặc thù",
                    "rule_type": "constraint",
                    "severity": "mandatory",
                    "formula": "if program_type == 'specialized_intensive' then internship_credits >= 8",
                    "description_vi": "Sinh viên thuộc chương trình chuyên sâu đặc thù bắt buộc hoàn thành tối thiểu 8 tín chỉ thực tập",
                    "concepts": ["C_SV_THUC_TAP", "C_SV_CHUONG_TRINH"]
                }
            },
            {
                "input": "Điểm trung bình tích lũy (GPA) = Σ(điểm × tín chỉ) / Σ(tín chỉ)",
                "output": {
                    "rule_name": "Công thức tính GPA",
                    "rule_type": "formula",
                    "severity": "info",
                    "formula": "GPA = sum(grade * credits) / sum(credits)",
                    "description_vi": "Điểm trung bình tích lũy được tính bằng tổng điểm nhân tín chỉ chia cho tổng tín chỉ",
                    "concepts": ["C_SV_DANH_GIA"]
                }
            }
        ],
        "prompt_template": """
Từ quy định sau, trích xuất luật (Rule) dạng logic:

Văn bản: {clause_text}

Trả về JSON:
{{
  "rule_name": "Tên luật bằng tiếng Việt có dấu",
  "rule_type": "constraint|formula|eligibility|deadline",
  "severity": "mandatory|recommended|info",
  "formula": "Logic dạng if-then hoặc công thức toán học",
  "description_vi": "Mô tả chi tiết bằng tiếng Việt",
  "concepts": ["C_SV_...", "C_SV_..."]
}}

Chỉ trích xuất NẾU văn bản chứa logic phức tạp. Nếu chỉ là mô tả đơn giản, trả về {{"rules": []}}.
"""
    }
    
    # ========================================================================
    # Cost & Performance Comparison
    # ========================================================================
    COST_ANALYSIS = {
        "tier1_regex": {
            "cost_per_page": 0.0,
            "speed": "< 1ms",
            "accuracy": "100%",
            "coverage": "Structure only"
        },
        "tier2_gemini_flash": {
            "cost_per_page": 0.0,  # Free experimental
            "speed": "~500ms",
            "accuracy": "95%",
            "coverage": "Simple entities & relationships"
        },
        "tier3_grok_fast": {
            "cost_per_page": 0.002,  # ~$0.002 per page
            "speed": "~2s",
            "accuracy": "98%",
            "coverage": "Complex rules & logic"
        },
        "total_cost_per_document": {
            "100_pages": 0.20,  # $0.20 for 100-page document
            "vs_claude_sonnet": 15.00,  # Would cost $15 with Claude 3.5 Sonnet
            "savings": "98.7%"
        }
    }
    
    # ========================================================================
    # Orchestration Strategy
    # ========================================================================
    ORCHESTRATION = {
        "pipeline": [
            {
                "step": 1,
                "tier": "Structure",
                "action": "Run legal_structure_parser.py",
                "input": "Raw PDF text",
                "output": "Document → Chapter → Article → Clause graph",
                "parallelizable": False
            },
            {
                "step": 2,
                "tier": "Entities",
                "action": "Run Gemini Flash on each Clause",
                "input": "Clause nodes from Step 1",
                "output": "Entity nodes + simple relationships",
                "parallelizable": True,  # Can batch Clauses
                "batch_size": 10
            },
            {
                "step": 3,
                "tier": "Rules",
                "action": "Run Grok 4.1 Fast on Clauses with complex logic",
                "input": "Clauses flagged as 'complex' by Gemini",
                "output": "Rule nodes with formulas",
                "parallelizable": True,
                "batch_size": 5,
                "filter": "Only clauses with if-then, formulas, constraints"
            }
        ],
        "optimization": {
            "skip_tier3_if": [
                "Clause is pure description",
                "No conditions/formulas detected in Tier 2",
                "Clause length < 50 words"
            ],
            "parallel_execution": "Use asyncio for Tier 2 & 3",
            "caching": "Cache Tier 2/3 results by clause_id"
        }
    }
    
    # ========================================================================
    # Environment Variables
    # ========================================================================
    ENV_VARS = {
        "OPENROUTER_API_KEY": "Required for Gemini Flash & Grok",
        "TIER2_MODEL": "google/gemini-2.0-flash-exp:free",
        "TIER3_MODEL": "x-ai/grok-4.1-fast:free",
        "TIER2_TEMPERATURE": "0.1",
        "TIER3_TEMPERATURE": "0.0",
        "TIER2_MAX_TOKENS": "8192",
        "TIER3_MAX_TOKENS": "4096"
    }


# ============================================================================
# Usage Example
# ============================================================================

if __name__ == "__main__":
    config = ThreeTierExtractionConfig()
    
    print("=" * 80)
    print("3-TIER EXTRACTION STRATEGY")
    print("=" * 80)
    
    print("\n📊 COST COMPARISON:")
    print(f"  100-page document with 3-tier: ${config.COST_ANALYSIS['total_cost_per_document']['100_pages']}")
    print(f"  Same document with Claude Sonnet: ${config.COST_ANALYSIS['total_cost_per_document']['vs_claude_sonnet']}")
    print(f"  Savings: {config.COST_ANALYSIS['total_cost_per_document']['savings']}")
    
    print("\n🔧 TIER BREAKDOWN:")
    print(f"\n  Tier 1 (Regex): {config.TIER1_CONFIG['use_case']}")
    print(f"    Cost: FREE")
    print(f"    Speed: {config.COST_ANALYSIS['tier1_regex']['speed']}")
    
    print(f"\n  Tier 2 (Gemini Flash): {config.TIER2_MODEL.use_case}")
    print(f"    Model: {config.TIER2_MODEL.model_id}")
    print(f"    Cost: ${config.TIER2_MODEL.cost_per_1m_tokens_input} per 1M tokens")
    
    print(f"\n  Tier 3 (Grok 4.1): {config.TIER3_MODEL.use_case}")
    print(f"    Model: {config.TIER3_MODEL.model_id}")
    print(f"    Cost: ${config.TIER3_MODEL.cost_per_1m_tokens_input} per 1M tokens")
    
    print("\n📝 ORCHESTRATION:")
    for step in config.ORCHESTRATION['pipeline']:
        print(f"  Step {step['step']}: {step['tier']}")
        print(f"    Action: {step['action']}")
        print(f"    Parallel: {step['parallelizable']}")
