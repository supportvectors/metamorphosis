# =============================================================================
#  Filename: text_modifiers.py
#
#  Short Description: LLM-backed text utilities (summarize, copy-edit) with structured outputs.
#
#  Creation date: 2025-08-31
#  Author: Asif Qamar
# =============================================================================

from __future__ import annotations

from typing import Annotated

from langchain_core.prompts import ChatPromptTemplate
from pydantic import Field, validate_call
from dotenv import load_dotenv
from loguru import logger

load_dotenv()

# Import custom exceptions and utilities
from metamorphosis.exceptions import (
    PostconditionError,
    raise_postcondition_error,
)
from metamorphosis.utilities import read_text_file, get_project_root
from metamorphosis.datamodel import SummarizedText, CopyEditedText
from metamorphosis import get_model_registry

class TextModifiers:
    """LLM-backed text processing utilities with structured outputs.

    This class provides text processing capabilities including summarization
    and copy editing using OpenAI's language models. All methods return
    structured Pydantic models for type safety and validation.

    The class uses prompt templates loaded from external files and leverages
    LangChain's structured output capabilities for reliable parsing.
    """

    def __init__(self) -> None:
        """Initialize the TextModifiers with LLM chains and prompt templates.

        Raises:
            ConfigurationError: If required environment variables are missing.
            FileOperationError: If prompt files cannot be loaded.
        """
        logger.debug("Initializing TextModifiers")

        # Acquire LLM clients from the central registry
        registry = get_model_registry()
        summarizer_llm = registry.summarizer_llm
        copy_editor_llm = registry.copy_editor_llm

        # Load prompt templates from files using utility functions
        project_root = get_project_root()
        prompts_dir = project_root / "prompts"
        logger.debug("Using prompts directory: {}", prompts_dir)

        summarizer_prompt_text = read_text_file(prompts_dir / "summarizer.md")
        copy_editor_prompt_text = read_text_file(prompts_dir / "copy_editor.md")

        # Compose prompts with input placeholders for clarity.
        self.summarizer = (
            ChatPromptTemplate.from_template(
                f"{summarizer_prompt_text}\\n\\nTarget maximum words: {{max_words}}\\n\\nText:\\n{{text}}"
            )
            | summarizer_llm.with_structured_output(SummarizedText)
        )
        self.copy_editor = (
            ChatPromptTemplate.from_template(f"{copy_editor_prompt_text}\\n\\nText:\\n{{text}}")
            | copy_editor_llm.with_structured_output(CopyEditedText)
        )

        logger.debug("TextModifiers initialized successfully")

    @validate_call
    def summarize(
        self,
        *,
        text: Annotated[str, Field(min_length=1)],
        max_words: Annotated[int, Field(gt=0)] = 300,
    ) -> SummarizedText:
        """Summarize text using the configured LLM chain.

        Args:
            text: The input text to summarize.
            max_words: Maximum number of words in the summary.

        Returns:
            SummarizedText: Structured summary with the summarized text.

        Raises:
            PostconditionError: If the output validation fails.
        """
        logger.debug("summarize: processing text (length={}, max_words={})", len(text), max_words)

        result = self.summarizer.invoke({"text": text, "max_words": max_words})

        # Postcondition (O(1)): ensure structured output is valid
        if not isinstance(result, SummarizedText) or not result.summarized_text:
            raise_postcondition_error(
                "Summarization output validation failed",
                context={"result_type": type(result).__name__, "has_text": bool(getattr(result, 'summarized_text', None))},
                operation="summarize_validation"
            )

        logger.debug("summarize: completed successfully (output_length={})", len(result.summarized_text))
        return result

    @validate_call
    def copy_edit(
        self, *, text: Annotated[str, Field(min_length=1)]
    ) -> CopyEditedText:
        """Copy edit text using the configured LLM chain.

        Args:
            text: The input text to copy edit.

        Returns:
            CopyEditedText: Structured output with the copy-edited text.

        Raises:
            PostconditionError: If the output validation fails.
        """
        logger.debug("copy_edit: processing text (length={})", len(text))

        result = self.copy_editor.invoke({"text": text})

        # Postcondition (O(1)): ensure structured output is valid
        if not isinstance(result, CopyEditedText) or not result.copy_edited_text:
            raise_postcondition_error(
                "Copy editing output validation failed",
                context={"result_type": type(result).__name__, "has_text": bool(getattr(result, 'copy_edited_text', None))},
                operation="copy_edit_validation"
            )

        logger.debug("copy_edit: completed successfully (output_length={})", len(result.copy_edited_text))
        return result


# Note: As per project preference, do not expose module-level factory functions here.
