# =============================================================================
#  Filename: state.py
#
#  Short Description: State management for self-reviewer workflows.
#
#  Creation date: 2025-09-08
#  Author: Asif Qamar
# =============================================================================

"""State Management for Self-Reviewer Workflows.

This module defines the state structure and management utilities for
the LangGraph-based self-reviewer workflow system.
"""

from __future__ import annotations

from typing import Annotated, Optional

from typing_extensions import TypedDict
from langgraph.graph.message import add_messages

from metamorphosis.datamodel import AchievementsList, ReviewScorecard


class GraphState(TypedDict):
    """State definition for the LangGraph workflow.

    This TypedDict defines the structure of the state that flows through the LangGraph,
    containing all the data needed at each step of the workflow.

    Attributes:
        original_text: The original self-review input text from the employee.
        copy_edited_text: The grammar and clarity improved version.
        summary: The abstractive summary of the key insights.
        word_cloud_path: Path to the generated word cloud image file.
        achievements: The key achievements extracted from the text by an agent accessing an achievements extraction langgraph tool.
        review_scorecard: The review scorecard generated from the text by an agent accessing a review scorecard generation langgraph tool.
        review_complete: A flag indicating if the achievements list has at least 3 items.
        messages: List of messages for agent communication.
    """

    original_text: str
    copy_edited_text: Optional[str]
    summary: Optional[str]
    word_cloud_path: Optional[str]
    achievements: Optional[AchievementsList]
    review_scorecard: Optional[ReviewScorecard]
    messages: Annotated[list, add_messages]
    review_complete: Optional[bool]
