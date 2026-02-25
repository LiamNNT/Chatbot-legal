"""
Reasoning feature: Symbolic Verification Pipeline for legal Q&A.

Reference:
  Rademaker, A. et al. (2024) "Deductive Verification of LLM generated
  SPARQL queries" — adapted for Cypher/Neo4j.

Pipeline stages:
  A. QuestionSpec extraction
  1. Cypher generation (LLM)
  2. Cypher verification (deterministic rules)
  3. Execute Cypher on KG (Neo4j)
  4. Answer generation (LLM reformulates KG data)
  C. Answer verification (deterministic rules)
"""

from .models import (
    AnswerType,
    QuestionIntent,
    QuestionSpec,
    GeneratedCypher,
    EntityMapping,
    CypherVerificationResult,
    VerificationStatus,
    RuleCheckResult,
    KGResult,
    KGRecord,
    StructuredAnswer,
    ArticleRef,
    AmountRange,
    AnswerVerdict,
    AnswerVerdictStatus,
    VerificationPipelineResult,
)
from .pipeline import LegalVerificationPipeline
from .question_spec import QuestionSpecExtractor
from .query_generator import CypherQueryGenerator
from .query_verifier import CypherQueryVerifier
from .kg_executor import KGExecutor
from .answer_generator import AnswerGenerator
from .answer_verifier import AnswerVerifier

__all__ = [
    # Pipeline
    "LegalVerificationPipeline",
    # Stage A
    "QuestionSpecExtractor",
    "QuestionSpec",
    "AnswerType",
    "QuestionIntent",
    # Stage 1
    "CypherQueryGenerator",
    "GeneratedCypher",
    "EntityMapping",
    # Stage 2
    "CypherQueryVerifier",
    "CypherVerificationResult",
    "VerificationStatus",
    "RuleCheckResult",
    # Stage 3
    "KGExecutor",
    "KGResult",
    "KGRecord",
    # Stage 4
    "AnswerGenerator",
    "StructuredAnswer",
    "ArticleRef",
    "AmountRange",
    # Stage C
    "AnswerVerifier",
    "AnswerVerdict",
    "AnswerVerdictStatus",
    # End-to-end
    "VerificationPipelineResult",
]
