# =============================================================================
#  Filename: text_modifiers.py
#
#  Short Description: LLM-backed text utilities (summarize, copy-edit) with structured outputs.
#
#  Creation date: 2025-08-31
#  Author: Asif Qamar
# =============================================================================

from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path
from typing import Optional

from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from pydantic import BaseModel, ConfigDict, Field, validate_call


def _read_text_file(file_path: Path) -> str:
    """Read a UTF-8 text file, raising ValueError if not found or empty.

    This helper is intentionally simple to keep cognitive complexity low.
    """
    if not file_path.exists() or not file_path.is_file():
        raise ValueError(f"Prompt file not found: {file_path}")
    content = file_path.read_text(encoding="utf-8").strip()
    if not content:
        raise ValueError(f"Prompt file is empty: {file_path}")
    return content


class SummarizedText(BaseModel):
    """Structured summary output."""

    model_config = ConfigDict(extra="forbid")

    summarized_text: str = Field(..., description="The summarized text")
    original_text: str = Field(..., description="The original text provided")
    size: int = Field(..., description="The size of the summarized text")


class CopyEditedText(BaseModel):
    """Structured copy-edit output."""

    model_config = ConfigDict(extra="forbid")

    copy_edited_text: str = Field(..., description="The copy edited text")
    original_text: str = Field(..., description="The original text provided")
    is_modified: bool = Field(..., description="Whether the text was modified")


class TextModifiers:
    """Builds summarization and copy-edit chains using a single LLM instance.

    A single instance is cached to avoid repeatedly loading prompts and models.
    """

    def __init__(self) -> None:
        openai_api_key = os.getenv("OPENAI_API_KEY")
        if not openai_api_key:
            raise ValueError("OPENAI_API_KEY environment variable is required")

        self.llm = ChatOpenAI(model="gpt-5", temperature=0, api_key=openai_api_key)

        project_root = Path(__file__).resolve().parents[3]
        prompts_dir = project_root / "prompts"

        summarizer_prompt_text = _read_text_file(prompts_dir / "summarizer.md")
        copy_editor_prompt_text = _read_text_file(prompts_dir / "copy_editor.md")

        # Compose prompts with input placeholders for clarity.
        self.summarizer = (
            ChatPromptTemplate.from_template(
                f"{summarizer_prompt_text}\n\nTarget maximum words: {{max_words}}\n\nText:\n{{text}}"
            )
            | self.llm.with_structured_output(SummarizedText)
        )
        self.copy_editor = (
            ChatPromptTemplate.from_template(f"{copy_editor_prompt_text}\n\nText:\n{{text}}")
            | self.llm.with_structured_output(CopyEditedText)
        )

    def summarize(self, *, text: str, max_words: int = 300) -> SummarizedText:
        """Summarize text using the configured LLM chain."""
        if text is None or not isinstance(text, str) or not text.strip():
            raise ValueError("text must be a non-empty string")
        if not isinstance(max_words, int) or max_words < 1:
            raise ValueError("max_words must be a positive integer")
        result = self.summarizer.invoke({"text": text, "max_words": max_words})
        if not result.summarized_text or not isinstance(result.summarized_text, str):
            raise ValueError("summarized_text must be a non-empty string")
        if result.size < 0:
            raise ValueError("size must be non-negative")
        return result

    def copy_edit(self, *, text: str) -> CopyEditedText:
        """Copy edit text using the configured LLM chain."""
        if text is None or not isinstance(text, str) or not text.strip():
            raise ValueError("text must be a non-empty string")
        result = self.copy_editor.invoke({"text": text})
        if not result.copy_edited_text or not isinstance(result.copy_edited_text, str):
            raise ValueError("copy_edited_text must be a non-empty string")
        return result


@lru_cache(maxsize=1)
def get_text_modifiers() -> TextModifiers:
    """Return a cached `TextModifiers` instance for reuse by callers."""
    return TextModifiers()