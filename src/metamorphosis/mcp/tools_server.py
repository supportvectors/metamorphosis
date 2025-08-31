
from fastmcp import FastMCP, tool
from wordcloud import WordCloud
import spacy

nlp = spacy.load("en_core_web_sm")

@tool("copy_edit")
def copy_edit(text: str) -> str:
    # Light grammar/spelling suggestion — for demo, keep it simple or call your LLM locally
    # IMPORTANT: do not restructure; preserve voice.
    return lightweight_fix(text)

@tool("word_cloud")
def create_word_cloud(text: str, top_k: int = 30):
    """
    Create a word cloud from the text.
    """
    return WordCloud(text, top_k).generate()

@tool("abstractive_summarize")
def abstractive_summarize(text: str, max_words: int = 100):
    # For teaching, call an LLM with a strict length guard. Or stub a simpler baseline.
    return summarize_with_llm(text, max_words)

if __name__ == "__main__":
    FastMCP().serve(host="0.0.0.0", port=3333)
