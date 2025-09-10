# =============================================================================
#  Filename: project_data_models.py
#
#  Short Description: Pydantic data models for project portfolio corpus.
#
#  Creation date: 2025-01-06
#  Author: Asif Qamar
# =============================================================================

from pathlib import Path
from typing import List, Optional, Dict, Any, Literal
from pydantic import BaseModel, Field, ConfigDict, field_validator


#============================================================================================
#  Pydantic Model: Project
#============================================================================================
EffortSizeLiteral = Literal["Small", "Medium", "Large", "X-large"]
ImpactCategoryLiteral = Literal[
    "Low Impact",
    "Medium Impact",
    "High Impact",
    "Mission Critical",
]


class Project(BaseModel):
    """Represents a single project with metadata.
    
    This model captures the structure of each line in a JSONL file,
    containing the project text/description, department attribution,
    impact category, and effort size.
    
    Attributes:
        text: The project text or description
        department: Department responsible for or owning the project
        impact_category: Impact categorization for the project
        effort_size: Effort sizing for the project
    """
    model_config = ConfigDict(
        str_strip_whitespace=True,
        validate_assignment=True,
        frozen=True,
        extra="forbid"
    )
    
    text: str = Field(
        ..., 
        min_length=1, 
        description="The project text content"
    )
    department: str = Field(
        ..., 
        min_length=1, 
        description="The department responsible for the project"
    )
    impact_category: ImpactCategoryLiteral = Field(
        ..., description="Impact category for the project"
    )
    effort_size: EffortSizeLiteral = Field(
        ..., description="Effort size for the project"
    )
    
    @field_validator('text', 'department', 'impact_category', 'effort_size')
    @classmethod
    def validate_non_empty_strings(cls, v: str) -> str:
        """Ensure all string fields are non-empty after stripping."""
        if not v or not v.strip():
            raise ValueError("Field cannot be empty or whitespace only")
        return v.strip()
    
    def to_payload(self) -> Dict[str, Any]:
        """Convert the project to a payload dictionary for vector storage.
        
        Returns:
            Dictionary suitable for Qdrant point payload.
        """
        return {
            "content": self.text,
            "content_type": "project",
            "department": self.department,
            "impact_category": self.impact_category,
            "effort_size": self.effort_size,
        }


#============================================================================================
#  Pydantic Model: ProjectPortfolio
#============================================================================================
class ProjectPortfolio(BaseModel):
    """Collection of projects loaded from the corpus.
    
    This model represents the complete collection of projects,
    providing validation and convenient access methods for the data.
    
    Attributes:
        projects: List of Project instances
        source_file: Optional path to the source JSONL file
    """
    model_config = ConfigDict(
        validate_assignment=True,
        arbitrary_types_allowed=True
    )
    
    projects: List[Project] = Field(
        ..., 
        min_length=1,
        description="Collection of projects"
    )
    source_file: Optional[Path] = Field(
        default=None,
        description="Path to the source JSONL file"
    )
    
    @field_validator('projects')
    @classmethod
    def validate_projects_not_empty(cls, v: List[Project]) -> List[Project]:
        """Ensure projects list is not empty."""
        if not v:
            raise ValueError("Projects collection cannot be empty")
        return v
    
    def __len__(self) -> int:
        """Return the number of projects in the collection."""
        return len(self.projects)
    
    def get_impact_categories(self) -> List[str]:
        """Get unique impact categories from all projects.
        
        Returns:
            Sorted list of unique category names.
        """
        impacts = {project.impact_category for project in self.projects}
        return sorted(impacts)
    
    def get_departments(self) -> List[str]:
        """Get unique departments from all projects.
        
        Returns:
            Sorted list of unique department names.
        """
        departments = {project.department for project in self.projects}
        return sorted(departments)
    
    def filter_by_impact_category(self, *, impact_category: str) -> List[Project]:
        """Filter projects by impact category.
        
        Args:
            impact_category: Impact category name to filter by.
            
        Returns:
            List of projects matching the impact category.
        """
        return [project for project in self.projects if project.impact_category == impact_category]
    
    def filter_by_department(self, *, department: str) -> List[Project]:
        """Filter projects by department.
        
        Args:
            department: Department name to filter by.
            
        Returns:
            List of projects by the specified department.
        """
        return [project for project in self.projects if project.department == department]


#============================================================================================ 