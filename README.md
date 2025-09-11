
# AI Agents Session

## Goal 

Introduction on AI Agents, and what it can do.

### Proposed method

#### Context

In a typical large organization, every employee is expected to write a self-evaluation of their own performance, what they did and what contributions they brought. **There is a rubric of the key points – such as impact, that they must cover**. Unfortunately, employees write either too verbose, too generic or other ways imperfect self-evaluations.

#### AI Agents based Self-Evaluation Builder

Build an application for self-evaluation during performance review cycles. It will contain a main text-area in the UI. As the user types, an ambient agent will be observing the text, and comparing it to the rubric, putting tick-marks and progress-bars around key elements of the rubric. Let us call this agent the “Observer Agent”. Then we can have another agent, whose job would be to suggest more powerful rewordings, or ask the user to elaborate on certain points to get more details. Let us call this agent “The Guide Agent”. When the user has completely entered all the text (with typos and grammatical errors), there will be another agent that will suggest rewordings “The Copy Editor Agent”. Finally, there will be a Reviewer agent that will ensure that the self-evaluation is complete with respect to the rubric, and will create extractions of the keywords (word-cloud), and a 100 word abstractive summarization.

All the collaborations will be mediated by an orchestration agent (Supervisor Agent)

##### The MCP Tools

* Copy editing tool
* Keywords-extraction tool with Spacy
* Abstractive summarizer

##### User Interface

For now, we will make the user-interface in Streamlit.



## Action Items

* Build this application in LangGraph, and FastMCP
* Create an architecture diagram for it
* Next, take a copy of this application, gut out the “Agent prompts”, and make it a coding exercise, where the participants have to write the appropriate prompt to make it work.
* Create a fill-in-the-blanks for a simple MCP tool, such as “Abstractive summarizer”


====================

## Steps

Create an MCP server, with some basic tools given above, and keeps many critical functionality outside LangGraph (so there is not that much vendor lockin)

**Copy Editing Tool** Take a text and clean up the language minimally, fixing grammatical errors, but leaving the diction as that of the original text. (In other words, do not rewrite the structure of the text itself.)
**Keywords-extraction tool** To create a word-cloud
**Abstractive summarization**

## Getting Started

Follow these steps to run the **Employee Self-Review Wizard** application:

### 1. Environment Setup
First, update the environment configuration by copying the example file and updating relevant variables:
```bash
cp .env.example .env
# Edit .env with your specific configuration values
```

### 2. Install Dependencies
Create the virtual environment and install all dependencies:
```bash
uv sync
```

### 3. Start the MCP Tools Server
Run the MCP tools server to provide the core functionality:
```bash
uv run ./src/metamorphosis/mcp/tools_server.py
```

### 4. Start the Agent Service
In a separate terminal, run the FastAPI service that hosts the LangGraph agents:
```bash
uv run ./src/metamorphosis/agents/agent_service.py
```

### 5. Launch the User Interface
Finally, start the Streamlit UI in another terminal:
```bash
streamlit run ./src/metamorphosis/ui/streamlit_ui.py
```

Once all services are running, you can access the application through the Streamlit interface in your web browser.