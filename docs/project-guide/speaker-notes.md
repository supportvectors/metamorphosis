### Speaker Notes (Metamorphosis Talk)

These notes are designed for a 20–25 minute session.

## Timing & Flow
- 0:00–2:00 — Welcome and goal: keep things simple, learn by building
- 2:00–5:00 — What are agents? (workflow + tools + state)
- 5:00–9:00 — Show the workflow diagram and explain branches
- 9:00–17:00 — Live demo: run WorkflowExecutor and narrate events
- 17:00–20:00 — Lessons learned + Q&A buffer

## Demo Checklist
- Terminal ready with `OPENAI_API_KEY` set
- From project root, open a Python REPL or a short script to:
  1. Create `WorkflowExecutor`
  2. `await initialize()`
  3. `await run_workflow(sample_text, thread_id="demo-1")`
  4. Print or view `word_cloud_path`

## Narration Tips
- Emphasize the tiny pieces: copy edit → summarize → visualize
- Explain that tools are normal functions behind a friendly interface
- Show that branching is readable and relies on small decisions

## Recovery Plan
- If the LLM call is slow: pre-load a saved result and explain it
- If network is flaky: walk through the diagrams and code structure

## Links to show
- Agents overview: `metamorphosis/agents/index.md`
- Self Reviewer package: `metamorphosis/agents/self_reviewer/index.md`
- TextModifiers class: `metamorphosis/mcp/TextModifiers.md`






