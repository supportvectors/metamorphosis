# =============================================================================
#  Filename: text_modifiers.py
#
#  Short Description: LLM-backed text utilities (summarize, copy-edit) with structured outputs.
#
#  Creation date: 2025-08-31
#  Author: Asif Qamar
# =============================================================================

from __future__ import annotations

from typing import Annotated, Any

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
from metamorphosis.datamodel import SummarizedText, CopyEditedText, AchievementsList, ReviewScorecard
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
        self.summarizer_llm = registry.summarizer_llm
        self.copy_editor_llm = registry.copy_editor_llm
        self.key_achievements_llm = registry.key_achievements_llm
        self.review_text_evaluator_llm = registry.review_text_evaluator_llm

        # Load prompt templates from files using utility functions
        project_root = get_project_root()
        prompts_dir = project_root / "prompts"
        logger.debug("Using prompts directory: {}", prompts_dir)

        # Load as-is; no VOICE placeholder expected in the template
        self.summarizer_system_prompt = read_text_file(prompts_dir / "summarizer_system_prompt.md")
        self.summarizer_user_prompt = read_text_file(prompts_dir / "summarizer_user_prompt.md")
        
        self.key_achievements_system_prompt = read_text_file(prompts_dir / "key_achievements_system_prompt.md")
        self.key_achievements_user_prompt = read_text_file(prompts_dir / "key_achievements_user_prompt.md")
        
        self.text_rationalization_system_prompt = read_text_file(prompts_dir / "text_rationalization_system_prompt.md")
        self.text_rationalization_user_prompt = read_text_file(prompts_dir / "text_rationalization_user_prompt.md")
        
        self.text_evaluator_system_prompt = read_text_file(prompts_dir / "text_evaluator_system_prompt.md")
        self.text_evaluator_user_prompt = read_text_file(prompts_dir / "text_evaluator_user_prompt.md")
        
     
        # Compose prompts with input placeholders for clarity.

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
        # Log the model details as a simple table for traceability and debugging.
        self._log_model_details_table("summarize")
        
        messages = [
            ("system", self.summarizer_system_prompt),
            ("user",self.summarizer_user_prompt.format(review=text)),
        ]
        prompt = ChatPromptTemplate.from_messages(messages)
        logger.debug("summarizer_llm: {}", self.summarizer_llm)
        summarizer = prompt | self.summarizer_llm.with_structured_output(SummarizedText)

        try:
            result = summarizer.invoke({})
        except Exception as e:
            logger.error("summarize: LLM invocation failed - {}", str(e))
            raise PostconditionError(
                "Summarization LLM invocation failed",
                operation="summarize_llm_invocation"
            ) from e

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
    def rationalize_text(
        self, *, text: Annotated[str, Field(min_length=1)]
    ) -> CopyEditedText:
        """Rationalize text by correcting grammar, spelling, and formatting errors.

        This method performs text rationalization using an LLM-based copy editor that makes
        minor, localized corrections to improve the professional quality of text while
        preserving the original meaning, structure, and content. The rationalization process
        focuses on fixing:

        - Spelling errors and typos (e.g., "teh" → "the", "recieved" → "received")
        - Grammar issues (subject-verb agreement, tense consistency, articles)
        - Punctuation normalization (quotes, commas, dashes, parentheses)
        - Capitalization consistency (proper nouns, product names, teams)
        - Whitespace and formatting standardization
        - Casual shorthand replacement with formal equivalents (e.g., "w/" → "with")

        The method is specifically designed for employee self-reviews and similar business
        documents that may contain informal language, typos, or inconsistent formatting
        from being pasted from drafts or messaging platforms.

        **Preservation Guarantees:**
        - Original paragraph structure and ordering are maintained exactly
        - Numerical values and units remain identical (only formatting may be normalized)
        - Bullet points, headings, and section order are preserved
        - Author's voice and intent (first/third person) are retained
        - No content is added, removed, or significantly rewritten

        **Style Transformations:**
        - Converts informal shorthand to professional language when unambiguous
        - Normalizes product/tool names for consistency
        - Standardizes punctuation and spacing around units and symbols
        - Removes casual interjections while preserving meaning
        - Corrects double negatives in reduction statements (e.g., "reduced by -38%" → "reduced by 38%")

        Args:
            text: The input text to rationalize. Must be non-empty string containing
                the content to be copy-edited. Typically employee self-review text
                or similar business documents that need professional polish.

        Returns:
            CopyEditedText: A structured response containing:
                - copy_edited_text: The rationalized text with corrections applied
                - size: Estimated token count of the rationalized text
                - is_edited: Boolean indicating whether any changes were made

        Raises:
            ValidationError: If the input text is empty or invalid.
            PostconditionError: If the LLM output validation fails or the structured
                response cannot be parsed correctly.
            ConfigurationError: If the copy editor LLM is not properly configured.

        Example:
            >>> modifier = TextModifiers()
            >>> result = modifier.rationalize_text(
            ...     text="I migrated teh system w/ better performance. "
            ...          "Latency dropped by -38% after optimizations."
            ... )
            >>> print(result.copy_edited_text)
            "I migrated the system with better performance. "
            "Latency dropped by 38% after optimizations."
            >>> print(result.is_edited)
            True

        Note:
            This method uses the text_rationalization_system_prompt.md and
            text_rationalization_user_prompt.md templates to guide the LLM's
            behavior. The rationalization is performed by the copy_editor_llm
            configured in the model registry.
        """
        logger.debug("rationalize_text: processing text (length={})", len(text))
        # Log the model details as a simple table for traceability and debugging.
        self._log_model_details_table("rationalize_text")

        # Construct the prompt using the text rationalization templates
        messages = [
            ("system", self.text_rationalization_system_prompt),
            ("user", self.text_rationalization_user_prompt.format(EMPLOYEE_REVIEW_TEXT=text)),
        ]
        prompt = ChatPromptTemplate.from_messages(messages)
        
        # Create the rationalization chain with structured output
        rationalizer = prompt | self.copy_editor_llm.with_structured_output(CopyEditedText)
        
        # Invoke the chain with exception handling
        try:
            result = rationalizer.invoke({})
        except Exception as e:
            logger.error("rationalize_text: LLM invocation failed - {}", str(e))
            raise PostconditionError(
                "Text rationalization LLM invocation failed",
                operation="rationalize_text_llm_invocation"
            ) from e

        # Postcondition (O(1)): ensure structured output is valid
        if not isinstance(result, CopyEditedText) or not result.copy_edited_text:
            raise_postcondition_error(
                "Text rationalization output validation failed",
                context={"result_type": type(result).__name__, "has_text": bool(getattr(result, 'copy_edited_text', None))},
                operation="rationalize_text_validation"
            )

        logger.debug("rationalize_text: completed successfully (output_length={}, edited={})", 
                    len(result.copy_edited_text), result.is_edited)
        return result

    # =========================================================================

    @validate_call
    def extract_achievements(
        self, *, text: Annotated[str, Field(min_length=1)]
    ) -> AchievementsList:
        """Extract key achievements from employee self-review text.

        This method analyzes employee self-review text and extracts up to 5 key achievements
        with structured metadata including impact areas, metrics, timeframes, and
        collaboration details. The extraction focuses on identifying concrete outcomes
        and business impact rather than activities or tasks.

        The method uses an LLM-based achievement extractor that follows strict guidelines
        to identify and rank achievements by:
        - Business/customer impact (revenue, cost, risk, user outcomes)
        - Reliability/quality/security improvements (SLO/MTTR/incidents/defects)
        - Breadth of ownership (Cross-team/Org-wide > TechLead > IC)
        - Adoption/usage and external validation
        - Recency (tie-breaker)

        **Achievement Structure:**
        Each extracted achievement includes:
        - **title**: Concise, outcome-oriented label (≤12 words)
        - **outcome**: Impact/result description (≤40 words)
        - **impact_area**: Categorized impact type (reliability, performance, security, etc.)
        - **metric_strings**: Verbatim numbers/units from the review text
        - **timeframe**: Explicit time period if stated (e.g., "Q2 2025", "H1")
        - **ownership_scope**: Leadership level if explicit (IC, TechLead, Manager, etc.)
        - **collaborators**: Named people/teams if mentioned

        **Quality Guarantees:**
        - No invented metrics, dates, or collaborators - only explicit information
        - Numbers and units copied exactly as they appear in the review
        - Achievements are deduplicated and ranked by impact
        - Maximum of 5 achievements returned, fewer if insufficient quality achievements exist

        Args:
            text: The employee self-review text to analyze. Must be non-empty string
                containing the review content from which to extract achievements.
                Typically contains mixed content (tasks, outcomes, anecdotes) that
                needs to be parsed for concrete accomplishments.

        Returns:
            AchievementsList: A structured response containing:
                - items: List of up to 5 Achievement objects ranked by impact
                - size: Token estimate of concatenated titles and outcomes
                - unit: Always "tokens"

        Raises:
            ValidationError: If the input text is empty or invalid.
            PostconditionError: If the LLM output validation fails or the structured
                response cannot be parsed correctly.
            ConfigurationError: If the key achievements LLM is not properly configured.

        Example:
            >>> modifier = TextModifiers()
            >>> result = modifier.extract_achievements(
            ...     text="I reduced checkout p95 latency from 480ms to 190ms in H1 2025 "
            ...          "by redesigning the caching layer with the Payments and SRE teams. "
            ...          "This improved conversion rates during peak traffic periods."
            ... )
            >>> print(result.items[0].title)
            "Cut checkout p95 latency"
            >>> print(result.items[0].impact_area)
            "performance"
            >>> print(result.items[0].metric_strings)
            ["480ms", "190ms"]

        Note:
            This method uses the key_achievements_system_prompt.md and
            key_achievements_user_prompt.md templates to guide the LLM's behavior.
            The extraction is performed by the key_achievements_llm configured
            in the model registry.
        """
        logger.debug("extract_achievements: processing text (length={})", len(text))
        # Log the model details as a simple table for traceability and debugging.
        self._log_model_details_table("extract_achievements")

        # Construct the prompt using the key achievements templates
        messages = [
            ("system", self.key_achievements_system_prompt),
            ("user", self.key_achievements_user_prompt.format(EMPLOYEE_REVIEW_TEXT=text)),
        ]
        prompt = ChatPromptTemplate.from_messages(messages)
        
        # Create the achievement extraction chain with structured output
        extractor = prompt | self.key_achievements_llm.with_structured_output(AchievementsList)
        
        # Invoke the chain with exception handling
        try:
            result = extractor.invoke({})
        except Exception as e:
            logger.error("extract_achievements: LLM invocation failed - {}", str(e))
            raise PostconditionError(
                "Achievement extraction LLM invocation failed",
                operation="extract_achievements_llm_invocation"
            ) from e

        # Postcondition (O(1)): ensure structured output is valid
        if not isinstance(result, AchievementsList):
            raise_postcondition_error(
                "Achievement extraction output validation failed",
                context={"result_type": type(result).__name__, "has_items": bool(getattr(result, 'items', None))},
                operation="extract_achievements_validation"
            )

        logger.debug("extract_achievements: completed successfully (items_count={}, total_size={})", 
                    len(result.items), result.size)
        return result

    # =========================================================================

    @validate_call
    def evaluate_review_text(
        self, *, text: Annotated[str, Field(min_length=1)]
    ) -> ReviewScorecard:
        """Evaluate the writing quality of employee self-review text.

        This method analyzes employee self-review text and provides a comprehensive
        assessment of writing quality across six key dimensions. The evaluation
        focuses on the quality of the writing itself, not job performance, to help
        HR partners and engineering leaders quickly assess review quality.

        The method uses an LLM-based evaluator that scores the review on:
        - **OutcomeOverActivity** (25%): Emphasis on concrete outcomes vs. task lists
        - **QuantitativeSpecificity** (25%): Use of metrics, numbers, and baselines
        - **ClarityCoherence** (15%): Logical flow and readability
        - **Conciseness** (15%): Efficient, non-redundant expression
        - **OwnershipLeadership** (10%): Clear ownership and leadership signals
        - **Collaboration** (10%): Evidence of cross-team work and partnerships

        **Scoring System:**
        Each dimension is scored 0-100 using anchor levels (20/40/60/80/95) with
        specific rubrics. The overall score is a weighted average that determines
        the verdict: excellent (≥85), strong (70-84), mixed (50-69), weak (<50).

        **Output Structure:**
        - Individual scores and rationales for each dimension
        - Specific, actionable improvement suggestions
        - Weighted overall score and verdict classification
        - Optional flags for common issues (e.g., no_numbers_detected, short_review)
        - Radar chart data for visualization

        Args:
            text: The employee self-review text to evaluate. Must be non-empty string
                containing the review content to be assessed for writing quality.
                Typically contains mixed content about achievements, projects, and
                activities that needs quality assessment.

        Returns:
            ReviewScorecard: A structured assessment containing:
                - metrics: List of 6 MetricScore objects with scores, rationales, suggestions
                - overall: Weighted average score (0-100)
                - verdict: Quality classification (excellent/strong/mixed/weak)
                - notes: Optional flags for specific issues detected
                - radar_labels: Metric names for chart visualization
                - radar_values: Corresponding scores for chart visualization

        Raises:
            ValidationError: If the input text is empty or invalid.
            PostconditionError: If the LLM output validation fails or the structured
                response cannot be parsed correctly.
            ConfigurationError: If the review text evaluator LLM is not properly configured.

        Example:
            >>> modifier = TextModifiers()
            >>> result = modifier.evaluate_review_text(
            ...     text="I reduced latency from 480ms to 190ms by optimizing the cache. "
            ...          "This improved user experience and reduced server costs by 15%."
            ... )
            >>> print(result.overall)
            75
            >>> print(result.verdict)
            "strong"
            >>> print(result.metrics[0].name)
            "OutcomeOverActivity"

        Note:
            This method uses the text_evaluator_system_prompt.md and
            text_evaluator_user_prompt.md templates to guide the LLM's behavior.
            The evaluation is performed by the review_text_evaluator_llm configured
            in the model registry.
        """
        logger.debug("evaluate_review_text: processing text (length={})", len(text))
        # Log the model details as a simple table for traceability and debugging.
        self._log_model_details_table("evaluate_review_text")

        # Construct the prompt using the text evaluator templates
        messages = [
            ("system", self.text_evaluator_system_prompt),
            ("user", self.text_evaluator_user_prompt.format(EMPLOYEE_REVIEW_TEXT=text)),
        ]
        prompt = ChatPromptTemplate.from_messages(messages)
        
        # Create the evaluation chain with structured output
        evaluator = prompt | self.review_text_evaluator_llm.with_structured_output(ReviewScorecard)
        
        # Invoke the chain with exception handling
        try:
            result = evaluator.invoke({})
        except Exception as e:
            logger.error("evaluate_review_text: LLM invocation failed - {}", str(e))
            raise PostconditionError(
                "Review text evaluation LLM invocation failed",
                operation="evaluate_review_text_llm_invocation"
            ) from e

        # Postcondition (O(1)): ensure structured output is valid
        if not isinstance(result, ReviewScorecard) or not result.metrics or len(result.metrics) != 6:
            raise_postcondition_error(
                "Review text evaluation output validation failed",
                context={
                    "result_type": type(result).__name__, 
                    "has_metrics": bool(getattr(result, 'metrics', None)),
                    "metrics_count": len(getattr(result, 'metrics', []))
                },
                operation="evaluate_review_text_validation"
            )

        logger.debug("evaluate_review_text: completed successfully (overall_score={}, verdict={})", 
                    result.overall, result.verdict)
        return result

    # =========================================================================

    def get_model_info(self, method: str) -> dict[str, Any] | None:
        """Get model configuration information for a specific method.

        Args:
            method: The method name (e.g., "summarize", "rationalize_text", "extract_achievements", "evaluate_review_text").

        Returns:
            Dictionary containing model configuration or None if not found.
        """
        method_to_llm = {
            "summarize": self.summarizer_llm,
            "rationalize_text": self.copy_editor_llm,
            "extract_achievements": self.key_achievements_llm,
            "evaluate_review_text": self.review_text_evaluator_llm,
        }
        
        llm = method_to_llm.get(method)
        if not llm:
            return None
            
        # Extract configuration from the LLM instance
        model_info = {
            "model": getattr(llm, "model_name", "N/A"),
            "temperature": getattr(llm, "temperature", "N/A"),
            "max_tokens": getattr(llm, "max_tokens", "N/A"),
            "timeout": getattr(llm, "request_timeout", "N/A"),
        }
        
        # Add optional parameters if they exist
        for attr in ("top_p", "frequency_penalty", "presence_penalty"):
            value = getattr(llm, attr, None)
            if value is not None:
                model_info[attr] = value
                
        return model_info

    def _log_model_details_table(self, method: str) -> None:
        """Log the LLM model details as a table for the given TextModifiers method.

        Args:
            method: The name of the method (e.g., "summarize", "rationalize_text").
        """
        # Defensive: ensure the model config is present and has expected keys
        model_info = self.get_model_info(method)
        if not model_info:
            logger.warning("No model info found for method '{}'", method)
            return

        # Prepare table rows
        rows = [
            ("Model", model_info.get("model", "N/A")),
            ("Temperature", model_info.get("temperature", "N/A")),
            ("Max Tokens", model_info.get("max_tokens", "N/A")),
            ("Timeout", model_info.get("timeout", "N/A")),
        ]
        # Optional fields
        for key in ("top_p", "frequency_penalty", "presence_penalty"):
            if key in model_info:
                rows.append((key.replace("_", " ").title(), model_info[key]))

        # Format as table
        col_width = max(len(str(k)) for k, _ in rows) + 2
        table_lines = [
            f"{'Parameter'.ljust(col_width)}| Value",
            f"{'-' * (col_width)}|{'-' * 20}",
        ]
        for k, v in rows:
            table_lines.append(f"{str(k).ljust(col_width)}| {v}")

        logger.info("LLM Model Details for '{}':\n{}", method, "\n".join(table_lines))


# Note: As per project preference, do not expose module-level factory functions here.
