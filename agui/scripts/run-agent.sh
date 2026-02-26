#!/bin/bash

# Navigate to the agent directory
cd "$(dirname "$0")/../../" || exit 1

# Activate the virtual environment
source .venv/bin/activate

# Run the agent
uv run src/metamorphosis/mcp/tools_server.py &

uv run src/metamorphosis/agents/agent_service_gadk.py
