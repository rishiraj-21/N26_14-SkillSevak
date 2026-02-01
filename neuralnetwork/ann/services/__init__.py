"""
SkillSevak Services Module

This module contains the core AI/ML services:
- resume_parser: Extract text from PDF/DOCX files
- skill_extractor: Dynamic NLP-based skill extraction (NO HARDCODING!)
- embedding_service: Generate semantic embeddings
- matching_engine: Calculate match scores
- recommendations: Generate improvement suggestions

Per PRD.md: All services are designed to work for ANY industry,
not just tech. No hardcoded skill dictionaries.
"""

from .resume_parser import ResumeParser
from .skill_extractor import DynamicSkillExtractor, SkillCategory
from .embedding_service import EmbeddingService
from .matching_engine import MatchingEngine

__all__ = [
    'ResumeParser',
    'DynamicSkillExtractor',
    'SkillCategory',
    'EmbeddingService',
    'MatchingEngine',
]
