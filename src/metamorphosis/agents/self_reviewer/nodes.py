# =============================================================================
#  Filename: nodes.py
#
#  Short Description: Workflow node implementations for self-reviewer system.
#
#  Creation date: 2025-09-08
#  Author: Asif Qamar
# =============================================================================

"""Workflow Node Implementations for Self-Reviewer System.

This module contains all the workflow node implementations used in the
self-reviewer LangGraph workflow. Each node represents a step in the
review processing pipeline.
"""

from __future__ import annotations

import json
from typing import Annotated, Literal, List

from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.messages import AIMessage, ToolMessage
from langgraph.prebuilt import ToolNode
from loguru import logger
from pydantic import Field, validate_call
from icontract import require, ensure

from metamorphosis.agents.self_reviewer.client import MCPClientManager
from metamorphosis.agents.self_reviewer.state import GraphState
from metamorphosis.agents.review_tools import extract_achievements, evaluate_review_text
from metamorphosis.datamodel import AchievementsList, ReviewScorecard
from metamorphosis.utilities import read_text_file, get_project_root
from metamorphosis.exceptions import raise_postcondition_error

from metamorphosis.rag.vectordb.embedded_vectordb import EmbeddedVectorDB
from metamorphosis.rag.vectordb.embedder import SimpleTextEmbedder
from metamorphosis.rag.corpus.achievement_evaluator import AchievementEvaluator
from metamorphosis.rag.corpus.project_data_models import AchievementEvaluation

class WorkflowNodes:
    """Contains all workflow node implementations.

    This class encapsulates all the node functions used in the self-reviewer
    workflow, providing a clean interface for graph construction and execution.

    Attributes:
        mcp_client: The MCP client manager for accessing tools.
        llm: The base language model for agent operations.
        achievements_extractor_llm: LLM bound with achievements extraction tools.
        review_text_evaluator_llm: LLM bound with review evaluation tools.
        achievements_extractor_tool_node: Tool node for achievements extraction.
        review_text_evaluator_tool_node: Tool node for review evaluation.
    """

    def __init__(self, mcp_client: MCPClientManager) -> None:
        """Initialize the workflow nodes.

        Args:
            mcp_client: Initialized MCP client manager.
        """
        self.mcp_client = mcp_client

        # Initialize LLM and tool configurations
        self.llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)
        self.achievements_extractor_llm = self.llm.bind_tools([extract_achievements])
        self.review_text_evaluator_llm = self.llm.bind_tools([evaluate_review_text])
        self.achievements_extractor_tool_node = ToolNode([extract_achievements])
        self.review_text_evaluator_tool_node = ToolNode([evaluate_review_text])

        # Load prompt templates
        project_root = get_project_root()
        prompts_dir = project_root / "prompts"
        self.achievements_extraction_system_prompt = read_text_file(
            prompts_dir / "achievements_extraction_system_prompt.md"
        )
        self.evaluation_score_system_prompt = read_text_file(
            prompts_dir / "evaluation_score_system_prompt.md"
        )

        # Initialize the achievement evaluator
        vector_db = EmbeddedVectorDB()
        embedder = SimpleTextEmbedder()
        self.achievement_evaluator = AchievementEvaluator(vector_db=vector_db, embedder=embedder)

    # -----------------------------------------------------------------------------

    @validate_call
    @require(lambda state: "original_text" in state, "State must contain original_text")
    @require(lambda state: isinstance(state["original_text"], str), "original_text must be string")
    @require(
        lambda state: len(state["original_text"].strip()) > 0, "original_text must not be empty"
    )
    @ensure(lambda result: "copy_edited_text" in result, "Result must contain copy_edited_text")
    @ensure(
        lambda result: isinstance(result["copy_edited_text"], str),
        "copy_edited_text must be string",
    )
    async def copy_editor_node(
        self, state: Annotated[dict, Field(description="Current workflow state")]
    ) -> dict:
        """Copy editor node for grammar and clarity improvements.

        This node processes the original self-review text to improve grammar,
        spelling, punctuation, and overall clarity.

        Args:
            state: Current workflow state containing original_text.

        Returns:
            dict: Updated state with copy_edited_text field populated.

        Raises:
            ValueError: If copy_edit tool is not available or postcondition fails.
            json.JSONDecodeError: If tool response is not valid JSON.
        """
        original_text = state["original_text"]
        logger.info("copy_editor_node: processing text (length={})", len(original_text))

        copy_edit_tool = self.mcp_client.get_tool("copy_edit")
        result = await copy_edit_tool.ainvoke({"text": original_text})

        result_data = json.loads(result)
        copy_edited_text = result_data["copy_edited_text"]

        return {"copy_edited_text": copy_edited_text}

    # -----------------------------------------------------------------------------

    @validate_call
    @require(lambda state: "copy_edited_text" in state, "State must contain copy_edited_text")
    @require(
        lambda state: isinstance(state["copy_edited_text"], str), "copy_edited_text must be string"
    )
    @require(
        lambda state: len(state["copy_edited_text"].strip()) > 0,
        "copy_edited_text must not be empty",
    )
    @ensure(lambda result: "summary" in result, "Result must contain summary")
    @ensure(lambda result: isinstance(result["summary"], str), "summary must be string")
    async def summarizer_node(
        self, state: Annotated[dict, Field(description="Current workflow state")]
    ) -> dict:
        """Summarizer node for abstractive text summarization.

        This node creates a concise, abstractive summary of the copy-edited text,
        extracting key insights and main points.

        Args:
            state: Current workflow state containing copy_edited_text.

        Returns:
            dict: Updated state with summary field populated.

        Raises:
            ValueError: If abstractive_summarize tool is not available or postcondition fails.
            json.JSONDecodeError: If tool response is not valid JSON.
        """
        copy_edited_text = state["copy_edited_text"]
        logger.info("summarizer_node: processing text (length={})", len(copy_edited_text))

        summarizer_tool = self.mcp_client.get_tool("abstractive_summarize")
        result = await summarizer_tool.ainvoke({"text": copy_edited_text})

        result_data = json.loads(result)
        summary = result_data["summarized_text"]

        return {"summary": summary}

    # -----------------------------------------------------------------------------

    @validate_call
    @require(lambda state: "copy_edited_text" in state, "State must contain copy_edited_text")
    @require(
        lambda state: isinstance(state["copy_edited_text"], str), "copy_edited_text must be string"
    )
    @require(
        lambda state: len(state["copy_edited_text"].strip()) > 0,
        "copy_edited_text must not be empty",
    )
    @ensure(lambda result: "word_cloud_path" in result, "Result must contain word_cloud_path")
    @ensure(
        lambda result: isinstance(result["word_cloud_path"], str), "word_cloud_path must be string"
    )
    async def wordcloud_node(
        self, state: Annotated[dict, Field(description="Current workflow state")]
    ) -> dict:
        """Word cloud generation node for visual text analysis.

        This node generates a visual word cloud from the copy-edited text, creating
        a graphical representation where word frequency is shown through font size.

        Args:
            state: Current workflow state containing copy_edited_text.

        Returns:
            dict: Updated state with word_cloud_path field populated.

        Raises:
            ValueError: If word_cloud tool is not available or postcondition fails.
        """
        copy_edited_text = state["copy_edited_text"]
        logger.info("wordcloud_node: processing text (length={})", len(copy_edited_text))

        wordcloud_tool = self.mcp_client.get_tool("word_cloud")
        result = await wordcloud_tool.ainvoke({"text": copy_edited_text})

        # The word_cloud tool returns a string path directly, not JSON
        wordcloud_path = result

        return {"word_cloud_path": wordcloud_path}

    # -----------------------------------------------------------------------------

    @validate_call
    @require(lambda state: "copy_edited_text" in state, "State must contain copy_edited_text")
    @require(
        lambda state: isinstance(state["copy_edited_text"], str), "copy_edited_text must be string"
    )
    @require(
        lambda state: len(state["copy_edited_text"].strip()) > 0,
        "copy_edited_text must not be empty",
    )
    @ensure(lambda result: "messages" in result, "Result must contain messages")
    @ensure(lambda result: isinstance(result["messages"], list), "messages must be list")
    async def achievements_extractor_node(
        self, state: Annotated[dict, Field(description="Current workflow state")]
    ) -> dict:
        """Achievements extractor node for extracting key achievements from the text.

        This asynchronous node is responsible for orchestrating the extraction of key achievements
        from the employee's copy-edited self-review text. It leverages a LangGraph agent, which
        utilizes the `extract_achievements` tool, and is guided by a system prompt designed to
        ensure accurate and relevant extraction. The node constructs a prompt with the current
        conversation history and the input text, invokes the agent, and returns the updated
        message list including the agent's response.

        Args:
            state: The current workflow state. Must contain:
                - "copy_edited_text" (str): The self-review text to analyze.
                - "messages" (list, optional): Conversation history for context.

        Returns:
            dict: A dictionary with a single key "messages", containing the updated list of
                messages (including the agent's response with extracted achievements).

        Raises:
            KeyError: If "copy_edited_text" is missing from the state.
            Exception: If the agent invocation fails or returns an unexpected result.
        """
        copy_edited_text = state["copy_edited_text"]
        logger.info(
            "achievements_extractor_node: processing text (length={})", len(copy_edited_text)
        )

        messages = state.get("messages", [])
        prompt = ChatPromptTemplate.from_messages(
            [
                ("system", self.achievements_extraction_system_prompt),
                MessagesPlaceholder("messages"),
                (
                    "human",
                    "Extract key achievements from this text:\\n\\n{input_text}\\n\\nIf needed, call the tool.",
                ),
            ]
        )
        rendered = prompt.invoke({"messages": messages, "input_text": copy_edited_text})
        ai_response = await self.achievements_extractor_llm.ainvoke(rendered)

        return {"messages": [ai_response]}

    # -----------------------------------------------------------------------------

    @validate_call
    def _validate_messages(self, msgs: list) -> None:
        """Validate that messages exist and contain tool messages.

        Args:
            msgs: List of messages to validate.

        Raises:
            ValueError: If validation fails.
        """
        if not msgs:
            raise_postcondition_error(
                "Post-tools node: no messages found",
                context={"messages_count": len(msgs) if msgs else 0},
                operation="post_tools_validation",
            )

    # -----------------------------------------------------------------------------

    @validate_call
    def _extract_tool_payload(self, tool_msg: ToolMessage) -> dict:
        """Extract payload from tool message content.

        Args:
            tool_msg: The tool message to extract payload from.

        Returns:
            dict: The extracted payload.
        """
        # Handle both dict and string content formats
        if isinstance(tool_msg.content, (dict, list)):
            return tool_msg.content

        # Try to parse JSON if it's a string
        try:
            return json.loads(tool_msg.content)
        except Exception:
            return {"raw": tool_msg.content}

    # -----------------------------------------------------------------------------

    @validate_call
    def _find_latest_tool_message(self, msgs: list) -> ToolMessage:
        """Find the most recent ToolMessage from the messages.

        Args:
            msgs: List of messages to search.

        Returns:
            ToolMessage: The latest tool message.

        Raises:
            ValueError: If no tool messages found.
        """
        tool_msgs = [m for m in reversed(msgs) if isinstance(m, ToolMessage)]
        if not tool_msgs:
            raise_postcondition_error(
                "Post-tools node: no tool messages found",
                context={"tool_msgs_count": len(tool_msgs) if tool_msgs else 0},
                operation="post_tools_validation",
            )
        return tool_msgs[0]

    # -----------------------------------------------------------------------------

    @require(lambda state: "messages" in state, "State must contain messages")
    @require(lambda state: isinstance(state["messages"], list), "messages must be list")
    @ensure(lambda result: "achievements" in result, "Result must contain achievements")
    @ensure(lambda result: "review_complete" in result, "Result must contain review_complete")
    async def after_achievements_parser(self, state: GraphState) -> dict:
        """Achievements extractor post-tools node for extracting key achievements from the text.

        Called after ToolNode executes. It reads the latest ToolMessage,
        extracts the tool result (AchievementsList), and writes it into the state.

        Args:
            state: Current workflow state containing messages.

        Returns:
            dict: Updated state with achievements and review_complete flag.
        """
        logger.info("after_achievements_parser: parsing achievements")
        msgs = state.get("messages", [])

        self._validate_messages(msgs)
        last_tool_msg = self._find_latest_tool_message(msgs)
        payload = self._extract_tool_payload(last_tool_msg)

        # We expect payload to match AchievementsList
        achievements_obj = payload if isinstance(payload, dict) else {"result": payload}
        achievements = AchievementsList(**achievements_obj)
        logger.info("after_achievements_parser: raw achievements (length={})", len(achievements.items))
        
        # Contextualize the achievements
        achievements = self._contextualize_achievements(achievements)
        logger.info("after_achievements_parser: contextualized achievements (length={})", len(achievements.items))

        summary = AIMessage(
            content=f"Received {len(achievements.items)} achievements from tool.\\n"
        )

        review_complete = len(achievements.items) >= 3
        return {
            "messages": [summary],
            "achievements": achievements,
            "review_complete": review_complete,
        }

    # -----------------------------------------------------------------------------

    @validate_call
    def _convert_achievement_evaluations_to_achievements(self, 
    achievement_evaluations: List[AchievementEvaluation], 
    size: int, 
    unit: Literal["tokens"]) -> AchievementsList:
        """Convert achievement evaluations to achievements.

        Args:
            achievement_evaluations: List of achievement evaluations.
            size: Size of the achievements list.
            unit: Unit of the achievements list.
        """
        updated_achievements = []
        for achievement_evaluation in achievement_evaluations:
            updated_achievement = achievement_evaluation.achievement
            # update the achievement with the evaluation results
            updated_achievement.contribution = achievement_evaluation.contribution
            updated_achievement.rationale = achievement_evaluation.rationale
            updated_achievement.project_name = achievement_evaluation.project.name
            updated_achievement.project_text = achievement_evaluation.project.text
            updated_achievement.project_department = achievement_evaluation.project.department
            updated_achievement.project_impact_category = achievement_evaluation.project.impact_category
            updated_achievement.project_effort_size = achievement_evaluation.project.effort_size

            updated_achievements.append(updated_achievement)

        return AchievementsList(items=updated_achievements, size=size, unit=unit)

    # -----------------------------------------------------------------------------

    @validate_call
    def _contextualize_achievements(self, achievements: AchievementsList) -> AchievementsList:
        """Contextualize the achievements using the achievement evaluator.

        Args:
            achievements: AchievementsList to contextualize.
        """
        logger.info("_contextualize_achievements: contextualizing achievements (length={})", len(achievements.items))
        
        try:
            contextualized_achievements = self.achievement_evaluator.contextualize(achievements=achievements)
            logger.info("_contextualize_achievements: contextualized achievements (length={})", len(contextualized_achievements))
            updated_achievements = self._convert_achievement_evaluations_to_achievements(contextualized_achievements, achievements.size, achievements.unit)
            logger.info("_contextualize_achievements: contextualized achievements (length={})", len(updated_achievements.items))
            return updated_achievements
        except Exception as e:
            logger.error("_contextualize_achievements: failed to contextualize achievements: {}", e)
            # Return original achievements if contextualization fails
            return achievements

    # -----------------------------------------------------------------------------

    @validate_call
    @require(lambda state: "copy_edited_text" in state, "State must contain copy_edited_text")
    @require(
        lambda state: isinstance(state["copy_edited_text"], str), "copy_edited_text must be string"
    )
    @require(
        lambda state: len(state["copy_edited_text"].strip()) > 0,
        "copy_edited_text must not be empty",
    )
    @ensure(lambda result: "messages" in result, "Result must contain messages")
    @ensure(lambda result: isinstance(result["messages"], list), "messages must be list")
    async def review_text_evaluator_node(
        self, state: Annotated[dict, Field(description="Current workflow state")]
    ) -> dict:
        """Review text evaluator node for evaluating the copy-edited text.

        This node evaluates the review text using an agent accessing a review scorecard generation langgraph tool.

        Args:
            state: Current workflow state containing copy_edited_text.

        Returns:
            dict: Updated state with messages containing evaluation response.
        """
        copy_edited_text = state["copy_edited_text"]
        logger.info(
            "review_text_evaluator_node: processing text (length={})", len(copy_edited_text)
        )

        messages = state.get("messages", [])
        prompt = ChatPromptTemplate.from_messages(
            [
                ("system", self.evaluation_score_system_prompt),
                MessagesPlaceholder("messages"),
                (
                    "human",
                    "Evaluate the review text and generate a review scorecard:\\n\\n{input_text}\\n\\nIf needed, call the tool.",
                ),
            ]
        )
        rendered = prompt.invoke({"messages": messages, "input_text": copy_edited_text})
        ai_response = await self.review_text_evaluator_llm.ainvoke(rendered)

        return {"messages": [ai_response]}

    # -----------------------------------------------------------------------------

    @require(lambda state: "messages" in state, "State must contain messages")
    @require(lambda state: isinstance(state["messages"], list), "messages must be list")
    @ensure(lambda result: "review_scorecard" in result, "Result must contain review_scorecard")
    async def after_evaluation_parser(self, state: GraphState) -> dict:
        """Review text evaluator post-tools node for evaluating the review text.

        Called after ToolNode executes. It reads the latest ToolMessage,
        extracts the tool result (ReviewScorecard), and writes it into the state.

        Args:
            state: Current workflow state containing messages.

        Returns:
            dict: Updated state with review_scorecard.
        """
        logger.info("after_evaluation_parser: parsing review scorecard")
        msgs = state.get("messages", [])

        self._validate_messages(msgs)
        last_tool_msg = self._find_latest_tool_message(msgs)
        payload = self._extract_tool_payload(last_tool_msg)

        # We expect payload to match ReviewScorecard
        review_scorecard_obj = payload if isinstance(payload, dict) else {"result": payload}
        review_scorecard = ReviewScorecard(**review_scorecard_obj)

        summary = AIMessage(
            content=f"Received {review_scorecard_obj.get('overall')} review scorecard from tool.\\n"
        )

        return {
            "messages": [summary],
            "review_scorecard": review_scorecard,
        }

    # -----------------------------------------------------------------------------

    @require(lambda state: isinstance(state, dict), "State must be a dictionary")
    async def should_call_achievements_extractor_tools(
        self, state: GraphState
    ) -> Literal["no_tools", "tools"]:
        """If the last AI message contains tool calls, go to tools; else no tools.

        Args:
            state: Current workflow state containing messages.

        Returns:
            Literal: "tools" if tool calls found, "no_tools" otherwise.
        """
        msgs = state.get("messages", [])
        if not msgs:
            return "no_tools"

        last = msgs[-1]
        if isinstance(last, AIMessage) and getattr(last, "tool_calls", None):
            logger.info("should_call_achievements_extractor_tools: calling tools")
            return "tools"

        logger.info("should_call_achievements_extractor_tools: no tools called")
        return "no_tools"

    # -----------------------------------------------------------------------------

    @require(lambda state: isinstance(state, dict), "State must be a dictionary")
    async def should_call_review_text_evaluator_tools(
        self, state: GraphState
    ) -> Literal["no_tools", "tools"]:
        """If the last AI message contains tool calls, go to tools; else no tools.

        Args:
            state: Current workflow state containing messages.

        Returns:
            Literal: "tools" if tool calls found, "no_tools" otherwise.
        """
        msgs = state.get("messages", [])
        if not msgs:
            return "no_tools"

        last = msgs[-1]
        if isinstance(last, AIMessage) and getattr(last, "tool_calls", None):
            logger.info("should_call_review_text_evaluator_tools: calling tools")
            return "tools"

        logger.info("should_call_review_text_evaluator_tools: no tools called")
        return "no_tools"
