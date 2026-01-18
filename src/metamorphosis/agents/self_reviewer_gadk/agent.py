# =============================================================================
#  Filename: agent.py
#
#  Short Description: ADK agent and tool definitions for the periodic employee self-review process.
#
#  Creation date: 2025-10-27
#  Author: Chandar L
# =============================================================================
import asyncio
import logging
import warnings
from functools import lru_cache
from typing import List
from google.adk.tools.tool_context import ToolContext
from google.adk.agents import LlmAgent
from google.adk.models.lite_llm import LiteLlm
from google.adk.tools.mcp_tool import McpToolset, StreamableHTTPConnectionParams

from metamorphosis.mcp.text_modifiers import TextModifiers
from metamorphosis.datamodel import AchievementsList
from metamorphosis.rag.corpus.achievement_evaluator import AchievementEvaluator
from metamorphosis.rag.corpus.project_data_models import AchievementEvaluation
from metamorphosis.rag.vectordb.embedded_vectordb import EmbeddedVectorDB
from metamorphosis.rag.vectordb.embedder import SimpleTextEmbedder
from typing import Literal, Any
# Suppress authentication warnings from ADK tools
warnings.filterwarnings("ignore", message=".*auth_config or auth_config.auth_scheme is missing.*")
logging.getLogger("google_adk.google.adk.tools.base_authenticated_tool").setLevel(logging.ERROR)
logger = logging.getLogger(__name__)
''' 
**ADK Agents for the periodic employee self-review process.**

Create an ADK MCP client to access the MCPtools defined in src/metamorphosis/mcp/tools_server.py module through streamable_http transport:
1. Copy editor (copy_edit)
2. Summarizer (abstractive_summarize)
3. Word cloud (word_cloud)

Create in-house ADK tools to extract the achievements and review scorecard from the copy-edited text from the 
following methods defined in src/metamorphosis/mcp/text_modifiers.py module by constructing the tools using the following methods:
1. Achievements extractor using extract_achievements method.
2. Review text evaluator using evaluate_review_text method.

Create an ADK agent that will leverage the above MCP tools as well as the in-house ADK tools to handle the following:
1. Copy editor - Review of the input text to improve grammar and clarity (using copy_edit MCP tool)
2. Summarizer - Summarization of the copy-edited text to extract the key insights (using abstractive_summarize MCP tool)
3. Word cloud - Generation of a word cloud image from the copy-edited text (using word_cloud MCP tool)
4. Achievements extractor - Extraction of the key achievements from the copy-edited text (using extract_achievements in-house ADK tool)
5. Review text evaluator - Evaluation of the copy-edited text to generate a review scorecard (using evaluate_review_text in-house ADK tool)

'''

@lru_cache(maxsize=1)
def _get_modifiers() -> TextModifiers:
    """Lazy, cached TextModifiers accessor for the ADK tools."""
    return TextModifiers()


@lru_cache(maxsize=1)
def _get_achievement_evaluator() -> AchievementEvaluator:
    """Lazy, cached AchievementEvaluator accessor for contextualization."""
    vector_db = EmbeddedVectorDB()
    embedder = SimpleTextEmbedder()
    return AchievementEvaluator(vector_db=vector_db, embedder=embedder)


def _convert_achievement_evaluations_to_achievements(
    achievement_evaluations: List[AchievementEvaluation],
    size: int,
    unit: str,
) -> AchievementsList:
    """Convert achievement evaluations to AchievementsList."""
    updated_achievements = []
    for achievement_evaluation in achievement_evaluations:
        updated_achievement = achievement_evaluation.achievement
        updated_achievement.contribution = achievement_evaluation.contribution
        updated_achievement.rationale = achievement_evaluation.rationale
        updated_achievement.project_name = achievement_evaluation.project.name
        updated_achievement.project_text = achievement_evaluation.project.text
        updated_achievement.project_department = achievement_evaluation.project.department
        updated_achievement.project_impact_category = achievement_evaluation.project.impact_category
        updated_achievement.project_effort_size = achievement_evaluation.project.effort_size
        updated_achievements.append(updated_achievement)

    return AchievementsList(items=updated_achievements, size=size, unit=unit)


def _contextualize_achievements(achievements: AchievementsList) -> AchievementsList:
    """Contextualize achievements with project metadata and contribution levels."""
    if not achievements.items:
        return achievements

    evaluator = _get_achievement_evaluator()
    try:
        evaluations = evaluator.contextualize(achievements=achievements)
        if not evaluations:
            return achievements
        return _convert_achievement_evaluations_to_achievements(
            evaluations,
            achievements.size,
            achievements.unit,
        )
    except Exception as exc:  # noqa: BLE001
        logger.error("Failed to contextualize achievements: %s", exc)
        return achievements

# ---- MCP Tools ----
mcp_toolset = McpToolset(
    connection_params=StreamableHTTPConnectionParams(url="http://localhost:3333/mcp"),
    tool_filter=["copy_edit", "abstractive_summarize", "word_cloud"]
    )
# ---------------------------------------------------------------------
# Function Tools (ADK-native)
# ---------------------------------------------------------------------

async def update_session_state(
    tool_context: ToolContext, 
    session_state_key: Literal["original_text", "reviewed_text", "summarized_text", "wordcloud_path"], 
    value: Any,
) -> dict:
    """
    Updates session state with a key-value pair.
    
    Args:
        tool_context: The tool context providing access to session and other services.
        session_state_key: Key of the session state to update.
        value: Value to set for the session state key.
    
    Returns:
        dict: Confirmation that state was updated.
    """
    print(f"Updating session state for key: {session_state_key} with value: {value}")
    # Update the session state - the session object is mutable and persisted automatically
    tool_context.state[session_state_key] = value
    
    return {"status": "updated"}

async def extract_achievements_tool(tool_context: ToolContext) -> dict:
    """
    Extracts achievements from reviewed text and stores them in session.state.
    
    Requires that reviewed_text be already set in session.state (from copy_edit MCP tool).
    
    Args:
        tool_context: The tool context providing access to session and other services.
    
    Returns:
        dict: A dictionary containing the extracted achievements.
    """
    reviewed = tool_context.state.get("reviewed_text", "")
    if not reviewed:
        return {"error": "reviewed_text not found in session state. Please call copy_edit tool first."}
    
    modifiers = _get_modifiers()
    achievements = await asyncio.to_thread(modifiers.extract_achievements, text=reviewed)
    achievements = await asyncio.to_thread(_contextualize_achievements, achievements)
    tool_context.state["achievements"] = achievements
    # Set review_complete based on number of achievements extracted
    achievement_count = len(achievements.items) if achievements and hasattr(achievements, "items") else 0
    tool_context.state["review_complete"] = achievement_count >= 3
    return {"achievements": achievements}

async def evaluate_text_tool(tool_context: ToolContext) -> dict:
    """
    Evaluates the reviewed text and stores evaluation results in session.state.
    
    Requires that reviewed_text be already set in session.state (from copy_edit MCP tool).
    
    Args:
        tool_context: The tool context providing access to session and other services.
    
    Returns:
        dict: A dictionary containing the evaluation results.
    """
    reviewed = tool_context.state.get("reviewed_text", "")
    if not reviewed:
        return {"error": "reviewed_text not found in session state. Please call copy_edit tool first."}
    
    modifiers = _get_modifiers()
    evaluation = await asyncio.to_thread(modifiers.evaluate_review_text, text=reviewed)
    tool_context.state["evaluation"] = evaluation
    return {"evaluation": evaluation}

# ---------------------------------------------------------------------
# LLM Agent — uses GPT-4o-mini to decide tool invocation order
# ---------------------------------------------------------------------
class ReviewAgent(LlmAgent):
    def __init__(self):
        super().__init__(
            name="text_review_agent",
            description=(
                "An intelligent text-processing agent that: "
                "1. Reviews text for grammar/typos "
                "2. Summarizes the reviewed text "
                "3. Generates a wordcloud "
                "4. Extracts achievements "
                "5. Evaluates the reviewed text"
            ),
            model=LiteLlm(model="gpt-4o"),
            tools=[
                mcp_toolset,
                update_session_state,
                extract_achievements_tool,
                evaluate_text_tool,
            ],
            instruction=(
                '''
                You are an intelligent self-reviewer assistant. 
                
                For each input text:
                1. You will update the session state with the key 'original_text' having the value as the input text.
                2. You will fix grammar/typos and update the session state with the key 'reviewed_text' having the value as the copy-edited text.
                3. You will summarize the reviewed text and update the session state with the key 'summarized_text' having the value as the summarized text.
                4. You will generate a wordcloud and update the session state with the key 'wordcloud_path' having the value as the path to the wordcloud image.
                5. You will extract the achievements and update the session state with the key 'achievements' having the value as the extracted achievements.
                6. You will evaluate the reviewed text and update the session state with the key 'evaluation' having the value as the evaluation results.
                
                Make sure to call the update_session_state tool at the beginning of the process to update
                the session state for the "original_text" key. 
                
                Thereafter, as and when you call the respective MCP tools, you will also call the update_session_state tool
                to update the session state for the "reviewed_text", "summarized_text", and "wordcloud_path" keys immediately after the 
                MCP tool call.

                For the "achievements" and "evaluation" keys, you will call the extract_achievements_tool and evaluate_text_tool 
                respectively and they will internally update the session state for the "achievements" and "evaluation" keys.
                '''
            ),
            output_key="final_agent_response"
        )
