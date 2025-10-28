# =============================================================================
#  Filename: adk_agents .py
#
#  Short Description: ADK agents for the periodic employee self-review process.
#
#  Creation date: 2025-10-27
#  Author: Chandar L
# =============================================================================
import asyncio
import logging
import warnings
from functools import lru_cache
from google.adk.tools.tool_context import ToolContext
from google.adk.agents import LlmAgent
from google.adk.models.lite_llm import LiteLlm
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.adk.tools.mcp_tool import McpToolset, StreamableHTTPConnectionParams

from metamorphosis.mcp.text_modifiers import TextModifiers

# Suppress authentication warnings from ADK tools
warnings.filterwarnings("ignore", message=".*auth_config or auth_config.auth_scheme is missing.*")
logging.getLogger("google_adk.google.adk.tools.base_authenticated_tool").setLevel(logging.ERROR)
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

# ---- MCP Tools ----
mcp_toolset = McpToolset(
    connection_params=StreamableHTTPConnectionParams(url="http://localhost:3333/mcp"),
    tool_filter=["copy_edit", "abstractive_summarize", "word_cloud"]
    )
# ---------------------------------------------------------------------
# Function Tools (ADK-native)
# ---------------------------------------------------------------------

async def update_state_from_mcp_output(tool_context: ToolContext, mcp_tool_name: str, text_data: str) -> dict:
    """
    Updates session state with data from MCP tool outputs.
    
    Args:
        tool_context: The tool context providing access to session and other services.
        mcp_tool_name: Name of the MCP tool that generated the output.
        text_data: The text data from the MCP tool response.
    
    Returns:
        dict: Confirmation that state was updated.
    """
    # Update the session state - the session object is mutable and persisted automatically
    if mcp_tool_name == "copy_edit":
        tool_context.state["reviewed_text"] = text_data
    elif mcp_tool_name == "abstractive_summarize":
        tool_context.state["summarized_text"] = text_data
    elif mcp_tool_name == "word_cloud":
        tool_context.state["wordcloud_path"] = text_data
    else:
        return {"status": "no_update"}
    
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
    achievements = modifiers.extract_achievements(text=reviewed)
    tool_context.state["achievements"] = achievements
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
    evaluation = modifiers.evaluate_review_text(text=reviewed)
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
            model=LiteLlm(model="gpt-4o-mini"),
            tools=[
                mcp_toolset,
                update_state_from_mcp_output,
                extract_achievements_tool,
                evaluate_text_tool,
            ],
            instruction=(
                "You are a text improvement assistant. For each input text:\n"
                "1. Call the copy_edit MCP tool to fix grammar/typos.\n"
                "2. IMMEDIATELY AFTER, call update_state_from_mcp_output with mcp_tool_name='copy_edit' and text_data=<the copy_edited_text from the result>.\n"
                "3. Call abstractive_summarize MCP tool on the reviewed text.\n"
                "4. IMMEDIATELY AFTER, call update_state_from_mcp_output with mcp_tool_name='abstractive_summarize' and text_data=<the summarized_text from the result>.\n"
                "5. Call word_cloud MCP tool on the reviewed text.\n"
                "6. IMMEDIATELY AFTER, call update_state_from_mcp_output with mcp_tool_name='word_cloud' and text_data=<the wordcloud path from the result>.\n"
                "7. Call extract_achievements_tool (reads from reviewed_text in state).\n"
                "8. Call evaluate_text_tool (reads from reviewed_text in state).\n"
                "Extract the text data from MCP tool responses and pass it to update_state_from_mcp_output."
            ),
            output_key="final_agent_response"
        )

# ---------------------------------------------------------------------
# Runner / Session orchestration
# ---------------------------------------------------------------------
async def main():
    app_name = "self_reviewer_gadk"
    user_id = "user_123"
    session_id = "session_abc"

    # Create a session service and session
    session_service = InMemorySessionService()
    await session_service.create_session(
        app_name=app_name,
        user_id=user_id,
        session_id=session_id,
        state={},
    )

    # Initialize agent and runner
    agent = ReviewAgent()
    runner = Runner(agent=agent, session_service=session_service, app_name=app_name)

    # Provide input text
    from google.genai import types
    
    user_input = types.Content(
        parts=[types.Part(text="Ths is an exampel text with some typos and achievements like winning hackathon.")]
    )

    # Run the agent (the LLM will autonomously call the tools) - collect all events
    # Use async context manager to ensure proper cleanup
    events = []
    async with runner:
        async for event in runner.run_async(user_id=user_id, session_id=session_id, new_message=user_input):
            events.append(event)
        print("\n--- COLLECTED EVENTS ---")
        for event in events:
            print(f"Event type: {event.author}, content: {event.content}")

    print("\n--- SESSION STATE ---")
    final_session = await session_service.get_session(app_name=app_name,
                                                        user_id= user_id,
                                                        session_id=session_id)
    print(final_session.state)

    # Close the MCP toolset to prevent resource leaks
    await mcp_toolset.close()

if __name__ == "__main__":
    asyncio.run(main())