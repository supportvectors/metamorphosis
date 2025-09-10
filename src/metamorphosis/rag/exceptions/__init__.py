# =============================================================================
#  Filename: __init__.py
#
#  Short Description: Exceptions package for metamorphosis.rag.
#
#  Creation date: 2025-01-06
#  Author: Asif Qamar
# =============================================================================

from .exceptions import (
    VectorDatabaseError,
    VectorDatabasePathNotFoundError,
    CollectionAlreadyExistsError,
    CollectionNotFoundError,
    InvalidCollectionParametersError,
    InvalidVectorSizeError,
    InvalidDistanceMetricError,
    InvalidPointsError,
    CollectionParameterMismatchError,
)

__all__ = [
    "VectorDatabaseError",
    "VectorDatabasePathNotFoundError",
    "CollectionAlreadyExistsError",
    "CollectionNotFoundError",
    "InvalidCollectionParametersError",
    "InvalidVectorSizeError",
    "InvalidDistanceMetricError",
    "InvalidPointsError",
    "CollectionParameterMismatchError",
] 