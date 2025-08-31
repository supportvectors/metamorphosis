
from fastmcp import FastMCP, tool
from wordcloud import WordCloud
import spacy

import text_modifiers
from text_modifiers import SummarizedText, CopyEditedText

@tool("copy_edit")
def copy_edit(text: str) -> CopyEditedText:
    return text_modifiers.copy_edit(text)

@tool("word_cloud")
def create_word_cloud(text: str) -> WordCloud:
    """
    Create a word cloud from the text.
    """
    return WordCloud(text).generate()

@tool("abstractive_summarize")
def abstractive_summarize(text: str, max_words: int = 300) -> SummarizedText:
    return text_modifiers.summarize(text)

if __name__ == "__main__":
    FastMCP().serve(host="0.0.0.0", port=3333)
