# tools_server/server.py (outline)
# Pseudocode — adapt to your MCP framework / FastMCP wrapper
from mcp import Server, tool
import spacy

nlp = spacy.load("en_core_web_sm")

@tool("copy_edit")
def copy_edit(text: str) -> str:
    # Light grammar/spelling suggestion — for demo, keep it simple or call your LLM locally
    # IMPORTANT: do not restructure; preserve voice.
    return lightweight_fix(text)

@tool("extract_keywords")
def extract_keywords(text: str, top_k: int = 20):
    doc = nlp(text.lower())
    cands = [t.lemma_ for t in doc if t.pos_ in ("NOUN","PROPN") and not t.is_stop]
    # trivial frequency baseline for workshop
    freq = {}
    for c in cands: freq[c] = freq.get(c,0)+1
    return [w for w,_ in sorted(freq.items(), key=lambda x: x[1], reverse=True)[:top_k]]

@tool("abstractive_summarize")
def abstractive_summarize(text: str, max_words: int = 100):
    # For teaching, call an LLM with a strict length guard. Or stub a simpler baseline.
    return summarize_with_llm(text, max_words)

if __name__ == "__main__":
    Server().serve(host="0.0.0.0", port=3333)
