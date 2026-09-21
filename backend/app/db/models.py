import uuid
from typing import Optional, List, Literal
from pydantic import BaseModel, Field, field_validator
from app.models.schemas import SourceReference, ShiftlyAnalysisResult


class ProjectCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=150, description="Name of the project")
    description: Optional[str] = Field(default=None, max_length=1000, description="Optional project description")


class ProjectUpdate(BaseModel):
    name: str = Field(..., min_length=1, max_length=150, description="Updated name of the project")

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        trimmed = v.strip()
        if not trimmed:
            raise ValueError("Project name cannot be empty or whitespace only.")
        if any(ord(c) < 32 for c in trimmed):
            raise ValueError("Project name cannot contain invalid control characters.")
        return trimmed


class AnalysisUpdate(BaseModel):
    title: str = Field(..., min_length=1, max_length=200, description="Updated title of the analysis")

    @field_validator("title")
    @classmethod
    def validate_title(cls, v: str) -> str:
        trimmed = v.strip()
        if not trimmed:
            raise ValueError("Analysis title cannot be empty or whitespace only.")
        if any(ord(c) < 32 for c in trimmed):
            raise ValueError("Analysis title cannot contain invalid control characters.")
        return trimmed


class Project(BaseModel):

    id: str
    name: str
    description: Optional[str] = None
    created_at: str
    updated_at: str
    analyses_count: int = 0
    user_id: Optional[str] = None



class StoredAnalysisSummary(BaseModel):
    id: str
    project_id: str
    title: str
    source_type: Optional[str] = None
    source_name: Optional[str] = None
    summary: str
    created_at: str
    key_points_count: int = 0
    actions_count: int = 0
    decisions_count: int = 0
    important_dates_count: int = 0
    pending_decisions_count: int = 0


class SearchResultItem(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    analysis_id: str
    analysis_title: str
    item_type: Literal["Key Point", "Action", "Decision", "Date", "Summary", "Pending Decision"]
    content: str
    details: Optional[str] = None
    source_reference: Optional[SourceReference] = None
    created_at: str


class SearchResponse(BaseModel):
    query: str
    total_results: int
    results: List[SearchResultItem]
