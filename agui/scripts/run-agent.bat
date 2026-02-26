@echo off
REM Navigate to the agent directory
cd /d %~dp0\..\..\

REM Activate the virtual environment
call .venv\Scripts\activate.bat

REM Run the agent
uv run main.py
