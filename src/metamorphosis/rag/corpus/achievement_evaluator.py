# =============================================================================
#  Filename: achievement_evaluator.py
#
#  Short Description: Evaluate achievements by mapping them to projects and
#                     estimating contribution levels with LLM support.
#
#  Creation date: 2025-09-10
#  Author: Asif Qamar
# =============================================================================

from __future__ import annotations

from typing import List, Optional
from icontract import require, ensure
from loguru import logger

from metamorphosis.datamodel import AchievementsList, Achievement
from metamorphosis.rag.corpus.project_data_models import (
    AchievementEvaluation,
    ContributionLevelLiteral,
)
from metamorphosis.rag.search.semantic_search import SemanticSearch
from metamorphosis.rag.vectordb.embedded_vectordb import EmbeddedVectorDB
from metamorphosis.rag.vectordb.embedder import SimpleTextEmbedder
from metamorphosis.model_registry import ModelRegistry


class AchievementEvaluator:
    """Contextualize achievements against projects and assess contribution level.

    The evaluator uses semantic search to map each achievement to the most
    relevant project(s), then prompts an LLM (from the `ModelRegistry`) to
    reason about the likely contribution level.
    """

    @require(lambda vector_db: isinstance(vector_db, EmbeddedVectorDB),
             "vector_db must be EmbeddedVectorDB")
    @require(lambda embedder: embedder is None or isinstance(embedder, SimpleTextEmbedder),
             "embedder must be SimpleTextEmbedder or None")
    def __init__(self, *, vector_db: EmbeddedVectorDB,
                 embedder: Optional[SimpleTextEmbedder] = None,
                 collection_name: str = "projects") -> None:
        self.embedder = embedder or SimpleTextEmbedder()
        self.semantic_search = SemanticSearch(
            embedder=self.embedder, vector_db=vector_db, collection_name=collection_name
        )
        self.models = ModelRegistry()

    # ------- helpers
    def _format_context(self, *, achievement: Achievement, top_k_texts: List[str]) -> str:
        return (
            "Achievement:\n"
            f"- title: {achievement.title}\n"
            f"- outcome: {achievement.outcome}\n"
            f"- impact_area: {achievement.impact_area}\n\n"
            "Candidate Projects:\n" + "\n".join([f"- {t}" for t in top_k_texts])
        )

    def _call_reasoning_model(self, *, context: str) -> ContributionLevelLiteral:
        # Use review_text_evaluator_llm as a reasoning-capable model by default
        llm = self.models.review_text_evaluator_llm
        prompt = (
            "You are an expert evaluator. Given an achievement and candidate projects, "
            "decide the employee contribution level: one of [Minor, Medium, Significant, Critical].\n\n"
            f"{context}\n\n"
            "Return only one word from the set above."
        )
        try:
            resp = llm.invoke(prompt)  # LangChain ChatOpenAI
            text = (resp.content or "").strip()
        except Exception as error:  # noqa: BLE001
            logger.warning(f"LLM call failed, defaulting to 'Medium': {error}")
            text = "Medium"

        normalized = text.split()[0].strip().capitalize()
        if normalized not in {"Minor", "Medium", "Significant", "Critical"}:
            normalized = "Medium"
        return normalized  # type: ignore[return-value]

    # ------- core API
    @require(lambda achievements: isinstance(achievements, AchievementsList) and len(achievements.items) > 0,
             "achievements must be a non-empty AchievementsList")
    @ensure(lambda result: isinstance(result, list), "Must return a list")
    def contextualize(self, *, achievements: AchievementsList,
                      limit: int = 10) -> List[AchievementEvaluation]:
        """Map each achievement to projects and estimate contribution level.

        Args:
            achievements: Structured list of achievements.
            limit: Max similar projects to consider per achievement.

        Returns:
            List of `AchievementEvaluation` objects.
        """
        evaluations: List[AchievementEvaluation] = []

        for ach in achievements.items:
            query = f"{ach.title}. {ach.outcome}"
            hits = self.semantic_search.search_with_text(
                query_text=query, limit=limit
            )

            if not hits:
                logger.info("No projects matched achievement: {}", ach.title)
                continue

            # Pick top-1 project by score for a concise judgment
            top_hit = hits[0]
            payload = top_hit.payload or {}
            project_text = payload.get("content", "")
            project_name = payload.get("name", "(unnamed)")
            top_k_texts = [h.payload.get("content", "") for h in hits if h.payload]

            context = self._format_context(achievement=ach, top_k_texts=top_k_texts)
            contribution = self._call_reasoning_model(context=context)

            from metamorphosis.rag.corpus.project_data_models import Project  # local import

            project = Project(
                name=project_name,
                text=project_text,
                department=payload.get("department", "Unknown"),
                impact_category=payload.get("impact_category", "Medium Impact"),
                effort_size=payload.get("effort_size", "Medium"),
            )

            evaluations.append(
                AchievementEvaluation(
                    achievement=ach,
                    project=project,
                    contribution=contribution,
                    rationale=None,
                )
            )

        return evaluations


