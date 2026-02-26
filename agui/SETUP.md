# Self-Review Agent Setup Guide

This Next.js application connects to your ADK-based self-review agent service via the AG-UI protocol.

## Architecture

- **Backend**: FastAPI service (`src/metamorphosis/agents/agent_service_gadk.py`) and MCP Tools Server (`src/metamorphosis/mcp/tools_server.py`). The FastAPI service exposes:
  - `/invoke` - Synchronous processing endpoint
  - `/stream` - SSE streaming endpoint
  - `/agui` - AG-UI endpoint for CopilotKit

- **Frontend**: Next.js app with CopilotKit that connects to the `/agui` endpoint (`src/app/api/copilotkit/route.ts`).

## Prerequisites

- **Node.js** 18+ and a package manager (`pnpm` recommended). 

  <details>
    <summary>Click here for macos steps to install Node.js and pnpm</summary>

    ```bash
    # Download and install nvm:
    curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.40.4/install.sh | bash
    # in lieu of restarting the shell
    \. "$HOME/.nvm/nvm.sh"
    # Download and install Node.js:
    nvm install 24
    # Verify the Node.js version:
    node -v # Should print "v24.14.0".
    # Download and install pnpm:
    corepack enable pnpm
    # Verify pnpm version:
    pnpm -v
    ```
    
  </details>
  <br>

- **Python** 3.12+ and [`uv`](https://docs.astral.sh/uv/) installed (required for running the Python backend).
- **Environment Variables**:
  - `OPENAI_API_KEY`: Required by the ADK agent (which uses `gpt-4o`).

## Setup Steps

1. **Install Dependencies**:
   ```bash
   cd agui
   pnpm install 
   ```
   > **Note:** The `postinstall` script will automatically run `uv sync` to set up the Python virtual environment (`.venv`) for the backend.

2. **Configure Environment**:
   ```bash
   cp .env.example .env
   ```
   Make sure to edit `.env` and insert your `OPENAI_API_KEY`.

3. **Start the Development Servers**:
   ```bash
   pnpm dev
   ```
   This single command concurrently starts:
   - The Next.js UI (`localhost:3000`)
   - The FastAPI ADK Agent Service (`localhost:8000`)
   - The MCP Tools Server (`localhost:3333`)

4. **Access the Application**:
   - Open [http://localhost:3000](http://localhost:3000) in your browser.
   - The CopilotKit sidebar will be open by default.
   - Enter your review text and click "Process Review".

## How It Works

1. **User Input**: User enters review text in the textarea and clicks "Process Review".
2. **State Update**: Frontend updates `original_text` in shared state via `setState()`.
3. **Agent Processing**: The ADK agent (`text_review_agent`) processes the text:
   - Calls `copy_edit` MCP tool → updates `reviewed_text`
   - Calls `abstractive_summarize` MCP tool → updates `summarized_text`
   - Calls `word_cloud` MCP tool → updates `wordcloud_path`
   - Calls `extract_achievements_tool` → updates `achievements`
   - Calls `evaluate_text_tool` → updates `evaluation`
4. **UI Updates**: Frontend automatically re-renders as state updates arrive.
5. **Results Display**: All results are shown in organized sections.

## Key Files

- `src/app/api/copilotkit/route.ts` - API route connecting to the AG-UI backend.
- `src/app/page.tsx` - Main page component with CopilotKit sidebar.
- `src/components/self-review.tsx` - Self-review UI component tabs.
- `src/lib/types.ts` - TypeScript types matching ADK agent state.
- `scripts/run-agent.sh` - Bash script to launch the Python agent and tools servers.

## Troubleshooting

### Agent Not Connecting
- Wait for all servers to fully start after running `pnpm dev`.
- Verify the backend is running by navigating to `http://localhost:8000/docs` in your browser.
- Check if `AGENT_URL` in `.env.local` accurately matches your backend URL.
- Ensure the agent name matches `text_review_agent` (defined in `agent.py`).

### State Not Updating
- Check the browser console for CopilotKit frontend errors.
- Verify the MCP tools server (`localhost:3333`) is running in the terminal output.
- Check backend logs for agent execution LLM errors (e.g. invalid OpenAI key).

### Word Cloud Not Displaying
- Verify the path in `wordcloud_path` is accessible.
- Check if the image file exists at the specified path.
- The UI will show an error if the image cannot be loaded.

## Next Steps

- Customize the UI styling in `src/components/self-review.tsx`.
- Add more frontend tools for interactive features.
- Implement generative UI for tool calls.
- Add human-in-the-loop features for approval workflows.
