# =============================================================================
#  Filename: projects_rag.py
#
#  Short Description: Project portfolio corpus loader with Pydantic models for Qdrant vectorization.
#
#  Creation date: 2025-01-06
#  Author: Asif Qamar
# =============================================================================

import json
from pathlib import Path
from typing import List, Optional, Dict, Any
from icontract import require, ensure
from pydantic import BaseModel, Field, field_validator
from qdrant_client import models
from loguru import logger

# Import instructor and OpenAI for LLM integration
import instructor
from openai import OpenAI

from metamorphosis.rag.vectordb.embedded_vectordb import EmbeddedVectorDB
from metamorphosis.rag.vectordb.embedder import SimpleTextEmbedder
from metamorphosis.rag.search.semantic_search import SemanticSearch
from metamorphosis.rag.exceptions import InvalidPointsError
from metamorphosis.rag.corpus.project_data_models import Project, ProjectPortfolio


#============================================================================================
#  Class: ProjectsRag
#============================================================================================
class ProjectsRag:
    """A powerful, intelligent corpus loader for project portfolios with RAG capabilities.
    
    This class provides a complete solution for working with collections of projects,
    offering semantic search, AI-powered question answering, and beautiful result display.
    Perfect for educational applications, research, or building chatbots that need access
    to organizational project knowledge.
    
    Key Features:
        - Load projects from JSONL files with automatic validation
        - Semantic search using state-of-the-art embeddings
        - Filter by department, impact category, or similarity score
        - AI-powered question answering with GPT models
        - Beautiful formatted output with Rich library
        - Complete RAG (Retrieval-Augmented Generation) pipeline
        - Batch operations for efficiency
    
    Typical Workflow:
        1. Initialize with a vector database
        2. Load projects from a JSONL file
        3. Index projects for semantic search
        4. Search for relevant projects
        5. Ask AI questions about the projects
    
    Example:
        ```python
        from pathlib import Path
        from metamorphosis.rag.vectordb.embedded_vectordb import EmbeddedVectorDB
        from metamorphosis.rag.corpus.projects_rag import ProjectsRag
        
        # Initialize
        vector_db = EmbeddedVectorDB()
        projects = ProjectsRag(vector_db=vector_db, collection_name="my_projects")
        
        # Load and index projects
        projects_file = Path("data/projects.jsonl")
        projects.load_and_index(projects_file)
        
        # Search for projects
        results = projects.search("analytics dashboard", limit=5)
        
        # Ask AI a question
        response = projects.ask_llm("What projects did Analytics deliver last quarter?")
        projects.display_llm_response(response, "analytics portfolio")
        ```
    
    Attributes:
        embedder: Text embedding model for vector representations
        collection_name: Name of the Qdrant collection storing the projects
        wisdom: Loaded collection of projects (None until loaded)
        semantic_search: Underlying search engine for similarity queries
    """
    
    # ----------------------------------------------------------------------------------------
    #  Constructor
    # ----------------------------------------------------------------------------------------
    @require(lambda vector_db: isinstance(vector_db, EmbeddedVectorDB),
             "Vector DB must be an EmbeddedVectorDB instance")
    @require(lambda embedder: embedder is None or isinstance(embedder, SimpleTextEmbedder),
             "Embedder must be None or a SimpleTextEmbedder instance")
    def __init__(self, vector_db: EmbeddedVectorDB, 
                 embedder: Optional[SimpleTextEmbedder] = None,
                 collection_name: str = "projects") -> None:
        """Initialize your project portfolio with intelligent search capabilities.
        
        Sets up the complete infrastructure for loading, indexing, and searching projects.
        The system uses advanced sentence transformers for semantic understanding
        and can work with any size collection efficiently.
        
        Args:
            vector_db: Your vector database instance where projects will be stored.
                This handles all the vector storage and retrieval operations.
            embedder: Optional text embedding model. If None, uses the default
                'sentence-transformers/all-MiniLM-L6-v2'.
            collection_name: Unique name for your project collection.
        
        Example:
            ```python
            # Basic setup with default embedder
            projects = ProjectsRag(vector_db=vector_db)
            
            # Custom setup with specific collection
            projects = ProjectsRag(
                vector_db=my_db,
                collection_name="analytics_projects"
            )
            
            # Advanced setup with custom embedder
            custom_embedder = SimpleTextEmbedder(model_name="custom-model")
            projects = ProjectsRag(vector_db=vector_db, embedder=custom_embedder)
            ```
        
        Note:
            The constructor automatically loads the RAG system prompt for AI interactions.
            If the prompt file is missing, a warning is logged but the system continues
            to work with reduced AI capabilities.
        """
        self.embedder = embedder or SimpleTextEmbedder()
        self.collection_name = collection_name
        self.wisdom: Optional[ProjectPortfolio] = None
        
        # Initialize the underlying semantic search engine
        self.semantic_search = SemanticSearch(
            embedder=self.embedder,
            vector_db=vector_db,
            collection_name=collection_name
        )
        
        logger.info(f"Initialized Projects corpus loader for collection '{collection_name}'")
        if not ProjectsRag.PROJECTS_RAG_SYSTEM_PROMPT:
            ProjectsRag.PROJECTS_RAG_SYSTEM_PROMPT = self._load_system_prompt()

        # Auto-bootstrap: if the collection is empty, try to load and index a default portfolio
        try:
            points_count = self.semantic_search.vector_db.count_points(
                collection_name=self.collection_name
            )
            if points_count == 0:
                default_file = self._find_default_portfolio_file()
                if default_file is not None and default_file.exists():
                    logger.info(
                        f"Auto-bootstrap: indexing default project portfolio from {default_file}"
                    )
                    self.load_from_jsonl(default_file)
                    self.index_all_projects()
                else:
                    logger.info(
                        "Auto-bootstrap skipped: no default portfolio file found."
                    )
        except Exception as e:
            logger.warning(f"Auto-bootstrap failed (continuing without data): {e}")

    def _load_system_prompt(self) -> str:
        """Load the AI system prompt from external configuration file.
        
        Returns:
            The system prompt text for RAG operations, or empty string if unavailable.
        """
        try:
            return ProjectsRag.SYSTEM_PROMPT_PATH.read_text(encoding="utf-8")
        except Exception as e:
            logger.warning(f"Could not load system prompt: {e}")
            return ""

    def _find_default_portfolio_file(self) -> Optional[Path]:
        """Locate the default project portfolio JSONL file if present.

        Returns:
            Path to `project_documents/project_portfolio.jsonl` if it exists, else None.
        """
        try:
            repo_root = Path(__file__).resolve().parents[4]
            candidate = repo_root / "project_documents" / "project_portfolio.jsonl"
            return candidate if candidate.exists() else None
        except Exception:
            return None

    
    # ----------------------------------------------------------------------------------------
    #  Load from JSONL
    # ----------------------------------------------------------------------------------------
    @require(lambda jsonl_path: isinstance(jsonl_path, (str, Path)),
             "JSONL path must be a string or Path object")
    @ensure(lambda result: isinstance(result, ProjectPortfolio),
            "Must return a ProjectPortfolio instance")
    def load_from_jsonl(self, jsonl_path: Path) -> ProjectPortfolio:
        """Load and validate projects from a JSONL (JSON Lines) file.
        
        Reads a file where each line contains a JSON object with project data. The method
        performs comprehensive validation, skips malformed entries with helpful warnings,
        and returns a structured collection ready for indexing and search.
        
        Expected JSONL Format:
            Each line should be a JSON object with these fields:
            - "text": The project text/description (required)
            - "department": The department responsible (required)
            - "impact_category": Impact classification (required)
            - "effort_size": Effort size (required)
        
        Args:
            jsonl_path: Path to your JSONL file containing projects.
                Can be a string path or pathlib.Path object.
        
        Returns:
            ProjectPortfolio object containing all successfully loaded projects with
            convenient methods for filtering and analysis.
        
        Raises:
            FileNotFoundError: When the specified file doesn't exist at the given path.
            InvalidPointsError: When no valid projects are found in the file, indicating
                format issues or empty content.
        
        Example:
            ```python
            # Load projects from file
            projects_path = Path("data/projects.jsonl")
            portfolio = projects.load_from_jsonl(projects_path)
            
            print(f"Loaded {len(portfolio)} projects")
            print(f"Categories: {portfolio.get_categories()}")
            print(f"Departments: {portfolio.get_departments()}")
            
            # Access individual projects
            for project in portfolio.projects[:3]:
                print(f'"{project.text}" - {project.department}')
            ```
        
        File Format Example:
            ```
            {"text": "Migrate data warehouse to lakehouse architecture.", "department": "Data Platform", "impact_category": "High Impact", "effort_size": "Large"}
            {"text": "Launch customer analytics dashboard.", "department": "Analytics", "impact_category": "Medium Impact", "effort_size": "Medium"}
            ```
        
        Note:
            - Empty lines in the file are automatically skipped
            - Malformed JSON lines generate warnings but don't stop the process
            - The loaded projects are stored in self.wisdom for later use
            - All text fields are automatically stripped of whitespace
        """
        jsonl_path = Path(jsonl_path)
        
        if not jsonl_path.exists():
            raise FileNotFoundError(f"JSONL file not found: {jsonl_path}")
        
        try:
            quotes = []
            with open(jsonl_path, 'r', encoding='utf-8') as file:
                for line_num, line in enumerate(file, 1):
                    line = line.strip()
                    if not line:  # Skip empty lines
                        continue
                    
                    try:
                        data = json.loads(line)
                        project = Project(**data)
                        quotes.append(project)
                    except (json.JSONDecodeError, ValueError) as e:
                        logger.warning(f"Skipped invalid line {line_num} in {jsonl_path}: {e}")
                        continue
            
            if not quotes:
                raise InvalidPointsError(
                    issue=f"No valid projects found in {jsonl_path}",
                    points_count=0
                )
            
            self.wisdom = ProjectPortfolio(projects=quotes, source_file=jsonl_path)
            logger.info(f"Loaded {len(quotes)} projects from {jsonl_path}")
            return self.wisdom
            
        except Exception as e:
            raise InvalidPointsError(
                issue=f"Failed to load projects from {jsonl_path}: {str(e)}",
                points_count=0
            )
    
    # ----------------------------------------------------------------------------------------
    #  Index All Projects
    # ----------------------------------------------------------------------------------------
    @require(lambda self: self.wisdom is not None,
             "Project portfolio must be loaded before indexing")
    def index_all_projects(self) -> List[str]:
        """Transform all loaded projects into searchable vector embeddings.
        
        This method takes your loaded projects and creates high-dimensional vector
        representations that enable semantic search. The process uses advanced
        sentence transformers to understand the meaning and context.
        
        Returns:
            List of unique point IDs for each indexed project. These IDs can be used
            for direct retrieval, debugging, or managing specific projects.
        
        Raises:
            InvalidPointsError: When indexing fails due to embedding errors,
                database issues, or missing project data.
        
        Example:
            ```python
            # Load projects first
            portfolio = projects.load_from_jsonl("projects.jsonl")
            
            # Index for semantic search
            point_ids = projects.index_all_projects()
            print(f"Successfully indexed {len(point_ids)} projects")
            
            # Now you can search semantically
            results = projects.search("analytics dashboard")
            ```
        
        Performance Notes:
            - Batch processing is used for efficiency with large collections
            - Indexing time scales with collection size and model complexity
            - GPU acceleration automatically used if available
        
        Note:
            You must call load_from_jsonl() before indexing.
        """
        if not self.wisdom:
            raise InvalidPointsError(
                issue="No project portfolio loaded. Call load_from_jsonl() first.",
                points_count=0
            )
        
        try:
            # Prepare texts and metadata for batch indexing
            texts = [p.text for p in self.wisdom.projects]
            metadata_list = [p.to_payload() for p in self.wisdom.projects]
            
            # Use SemanticSearch's batch indexing capability
            indexed_ids = self.semantic_search.index_all_text(
                texts=texts,
                metadata_list=metadata_list
            )
            
            logger.info(f"Successfully indexed {len(indexed_ids)} projects into collection '{self.collection_name}'")
            return indexed_ids
            
        except Exception as e:
            raise InvalidPointsError(
                issue=f"Failed to index projects: {str(e)}",
                points_count=len(self.wisdom.projects) if self.wisdom else 0
            )
    
    # ----------------------------------------------------------------------------------------
    #  Collection Management
    # ----------------------------------------------------------------------------------------
    def recreate_collection(self) -> None:
        """Completely reset your project collection with a fresh, empty database.
        
        This is a powerful cleanup method that removes all existing points and
        creates a brand new collection. Use this when you need to start over,
        fix corruption issues, or completely change your dataset.
        """
        try:
            # Delete existing collection if it exists
            if self.semantic_search.vector_db.collection_exists(self.collection_name):
                logger.info(f"Deleting existing collection '{self.collection_name}'")
                self.semantic_search.vector_db.delete_collection(
                    collection_name=self.collection_name
                )
            
            # Create new empty collection
            logger.info(f"Creating new empty collection '{self.collection_name}'")
            self.semantic_search.vector_db.create_collection(
                collection_name=self.collection_name,
                vector_size=self.semantic_search.embedder.get_vector_size(),
                distance=self.semantic_search.embedder.get_distance_metric()
            )
            
            # Clear loaded data
            self.wisdom = None
            
            logger.info(f"Successfully recreated empty collection '{self.collection_name}'")
            
        except Exception as e:
            raise InvalidPointsError(
                issue=f"Failed to recreate collection: {str(e)}",
                points_count=0
            )
    
    # ----------------------------------------------------------------------------------------
    #  Load and Index
    # ----------------------------------------------------------------------------------------
    def load_and_index(self, jsonl_path: Path) -> tuple[ProjectPortfolio, List[str]]:
        """One-step solution: load projects from file and make them instantly searchable.
        
        This convenience method combines loading and indexing in a single call,
        perfect for getting up and running quickly. It handles the complete
        pipeline from raw JSONL file to searchable vector database.
        
        Args:
            jsonl_path: Path to your JSONL file containing projects.
        
        Returns:
            A tuple containing:
            - ProjectPortfolio: Your loaded and validated project collection
            - List[str]: Point IDs for all indexed projects
        
        Note:
            This method is equivalent to calling load_from_jsonl() followed by
            index_all_projects(), but more convenient for common workflows.
        """
        wisdom = self.load_from_jsonl(jsonl_path)
        point_ids = self.index_all_projects()
        return wisdom, point_ids
    
    # ----------------------------------------------------------------------------------------
    #  Search Projects
    # ----------------------------------------------------------------------------------------
    @require(lambda query: isinstance(query, str) and len(query.strip()) > 0,
             "Query must be a non-empty string")
    @require(lambda limit: isinstance(limit, int) and limit > 0,
             "Limit must be a positive integer")
    @require(lambda department: department is None or (isinstance(department, str) and len(department.strip()) > 0),
             "Department filter must be None or a non-empty string")
    @require(lambda impact_category: impact_category is None or (isinstance(impact_category, str) and len(impact_category.strip()) > 0),
             "Impact category filter must be None or a non-empty string")
    @ensure(lambda result: isinstance(result, list), "Must return a list")
    def search(self, query: str, limit: int = 10, 
              score_threshold: Optional[float] = None,
              department: Optional[str] = None,
              impact_category: Optional[str] = None) -> List[models.ScoredPoint]:
        """Find the most relevant projects using intelligent semantic search.
        
        Args:
            query: Your search text.
            limit: Maximum number of results to return (default: 10).
            score_threshold: Minimum similarity score (0.0-1.0).
            department: Filter results to only include projects by this department.
            impact_category: Filter results to only include projects in this impact category.
        
        Returns:
            List of ScoredPoint objects, each containing:
            - score: Similarity score (higher = more relevant)
            - payload: Project metadata (content, department, impact_category, effort_size)
            Results are automatically sorted by relevance (highest scores first).
        """
        try:
            # Use SemanticSearch for the core search functionality
            # Request more results than needed to allow for filtering
            search_limit = limit * 3 if (department or impact_category) else limit
            
            initial_results = self.semantic_search.search_with_text(
                query_text=query.strip(),
                limit=search_limit,
                score_threshold=score_threshold
            )
            
            # Apply metadata filters if specified
            filtered_results = self._apply_metadata_filters(
                results=initial_results,
                department_filter=department,
                impact_category_filter=impact_category
            )
            
            # Limit to requested number of results
            final_results = filtered_results[:limit]
            
            logger.info(
                f"Projects search for '{query[:50]}...' returned {len(final_results)} results"
                f"{' (filtered by department)' if department else ''}"
                f"{' (filtered by impact category)' if impact_category else ''}"
            )
            
            return final_results
            
        except Exception as e:
            raise InvalidPointsError(
                issue=f"Failed to search projects: {str(e)}",
                points_count=1
            )

    # ----------------------------------------------------------------------------------------
    #  Search Projects (as Domain Models)
    # ----------------------------------------------------------------------------------------
    @require(lambda query: isinstance(query, str) and len(query.strip()) > 0,
             "Query must be a non-empty string")
    @require(lambda limit: isinstance(limit, int) and limit > 0,
             "Limit must be a positive integer")
    @require(lambda department: department is None or (isinstance(department, str) and len(department.strip()) > 0),
             "Department filter must be None or a non-empty string")
    @require(lambda impact_category: impact_category is None or (isinstance(impact_category, str) and len(impact_category.strip()) > 0),
             "Impact category filter must be None or a non-empty string")
    @ensure(lambda result: isinstance(result, list), "Must return a list")
    def search_projects(self, query: str, limit: int = 10,
                        score_threshold: Optional[float] = None,
                        department: Optional[str] = None,
                        impact_category: Optional[str] = None) -> List[Project]:
        """Search projects and return them as `Project` domain objects.
        
        This helper wraps `search()` and maps each hit's payload into a
        strongly-typed `Project` instance. It enforces the presence of
        required fields and fails fast with a clear error if payloads are
        malformed.
        """
        try:
            hits = self.search(
                query=query,
                limit=limit,
                score_threshold=score_threshold,
                department=department,
                impact_category=impact_category,
            )

            projects: List[Project] = []
            for hit in hits:
                payload: Dict[str, Any] = hit.payload or {}

                if not all(k in payload for k in ("name", "content", "department", "impact_category", "effort_size")):
                    raise InvalidPointsError(
                        issue="Search hit payload missing required keys",
                        points_count=1,
                    )

                model_input = {
                    "name": payload.get("name", ""),
                    "text": payload.get("content", ""),
                    "department": payload.get("department"),
                    "impact_category": payload.get("impact_category"),
                    "effort_size": payload.get("effort_size"),
                }

                projects.append(Project(**model_input))

            return projects

        except InvalidPointsError:
            raise
        except Exception as e:
            raise InvalidPointsError(
                issue=f"Failed to map search results to Project models: {str(e)}",
                points_count=1,
            )
    
    # ----------------------------------------------------------------------------------------
    #  Get Collection Stats
    # ----------------------------------------------------------------------------------------
    def get_collection_stats(self) -> Dict[str, Any]:
        """Get comprehensive statistics and insights about your project collection.
        
        Returns:
            Dictionary containing detailed statistics:
            - collection_name: Name of your project collection
            - collection_exists: Whether the database collection exists
            - point_count: Total projects stored in the database
            - loaded_projects: Number of projects currently loaded in memory
            - categories: List of all unique project categories (sorted)
            - departments: List of all unique departments (sorted)
        """
        stats = {
            "collection_name": self.collection_name,
            "collection_exists": self.semantic_search.vector_db.collection_exists(self.collection_name),
            "point_count": 0,
            "loaded_projects": 0,
            "categories": [],
            "departments": []
        }
        
        if stats["collection_exists"]:
            stats["point_count"] = self.semantic_search.vector_db.count_points(
                collection_name=self.collection_name
            )
        
        if self.wisdom:
            stats["loaded_projects"] = len(self.wisdom)
            stats["categories"] = self.wisdom.get_categories()
            stats["departments"] = self.wisdom.get_departments()
        
        return stats
    
    # ----------------------------------------------------------------------------------------
    #  Additional SemanticSearch Integration
    # ----------------------------------------------------------------------------------------
    def consistency_check(self) -> bool:
        """Verify that your database collection is properly configured and ready to use."""
        return self.semantic_search.consistency_check()
    
    def index_single_project(self, project: Project) -> str:
        """Index a single project.
        
        Args:
            project: Project instance to index.
            
        Returns:
            Point ID of the indexed project.
        """
        return self.semantic_search.index_text(
            text=project.text,
            metadata=project.to_payload()
        )
    
    # ----------------------------------------------------------------------------------------
    #  RAG System Prompts
    # ----------------------------------------------------------------------------------------
    # Path to the external system prompt file
    SYSTEM_PROMPT_PATH = Path(__file__).parent / "prompts" / "projects_system_prompt.md"

    # Comprehensive RAG System Prompt for ProjectsRag Class (loaded at init time)
    PROJECTS_RAG_SYSTEM_PROMPT: str = ""

    # Alternative shorter version for quick use
    SIMPLE_PROJECTS_PROMPT = """
    You are an expert on organizational projects and portfolios. Use the provided search results 
    to answer questions about projects, departments, and outcomes. 
    Always attribute items to their department and explain their relevance to the user's question. 
    Be conversational, thoughtful, and helpful in connecting users with the insights 
    found in the project portfolio.
    """

    # ----------------------------------------------------------------------------------------
    #  RAG Helper Methods
    # ----------------------------------------------------------------------------------------
    @require(lambda search_results: isinstance(search_results, list), "Search results must be a list")
    @require(lambda max_results: isinstance(max_results, int) and max_results > 0,
             "Max results must be a positive integer")
    def format_search_results_for_rag(self, search_results: List[models.ScoredPoint], 
                                     max_results: int = 5) -> str:
        """Format search results from Projects for RAG system prompt.
        
        Args:
            search_results: List of ScoredPoint objects from ProjectsRag.search()
            max_results: Maximum number of results to include
            
        Returns:
            Formatted string for RAG context
        """
        if not search_results:
            return "No relevant projects found for this query."
        
        formatted_results = []
        for i, result in enumerate(search_results[:max_results], 1):
            content = result.payload.get("content", "")
            department = result.payload.get("department", "Unknown")
            category = result.payload.get("impact_category", "Unknown")
            score = result.score
            
            formatted_results.append(f"""
Project {i}: "{content}"
Department: {department}
Category: {category}
Relevance Score: {score:.3f}
""")
        
        return "\n".join(formatted_results)
    
    @require(lambda user_query: isinstance(user_query, str) and len(user_query.strip()) > 0,
             "User query must be a non-empty string")
    @require(lambda search_results: isinstance(search_results, list), "Search results must be a list")
    def create_rag_context(self, user_query: str, search_results: List[models.ScoredPoint], 
                          system_prompt: Optional[str] = None) -> str:
        """Create a complete RAG context with system prompt and formatted results.
        
        Args:
            user_query: The user's question
            search_results: Search results from ProjectsRag.search()
            system_prompt: System prompt to use (defaults to comprehensive prompt)
            
        Returns:
            Complete RAG context string
        """
        if system_prompt is None:
            system_prompt = self.PROJECTS_RAG_SYSTEM_PROMPT
        if not isinstance(system_prompt, str) or not system_prompt.strip():
            raise ValueError("System prompt must be a non-empty string")
        
        formatted_results = self.format_search_results_for_rag(search_results)
        
        context = f"""
{system_prompt}

## User Query
{user_query}

## Relevant Projects
{formatted_results}

Please answer the user's question using the provided projects and following the guidelines above.
"""
        return context
    
    @require(lambda user_query: isinstance(user_query, str) and len(user_query.strip()) > 0,
             "User query must be a non-empty string")
    @require(lambda limit: isinstance(limit, int) and limit > 0, "Limit must be a positive integer")
    def search_and_create_rag_context(self, user_query: str, limit: int = 5,
                                    score_threshold: Optional[float] = None,
                                    department: Optional[str] = None,
                                    impact_category: Optional[str] = None,
                                    system_prompt: Optional[str] = None) -> str:
        """Search for projects and create RAG context in one convenient method.
        
        Args:
            user_query: The user's question
            limit: Maximum number of search results to include
            score_threshold: Minimum similarity score threshold
            department: Optional filter to only return projects by this department
            impact_category: Optional filter to only return projects in this impact category
            system_prompt: System prompt to use (defaults to comprehensive prompt)
            
        Returns:
            Complete RAG context string
        """
        # Search for relevant projects
        search_results = self.search(
            query=user_query,
            limit=limit,
            score_threshold=score_threshold,
            department=department,
            impact_category=impact_category
        )
        
        # Create RAG context
        return self.create_rag_context(user_query, search_results, system_prompt)
    
    # ----------------------------------------------------------------------------------------
    #  Helper Methods (Private)
    # ----------------------------------------------------------------------------------------
    @require(lambda results: isinstance(results, list), "Results must be a list")
    @require(lambda search_description: isinstance(search_description, str) and len(search_description.strip()) > 0,
             "Search description must be a non-empty string")
    @require(lambda max_text_length: isinstance(max_text_length, int) and max_text_length > 0,
             "Max text length must be a positive integer")
    def display_search_results(self, results: List[models.ScoredPoint], 
                              search_description: str, 
                              max_text_length: int = 120) -> None:
        """Present search results in a beautiful, easy-to-read table format.
        
        Args:
            results: Your search results from the search() method. Each result
                contains the project text, department, impact_category, effort_size, and relevance score.
            search_description: A descriptive title for the search that will be
                displayed at the top of the table (e.g., "Analytics Projects").
            max_text_length: Maximum characters to display for each item before
                truncating with "..." (default: 120). Keeps table readable.
        """
        try:
            from rich.console import Console
            from rich.table import Table
            from rich.text import Text
            
            console = Console()
            
            # Create table
            table = Table(
                title=f"🔍 {search_description}",
                show_header=True,
                header_style="bold magenta",
                border_style="blue",
                padding=(1, 2)
            )
            
            # Add columns
            table.add_column("#", style="magenta", width=15, justify="center")
            table.add_column("Score", style="green", width=20, justify="center")
            table.add_column("Project", style="bright_white", width=60)
            table.add_column("Name", style="cyan", width=30)
            table.add_column("Department", style="bold bright_yellow", width=25)
            table.add_column("Impact Category", style="white", width=25)
            
            if not results:
                table.add_row("", "", "❌ No results found.", "", "")
                console.print(table)
                return
            
            # Add rows
            for i, result in enumerate(results, 1):
                content = result.payload.get("content", "")
                name = result.payload.get("name", "(unnamed)")
                department = result.payload.get("department", "Unknown")
                category = result.payload.get("impact_category", "Unknown")
                score = result.score
                
                # Truncate long text for readability
                display_content = (content if len(content) <= max_text_length 
                                 else content[:max_text_length-3] + "...")
                
                # Create styled text
                project_text = Text(f'"{display_content}"', style="italic")
                
                table.add_row(
                    str(i),
                    f"{score:.3f}",
                    project_text,
                    name,
                    department,
                    category
                )
            
            # Display table
            console.print(table)
            console.print(f"📊 Found {len(results)} results", style="bold green")
            
        except ImportError:
            # Fallback to simple print if rich is not available
            logger.warning("Rich library not available, falling back to simple display")
            self._display_search_results_simple(results, search_description, max_text_length)
        except Exception as e:
            logger.error(f"Failed to display search results: {str(e)}")
            # Fallback to simple display
            self._display_search_results_simple(results, search_description, max_text_length)
    
    def _display_search_results_simple(self, results: List[models.ScoredPoint], 
                                      search_description: str, 
                                      max_text_length: int) -> None:
        """Simple fallback display method when rich is not available.
        
        Args:
            results: List of ScoredPoint objects from search results.
            search_description: Description of the search to display.
            max_text_length: Maximum length for text before truncation.
        """
        print(f"\n🔍 {search_description}")
        print("=" * len(f"🔍 {search_description}"))
        
        if not results:
            print("   ❌ No results found.")
            return
        
        print(f"   📊 Found {len(results)} results")
        print()
        
        for i, result in enumerate(results, 1):
            content = result.payload.get("content", "")
            department = result.payload.get("department", "Unknown")
            category = result.payload.get("impact_category", "Unknown")
            
            # Truncate long text for readability
            display_content = (content if len(content) <= max_text_length 
                             else content[:max_text_length-3] + "...")
            
            print(f"   {i}. 📊 Score: {result.score:.3f}")
            print(f"      📝 Project: \"{display_content}\"")
            print(f"      🏢 Department: {department}")
            print(f"      🏷️  Category: {category}")
            print()
    
    def _apply_metadata_filters(self, results: List[models.ScoredPoint],
                               department_filter: Optional[str] = None,
                               impact_category_filter: Optional[str] = None) -> List[models.ScoredPoint]:
        """Apply department and/or impact category filters to search results.
        
        Args:
            results: List of scored points from vector search.
            department_filter: Optional department name to filter by.
            category_filter: Optional category name to filter by.
            
        Returns:
            Filtered list of scored points.
        """
        if not department_filter and not impact_category_filter:
            return results
        
        filtered_results = []
        
        for result in results:
            # Skip results without payload
            if not result.payload:
                continue
            
            # Apply department filter
            if department_filter:
                result_department = result.payload.get("department", "")
                if not result_department or result_department.lower() != department_filter.lower():
                    continue
            
            # Apply category filter
            if impact_category_filter:
                result_category = result.payload.get("impact_category", "")
                if not result_category or result_category.lower() != impact_category_filter.lower():
                    continue
            
            filtered_results.append(result)
        
        return filtered_results

    # ----------------------------------------------------------------------------------------
    #  LLM Response Models
    # ----------------------------------------------------------------------------------------
    class ProjectsResponse(BaseModel):
        """Structured response from LLM about projects portfolio queries."""
        
        answer: str = Field(
            ..., 
            description="A thoughtful answer to the user's question about projects, using the provided context"
        )
        key_insights: List[str] = Field(
            ..., 
            min_length=1,
            max_length=5,
            description="2-5 key insights or themes from the projects"
        )
        recommended_projects: List[str] = Field(
            default_factory=list,
            description="Specific projects most relevant to the answer (with department attribution)"
        )
        follow_up_questions: List[str] = Field(
            default_factory=list,
            description="2-3 follow-up questions to explore related topics"
        )
        
        @field_validator('answer')
        @classmethod
        def validate_answer_length(cls, v: str) -> str:
            """Ensure answer is substantial."""
            if len(v.strip()) < 50:
                raise ValueError("Answer must be at least 50 characters long")
            return v
    
    # ----------------------------------------------------------------------------------------
    #  LLM Integration Methods
    # ----------------------------------------------------------------------------------------
    @require(lambda user_query: isinstance(user_query, str) and len(user_query.strip()) > 0,
             "User query must be a non-empty string")
    @require(lambda limit: isinstance(limit, int) and limit > 0, "Limit must be a positive integer")
    def ask_llm(self, *, user_query: str, limit: int = 5, 
                score_threshold: Optional[float] = None,
                department: Optional[str] = None,
                impact_category: Optional[str] = None,
                model: str = "gpt-4o") -> "ProjectsRag.ProjectsResponse":
        """Ask AI thoughtful questions about projects and get structured, insightful answers.
        
        This method combines the power of semantic search with advanced AI reasoning
        to provide comprehensive answers grounded in your project portfolio.
        
        Args:
            user_query: Your question.
            limit: Number of relevant projects to provide as context (default: 5).
            score_threshold: Only use items above this similarity score (0.0-1.0).
            department: Focus the answer on projects from this specific department only.
            impact_category: Limit context to projects from this impact category only.
            model: OpenAI model to use.
        
        Returns:
            ProjectsResponse containing:
            - answer: Comprehensive, thoughtful response to your question
            - key_insights: 2-5 main themes or takeaways from the analysis
            - recommended_projects: Most relevant items with proper attribution
            - follow_up_questions: Suggested related questions to explore further
        """
        try:
            # Create RAG context
            rag_context = self.search_and_create_rag_context(
                user_query=user_query,
                limit=limit,
                score_threshold=score_threshold,
                department=department,
                impact_category=impact_category
            )
            
            # Create instructor-patched client
            client = instructor.from_openai(OpenAI())
            
            # Get structured response from LLM
            response = client.chat.completions.create(
                model=model,
                response_model=self.ProjectsResponse,
                messages=[
                    {"role": "user", "content": rag_context}
                ]
            )
            
            logger.info(f"LLM response generated for query: '{user_query[:50]}...'")
            return response
            
        except Exception as e:
            logger.error(f"Failed to get LLM response: {str(e)}")
            raise InvalidPointsError(
                issue=f"LLM query failed: {str(e)}",
                points_count=1
            )
    
    @require(lambda user_query: isinstance(user_query, str) and len(user_query.strip()) > 0,
             "User query must be a non-empty string")
    def ask_llm_simple(self, *, user_query: str, limit: int = 3, 
                      model: str = "gpt-4o") -> str:
        """Get a simple text response from the LLM about projects.
        
        Args:
            user_query: The user's question about projects
            limit: Maximum number of search results to include
            model: OpenAI model to use (default: gpt-4o)
            
        Returns:
            Simple text response from the LLM
        """
        try:
            # Create RAG context
            rag_context = self.search_and_create_rag_context(
                user_query=user_query,
                limit=limit
            )
            
            # Create OpenAI client
            client = OpenAI()
            
            # Get simple response from LLM
            response = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "user", "content": rag_context}
                ],
                max_tokens=500,
                temperature=0.7
            )
            
            answer = response.choices[0].message.content
            logger.info(f"Simple LLM response generated for query: '{user_query[:50]}...'")
            return answer
            
        except Exception as e:
            logger.error(f"Failed to get simple LLM response: {str(e)}")
            raise InvalidPointsError(
                issue=f"Simple LLM query failed: {str(e)}",
                points_count=1
            )
    
    def display_llm_response(self, response: "ProjectsRag.ProjectsResponse", user_query: str) -> None:
        """Display the LLM response in a formatted way using rich.
        
        Args:
            response: The structured response from the LLM
            user_query: The original user query
        """
        try:
            from rich.console import Console
            from rich.panel import Panel
            from rich.text import Text
            from rich.columns import Columns
            
            console = Console()
            
            # Display the main answer
            console.print(Panel(
                Text(response.answer, style="white"),
                title=f"🤖 LLM Answer to: '{user_query}'",
                border_style="green"
            ))
            
            # Display key insights
            insights_text = "\n".join([f"• {insight}" for insight in response.key_insights])
            console.print(Panel(
                Text(insights_text, style="cyan"),
                title="💡 Key Insights",
                border_style="blue"
            ))
            
            # Display recommended projects
            if response.recommended_projects:
                quotes_text = "\n\n".join([f"📁 {proj}" for proj in response.recommended_projects])
                console.print(Panel(
                    Text(quotes_text, style="yellow"),
                    title="📚 Recommended Projects",
                    border_style="yellow"
                ))
            
            # Display follow-up questions
            if response.follow_up_questions:
                questions_text = "\n".join([f"❓ {question}" for question in response.follow_up_questions])
                console.print(Panel(
                    Text(questions_text, style="magenta"),
                    title="🔍 Follow-up Questions",
                    border_style="magenta"
                ))
                
        except ImportError:
            # Fallback to simple print if rich is not available
            logger.warning("Rich library not available, falling back to simple display")
            self._display_llm_response_simple(response, user_query)
        except Exception as e:
            logger.error(f"Failed to display LLM response: {str(e)}")
            self._display_llm_response_simple(response, user_query)
    
    def _display_llm_response_simple(self, response: "ProjectsRag.ProjectsResponse", user_query: str) -> None:
        """Simple fallback display method when rich is not available.
        
        Args:
            response: The structured response from the LLM
            user_query: The original user query
        """
        print(f"\n🤖 LLM Answer to: '{user_query}'")
        print("=" * 60)
        print(response.answer)
        print()
        
        print("💡 Key Insights:")
        for insight in response.key_insights:
            print(f"  • {insight}")
        print()
        
        if response.recommended_projects:
            print("📚 Recommended Projects:")
            for proj in response.recommended_projects:
                print(f"  📁 {proj}")
            print()
        
        if response.follow_up_questions:
            print("🔍 Follow-up Questions:")
            for question in response.follow_up_questions:
                print(f"  ❓ {question}")
            print()

    # ----------------------------------------------------------------------------------------
    #  RAG Facade Method
    # ----------------------------------------------------------------------------------------
    @require(lambda user_query: isinstance(user_query, str) and len(user_query.strip()) > 0,
             "User query must be a non-empty string")
    @require(lambda limit: isinstance(limit, int) and limit > 0, "Limit must be a positive integer")
    def rag(self, *, user_query: str, limit: int = 5, 
            score_threshold: Optional[float] = None,
            department: Optional[str] = None,
            impact_category: Optional[str] = None,
            model: str = "gpt-4o",
            response_type: str = "structured") -> Dict[str, Any]:
        """🚀 Complete AI-powered question answering in one powerful method call.
        
        This is your one-stop solution for getting intelligent answers about projects.
        It automatically searches your project collection, finds the most relevant content,
        and generates comprehensive AI responses with full transparency into the process.
        
        Perfect for building chatbots, educational tools, or research applications where
        you need both the AI answer and access to the underlying source material.
        
        The Complete RAG Pipeline:
        1. 🔍 Semantic search finds relevant projects from your collection
        2. 📝 Context generation creates optimized prompts for the AI
        3. 🤖 AI reasoning produces thoughtful, grounded responses
        4. 📊 Full transparency with all intermediate results returned
        
        Args:
            user_query: Your question about projects. Use natural, conversational
                language like "How do projects demonstrate loyalty?" or "What can
                projects teach children about responsibility?"
            limit: Number of projects to use as context (default: 5). More context
                can improve answer quality but increases cost and response time.
            score_threshold: Minimum relevance score for projects (0.0-1.0). Higher
                values ensure only highly relevant projects are used as context.
            department: Limit context to projects from this department only. Great for
                exploring specific perspectives or philosophies.
            category: Focus on projects from this category only. Useful for domain-
                specific questions like "Ethics" or "Project Management".
            model: OpenAI model for AI responses. "gpt-4o" gives the best quality,
                "gpt-3.5-turbo" is faster and more economical.
            response_type: Format of AI response:
                - "structured": Rich AnimalWisdomResponse with insights and follow-ups
                - "simple": Plain text response for basic use cases
        
        Returns:
            Complete results dictionary containing:
            - llm_response: AI answer (structured object or simple string)
            - search_results: List of relevant projects found (with scores)
            - rag_context: Full prompt sent to AI (for debugging/transparency)
            - query_info: Metadata about the query and processing parameters
        
        Raises:
            InvalidPointsError: When any step fails (search, context generation,
                or AI response). Error messages indicate which step failed.
        
        Example:
            ```python
            # Complete RAG in one call
            result = projects.rag(
                "What do projects teach us about unconditional love?",
                limit=7,
                score_threshold=0.6,
                response_type="structured"
            )
            
            # Access the AI response
            ai_answer = result["llm_response"]
            print("AI Answer:", ai_answer.answer)
            
            # See what projects were used
            projects_used = result["search_results"]
            print(f"Based on {len(projects_used)} relevant projects")
            
            # Inspect the full context (for debugging)
            full_prompt = result["rag_context"]
            
            # Get query metadata
            info = result["query_info"]
            print(f"Model: {info['model']}, Results: {info['results_count']}")
            ```
        
        Advanced Usage:
            ```python
            # Domain-specific question
            ethics_result = projects.rag(
                user_query="How should humans treat wild projects?",
                impact_category="Ethics and Compassion",
                limit=10
            )
            
            # Author-focused inquiry
            gandhi_result = projects.rag(
                "What did Gandhi believe about projects?",
                department="Data Platform",
                response_type="simple"
            )
            ```
        
        Use Cases:
            - Educational Q&A systems about projects and nature
            - Research tools for exploring project-human relationships
            - Content generation for blogs, articles, or presentations
            - Interactive chatbots with grounded, source-backed responses
            - Philosophical exploration of project wisdom and ethics
        
        Performance Tips:
            - Start with limit=5 for good balance of quality and speed
            - Use score_threshold=0.7+ for highly focused questions
            - Choose "simple" response_type for faster, lower-cost interactions
            - Cache results for frequently asked questions
        """
        try:
            # Step 1: Perform semantic search
            search_results = self.search(
                query=user_query,
                limit=limit,
                score_threshold=score_threshold,
                department=department,
                impact_category=impact_category
            )
            
            # Step 2: Generate RAG context
            rag_context = self.create_rag_context(
                user_query=user_query,
                search_results=search_results
            )
            
            # Step 3: Get LLM response based on type
            if response_type.lower() == "structured":
                llm_response = self.ask_llm(
                    user_query=user_query,
                    limit=limit,
                    score_threshold=score_threshold,
                    department=department,
                    impact_category=impact_category,
                    model=model
                )
            elif response_type.lower() == "simple":
                llm_response = self.ask_llm_simple(
                    user_query=user_query,
                    limit=limit,
                    model=model
                )
            else:
                raise ValueError(f"Invalid response_type: {response_type}. Must be 'structured' or 'simple'")
            
            # Step 4: Prepare query info
            query_info = {
                "user_query": user_query,
                "limit": limit,
                "score_threshold": score_threshold,
                "department_filter": department,
                "impact_category_filter": impact_category,
                "model": model,
                "response_type": response_type,
                "results_count": len(search_results)
            }
            
            # Step 5: Return complete RAG result
            result = {
                "llm_response": llm_response,
                "search_results": search_results,
                "rag_context": rag_context,
                "query_info": query_info
            }
            
            logger.info(f"Complete RAG pipeline executed for query: '{user_query[:50]}...' "
                       f"with {len(search_results)} results and {response_type} response")
            
            return result
            
        except Exception as e:
            logger.error(f"RAG pipeline failed: {str(e)}")
            raise InvalidPointsError(
                issue=f"RAG pipeline failed: {str(e)}",
                points_count=1
            ) 