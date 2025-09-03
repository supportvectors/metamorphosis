# =============================================================================
#  Filename: utilities.py
#
#  Short Description: Common utility functions used across the metamorphosis project.
#
#  Creation date: 2025-01-15
#  Author: Asif Qamar
# =============================================================================

"""Common utility functions for the metamorphosis project.

This module provides reusable utility functions that are used across multiple
components of the metamorphosis system. All utilities follow Design-by-Contract
principles with proper validation and error handling.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Annotated

from pydantic import Field, validate_call
from loguru import logger

from metamorphosis.exceptions import FileOperationError, ConfigurationError


@validate_call
def read_text_file(
    file_path: Annotated[Path | str, Field(description="Path to the text file to read")]
) -> str:
    """Read a UTF-8 text file with comprehensive error handling.

    This utility function provides robust file reading with proper error handling
    and validation. It's designed to be reused across the project for consistent
    file operations.

    Args:
        file_path: Path to the text file to read (Path object or string).

    Returns:
        str: Content of the file, stripped of leading/trailing whitespace.

    Raises:
        FileOperationError: If file not found, not accessible, or empty.
    """
    # Convert string to Path if necessary
    if isinstance(file_path, str):
        file_path = Path(file_path)
    
    logger.debug("Reading text file: {}", file_path)
    
    # Precondition validation via pydantic is already done by @validate_call
    
    if not file_path.exists():
        raise FileOperationError(
            f"File not found: {file_path}",
            file_path=str(file_path),
            operation_type="read",
            operation="file_existence_check",
            error_code="FILE_NOT_FOUND"
        )
    
    if not file_path.is_file():
        raise FileOperationError(
            f"Path is not a file: {file_path}",
            file_path=str(file_path),
            operation_type="read",
            operation="file_type_check",
            error_code="NOT_A_FILE"
        )
    
    try:
        content = file_path.read_text(encoding="utf-8").strip()
    except (OSError, UnicodeDecodeError) as e:
        raise FileOperationError(
            f"Failed to read file: {file_path}",
            file_path=str(file_path),
            operation_type="read",
            operation="file_content_read",
            error_code="READ_FAILED",
            original_error=e
        ) from e
    
    if not content:
        raise FileOperationError(
            f"File is empty: {file_path}",
            file_path=str(file_path),
            operation_type="read",
            operation="content_validation",
            error_code="EMPTY_FILE"
        )
    
    # Postcondition (O(1)): ensure we return non-empty string
    if not isinstance(content, str) or not content:
        raise FileOperationError(
            "Postcondition failed: content must be non-empty string",
            file_path=str(file_path),
            operation_type="read",
            operation="postcondition_check",
            error_code="POSTCONDITION_FAILED"
        )
    
    logger.debug("Successfully read file: {} ({} chars)", file_path, len(content))
    return content


@validate_call
def get_project_root(
    env_var_name: Annotated[str, Field(min_length=1)] = "PROJECT_ROOT_DIR",
    fallback_levels: Annotated[int, Field(ge=1, le=10)] = 3
) -> Path:
    """Get project root directory from environment variable or path resolution.

    This utility provides a consistent way to locate the project root directory
    across different modules, supporting both environment variable configuration
    and automatic path resolution.

    Args:
        env_var_name: Name of environment variable containing project root path.
        fallback_levels: Number of parent directories to traverse for fallback.

    Returns:
        Path: Absolute path to the project root directory.

    Raises:
        ConfigurationError: If project root cannot be determined.
    """
    logger.debug("Resolving project root (env_var={}, fallback_levels={})", 
                env_var_name, fallback_levels)
    
    # Try environment variable first
    project_root_str = os.getenv(env_var_name)
    if project_root_str:
        project_root = Path(project_root_str).resolve()
        if project_root.exists() and project_root.is_dir():
            logger.debug("Using project root from {}: {}", env_var_name, project_root)
            return project_root
        else:
            raise ConfigurationError(
                f"Project root from {env_var_name} does not exist or is not a directory",
                context={"env_var": env_var_name, "path": project_root_str},
                operation="project_root_resolution",
                error_code="INVALID_PROJECT_ROOT"
            )
    
    # Fallback to path resolution
    try:
        # Get the current file's directory and traverse up
        current_file = Path(__file__).resolve()
        project_root = current_file.parents[fallback_levels - 1]
        
        # Postcondition (O(1)): ensure we found a valid directory
        if not project_root.exists() or not project_root.is_dir():
            raise ConfigurationError(
                f"Fallback project root resolution failed: {project_root}",
                context={"fallback_levels": fallback_levels, "current_file": str(current_file)},
                operation="project_root_fallback",
                error_code="FALLBACK_FAILED"
            )
        
        logger.debug("Using fallback project root: {}", project_root)
        return project_root
        
    except (IndexError, OSError) as e:
        raise ConfigurationError(
            f"Could not determine project root directory",
            context={"env_var": env_var_name, "fallback_levels": fallback_levels},
            operation="project_root_resolution",
            error_code="ROOT_RESOLUTION_FAILED",
            original_error=e
        ) from e


@validate_call
def ensure_directory_exists(
    directory_path: Annotated[Path | str, Field(description="Directory path to create if needed")]
) -> Path:
    """Ensure a directory exists, creating it if necessary.

    Args:
        directory_path: Path to the directory (Path object or string).

    Returns:
        Path: Absolute path to the directory.

    Raises:
        FileOperationError: If directory cannot be created.
    """
    if isinstance(directory_path, str):
        directory_path = Path(directory_path)
    
    directory_path = directory_path.resolve()
    
    if directory_path.exists():
        if not directory_path.is_dir():
            raise FileOperationError(
                f"Path exists but is not a directory: {directory_path}",
                file_path=str(directory_path),
                operation_type="create",
                operation="directory_validation",
                error_code="NOT_A_DIRECTORY"
            )
        return directory_path
    
    try:
        directory_path.mkdir(parents=True, exist_ok=True)
        logger.debug("Created directory: {}", directory_path)
        return directory_path
    except OSError as e:
        raise FileOperationError(
            f"Failed to create directory: {directory_path}",
            file_path=str(directory_path),
            operation_type="create",
            operation="directory_creation",
            error_code="CREATE_FAILED",
            original_error=e
        ) from e
