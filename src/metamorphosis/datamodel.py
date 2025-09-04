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
    word_cloud_path: str | None = Field(
        None, description="The path to the word cloud image"
    )


