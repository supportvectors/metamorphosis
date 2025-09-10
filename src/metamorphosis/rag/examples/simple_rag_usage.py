# =============================================================================
#  Filename: simple_rag_usage.py
#
#  Short Description: Simple example of using the rag() facade method.
#
#  Creation date: 2025-01-06
#  Author: Asif Qamar
# =============================================================================

"""
Simple example showing how to use the rag() facade method.

This demonstrates the minimal code needed to get a complete RAG response
from the ProjectsRag class.
"""

import sys
from pathlib import Path

# Add the src directory to the path so we can import our modules
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from metamorphosis.rag.corpus.projects_rag import ProjectsRag
from metamorphosis.rag.vectordb.embedded_vectordb import EmbeddedVectorDB
from metamorphosis.rag.vectordb.embedder import SimpleTextEmbedder


def main():
    """Simple example of using the rag() facade method."""
    print("🎯 Simple RAG Usage Example")
    print("=" * 40)
    
    # Initialize components
    vector_db = EmbeddedVectorDB()
    embedder = SimpleTextEmbedder()
    projects = ProjectsRag(vector_db=vector_db, embedder=embedder)
    
    # User query
    query = "What makes golden retrievers so special?"
    
    print(f"\n📝 Query: '{query}'")
    
    # Single method call for complete RAG pipeline
    result = projects.rag(
        user_query=query,
        limit=3,
        response_type="structured"
    )
    
    # Access the results
    llm_response = result['llm_response']
    search_results = result['search_results']
    
    print(f"\n✅ Found {len(search_results)} relevant items")
    print(f"🤖 LLM Answer: {llm_response.answer[:100]}...")
    print(f"💡 Key Insights: {len(llm_response.key_insights)} insights")
    
    # Display the full response
    projects.display_llm_response(llm_response, query)


if __name__ == "__main__":
    main()


#============================================================================================ 