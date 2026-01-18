# =============================================================================
#  Filename: main.py
#
#  Short Description: Main execution script for the ADK self-reviewer agent.
#
#  Creation date: 2025-10-27
#  Author: Chandar L
# =============================================================================
import asyncio
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService

from metamorphosis.agents.self_reviewer_gadk.agent import ReviewAgent, mcp_toolset

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
    
    original_text = "Ths is an exampel text with some typos and achievements like winning hackathon."
    user_input = types.Content(
        parts=[types.Part(text=original_text)]
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
                                                        
    from rich import print as rprint
    rprint(final_session.state)

    # Close the MCP toolset to prevent resource leaks
    await mcp_toolset.close()

if __name__ == "__main__":
    asyncio.run(main())
