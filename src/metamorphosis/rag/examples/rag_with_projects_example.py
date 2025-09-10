# =============================================================================
#  Filename: rag_with_projects_example.py
#
#  Short Description: Example demonstrating RAG functionality with ProjectsRag class.
#
#  Creation date: 2025-01-06
#  Author: Asif Qamar
# =============================================================================

"""
Example: RAG (Retrieval Augmented Generation) with ProjectsRag

This example shows two simple, project-relevant use cases:
1) Find projects related to a specific topic (e.g., feature store rollout)
2) Filter search by department (e.g., Data Platform) for targeted discovery

ProjectsRag auto-bootstraps by loading and indexing
`project_documents/project_portfolio.jsonl` if the collection is empty.
"""

import sys
from pathlib import Path

# Add the src directory to the path so we can import our modules
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from metamorphosis.rag.corpus.projects_rag import ProjectsRag
from metamorphosis.rag.vectordb.embedded_vectordb import EmbeddedVectorDB
from metamorphosis.rag.vectordb.embedder import SimpleTextEmbedder
from loguru import logger


def main():
    """Minimal, project-focused demo for ProjectsRag."""
    print("🎯 RAG with ProjectsRag — Minimal Project Examples")
    print("=" * 70)

    # Initialize components (auto-bootstrap will index default portfolio if empty)
    print("\n1️⃣ Initializing...")
    vector_db = EmbeddedVectorDB()
    embedder = SimpleTextEmbedder(model_name="sentence-transformers/all-MiniLM-L6-v2")
    projects = ProjectsRag(vector_db=vector_db, embedder=embedder)
    print("   ✅ Ready")

    # Example 1 — Topic search (feature store rollout)
    print("\n2️⃣ Topic search: 'feature store real-time offers'")
    topic_query = "feature store real-time offers"
    results_topic = projects.search(query=topic_query, limit=5)
    projects.display_search_results(
        results=results_topic,
        search_description="Feature store related projects",
        max_text_length=100,
    )

    # Example 2 — Department-filtered search (Data Platform)
    print("\n3️⃣ Department-filtered search: 'data quality' in 'Data Platform'")
    dept_query = "data quality"
    results_dept = projects.search(
        query=dept_query,
        limit=5,
        department="Data Platform",
    )
    projects.display_search_results(
        results=results_dept,
        search_description="Data Platform — data quality projects",
        max_text_length=100,
    )

    print("\n✅ Examples completed!")
    return True


def demonstrate_rag_context_structure():
    """Demonstrate the structure of the generated RAG context."""
    
    print("\n🔍 RAG Context Structure Analysis")
    print("=" * 50)
    
    # Initialize components
    vector_db = EmbeddedVectorDB()
    embedder = SimpleTextEmbedder()
    projects = ProjectsRag(vector_db=vector_db, embedder=embedder)
    
    # Create a simple example
    user_query = "a friendship with projects"
    search_results = projects.search(user_query, limit=2)
    
    # Show the formatted results
    print("\n📝 Formatted Search Results:")
    formatted_results = projects.format_search_results_for_rag(search_results)
    print(formatted_results)
    
    # Show the complete context
    print("\n📋 Complete RAG Context Structure:")
    rag_context = projects.create_rag_context(user_query, search_results)
    
    # Split and display sections
    sections = rag_context.split("##")
    for i, section in enumerate(sections, 1):
        if section.strip():
            print(f"\n--- Section {i} ---")
            print(section.strip())


if __name__ == "__main__":
    try:
        # Run the main example
        success = main()
        if not success:
            sys.exit(1)
        
    except Exception as e:
        logger.error(f"Example failed: {str(e)}")
        print(f"❌ Example failed: {str(e)}")
        sys.exit(1)


#============================================================================================ 