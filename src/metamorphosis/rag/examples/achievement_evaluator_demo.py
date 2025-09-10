# =============================================================================
#  Filename: achievement_evaluator_demo.py
#
#  Short Description: Demo - extract achievements from a sample review, then
#                     contextualize them against projects and print a rich table.
#
#  Creation date: 2025-09-10
#  Author: Asif Qamar
# =============================================================================

from __future__ import annotations

from pathlib import Path
from rich.table import Table
from rich.console import Console

# Make src importable when running as a script
import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from metamorphosis.mcp.text_modifiers import TextModifiers
from metamorphosis.rag.corpus.achievement_evaluator import AchievementEvaluator
from metamorphosis.rag.vectordb.embedded_vectordb import EmbeddedVectorDB
from metamorphosis.rag.vectordb.embedder import SimpleTextEmbedder


def main() -> bool:
    console = Console()
    console.print("🎯 Achievement Evaluation Demo", style="bold green")
    console.rule()

    # Load sample review text
    repo_root = Path(__file__).resolve().parents[4]
    review_path = repo_root / "sample_reviews" / "data_engineer_review.md"
    text = review_path.read_text(encoding="utf-8")

    # Extract achievements
    tm = TextModifiers()
    achievements = tm.extract_achievements(text=text)

    # Evaluate against projects
    vector_db = EmbeddedVectorDB()
    embedder = SimpleTextEmbedder()
    evaluator = AchievementEvaluator(vector_db=vector_db, embedder=embedder)
    evaluations = evaluator.contextualize(achievements=achievements, limit=10)

    # Render results table
    table = Table(title="Achievement Evaluations")
    table.add_column("#", justify="right")
    table.add_column("Achievement")
    table.add_column("Contribution")
    table.add_column("Name")
    table.add_column("Project (snippet)")
    table.add_column("Department")
    table.add_column("Impact")

    for idx, ev in enumerate(evaluations, start=1):
        ach = ev.achievement
        proj = ev.project
        snippet = (proj.text[:80] + "...") if len(proj.text) > 80 else proj.text
        table.add_row(
            str(idx),
            f"{ach.title}",
            ev.contribution,
            proj.name,
            snippet,
            proj.department,
            proj.impact_category,
        )

    console.print(table)
    console.print(f"Total evaluated: {len(evaluations)}", style="dim")
    return True


if __name__ == "__main__":
    ok = main()
    sys.exit(0 if ok else 1)


