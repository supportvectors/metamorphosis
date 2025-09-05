# =============================================================================
#  Filename: datamodel.py
#
#  Short Description: Centralized Pydantic data models used across Metamorphosis.
#
#  Creation date: 2025-09-04
#  Author: Asif Qamar
# =============================================================================

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


# models_extras.py
from typing import List, Literal, Optional

# ---------- Achievements ----------
ImpactArea = Literal[
    "reliability",
    "performance",
    "security",
    "cost",
    "revenue",
    "customer",
    "delivery_speed",
    "quality",
    "compliance",
    "team",
]


class Achievement(BaseModel):
    title: str = Field(..., description="≤12 words, concise label.")
    outcome: str = Field(..., description="≤40 words, outcome-focused description.")
    impact_area: ImpactArea
    metric_strings: List[str] = Field(
        default_factory=list, description="Copy numbers/units verbatim if present."
    )
    timeframe: Optional[str] = None  # e.g., 'H1 2025', 'Q3', 'year'
    ownership_scope: Optional[Literal["IC", "TechLead", "Manager", "Cross-team", "Org-wide"]] = None
    collaborators: List[str] = Field(default_factory=list)  # names/teams if explicitly mentioned


class AchievementsList(BaseModel):
    items: List[Achievement]
    size: int = Field(..., description="Token estimate of concatenated titles+outcomes.")
    unit: Literal["tokens"] = "tokens"


# ---------- Review Scorecard (for radar) ----------
class MetricScore(BaseModel):
    name: Literal[
        "OutcomeOverActivity",
        "QuantitativeSpecificity",
        "ClarityCoherence",
        "Conciseness",
        "OwnershipLeadership",
        "Collaboration",
    ]
    score: int = Field(..., ge=0, le=100)
    rationale: str = Field(..., description="One sentence; point to evidence from the text.")
    suggestion: str = Field(..., description="One improvement action; concrete and concise.")


Verdict = Literal["excellent", "strong", "mixed", "weak"]


class ReviewScorecard(BaseModel):
    metrics: List[MetricScore]  # length 6, in the order above
    overall: int = Field(..., ge=0, le=100)
    verdict: Verdict
    notes: List[str] = Field(default_factory=list)  # optional flags, e.g., “no metrics found”
    radar_labels: List[str]  # echo names for plotting
    radar_values: List[int]  # 6 integers (0-100)


class SummarizedText(BaseModel):
    """Structured summary output returned by summarization routines."""

    model_config = ConfigDict(extra="forbid")
    summarized_text: str = Field(
        ..., description="The generated abstractive summary text", min_length=1
    )
    size: int = Field(..., description="The size of the summary in tokens")


class CopyEditedText(BaseModel):
    """Rationalized text with typos and grammar errors corrected."""

    model_config = ConfigDict(extra="forbid")
    copy_edited_text: str = Field(
        ..., description="The lightly normalized and corrected text", min_length=1
    )
    size: int = Field(..., description="The size of the copy-edited text in tokens")
    is_edited: bool = Field(..., description="Whether the text was edited")


class InvokeRequest(BaseModel):
    """Request model for synchronous self-review processing (/invoke)."""

    model_config = ConfigDict(extra="forbid")

    review_text: str = Field(
        ...,
        min_length=1,
        description="The review text to process through the LangGraph",
        example=(
            "I had an eventful cycle this summer. Learnt agentic workflows and implemented a "
            "self-reviewer agent for the periodic employee self-review process. It significantly "
            "improved employee productivity for the organization."
        ),
    )
    thread_id: str | None = Field(
        None,
        description=(
            "Optional thread ID for state persistence. If not provided, a new UUID will be generated."
        ),
        example="thread_123",
    )


class StreamRequest(BaseModel):
    """Request model for streaming self-review processing via SSE (/stream)."""

    model_config = ConfigDict(extra="forbid")

    review_text: str = Field(
        ..., min_length=1, description="The review text to process through the LangGraph"
    )
    thread_id: str = Field(
        ..., min_length=1, description="Unique identifier for the conversation thread"
    )
    mode: str = Field(
        "values",
        pattern=r"^(values|updates)$",
        description=(
            "Streaming mode - 'updates' for state changes only, 'values' for full state each step"
        ),
    )


class InvokeResponse(BaseModel):
    """Response model for synchronous self-review processing results."""

    model_config = ConfigDict(extra="forbid")

    original_text: str = Field(..., description="The original review text")
    copy_edited_text: str | None = Field(None, description="The copy-edited text")
    summary: str | None = Field(None, description="The summary of the copy-edited text")
    word_cloud_path: str | None = Field(None, description="The path to the word cloud image")
