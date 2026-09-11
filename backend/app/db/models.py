import uuid
from typing import Optional, List, Literal
from pydantic import BaseModel, Field, field_validator
from app.models.schemas import SourceReference, ShiftlyAnalysisResult


class ProjectCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=150, description="Name of the project")
    description: Optional[str] = Field(default=None, max_length=1000, description="Optional project description")


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


class SearchResultItem(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    analysis_id: str
    analysis_title: str
    item_type: Literal["Key Point", "Action", "Decision", "Date", "Summary"]
    content: str
    details: Optional[str] = None
    source_reference: Optional[SourceReference] = None
    created_at: str


class SearchResponse(BaseModel):
    query: str
    total_results: int
    results: List[SearchResultItem]
