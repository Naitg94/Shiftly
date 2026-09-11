import logging
from typing import List
from fastapi import APIRouter, HTTPException, Query, status
from app.db.models import Project, ProjectCreate, StoredAnalysisSummary, SearchResponse
from app.db.repository import (
    memory_repo,
    ProjectNotFoundError,
    AnalysisNotFoundError,
    DatabaseOperationError,
    DatabaseConfigurationError,
)
from app.models.schemas import ShiftlyAnalysisResult

logger = logging.getLogger("shiftly.api.projects")
router = APIRouter()


@router.post(
    "/projects",
    response_model=Project,
    status_code=status.HTTP_201_CREATED,
    summary="Create Project",
    description="Creates a new project container in Project Memory.",
)
def create_project(payload: ProjectCreate) -> Project:
    clean_name = payload.name.strip()
    if not clean_name:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Project name cannot be empty or only whitespace.",
        )
    try:
        project = memory_repo.create_project(name=clean_name, description=payload.description)
        return project
    except DatabaseConfigurationError as dce:
        logger.error(f"Database configuration missing: {dce}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(dce),
        )
    except DatabaseOperationError as doe:
        logger.error(f"Failed to create project: {doe}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Database error creating project: {str(doe)}",
        )


@router.get(
    "/projects",
    response_model=List[Project],
    summary="List Projects",
    description="Retrieves all projects stored in Project Memory ordered by creation date.",
)
def list_projects() -> List[Project]:
    try:
        return memory_repo.list_projects()
    except DatabaseConfigurationError as dce:
        logger.error(f"Database configuration missing: {dce}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(dce),
        )
    except Exception as e:
        logger.error(f"Failed to list projects: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Database error retrieving projects: {str(e)}",
        )


@router.get(
    "/projects/{project_id}",
    response_model=Project,
    summary="Get Project Details",
    description="Retrieves a specific project by ID.",
)
def get_project(project_id: str) -> Project:
    try:
        project = memory_repo.get_project(project_id)
        if not project:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Project with ID '{project_id}' was not found.",
            )
        return project
    except HTTPException:
        raise
    except DatabaseConfigurationError as dce:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(dce),
        )
    except Exception as e:
        logger.error(f"Failed to get project: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Database error retrieving project: {str(e)}",
        )


@router.delete(
    "/projects/{project_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete Project",
    description="Deletes a project and cascades deletion to all associated analyses.",
)
def delete_project(project_id: str):
    try:
        memory_repo.delete_project(project_id)
        return None
    except ProjectNotFoundError as pne:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(pne),
        )
    except DatabaseConfigurationError as dce:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(dce),
        )
    except Exception as e:
        logger.error(f"Failed to delete project: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Database error deleting project: {str(e)}",
        )


@router.post(
    "/projects/{project_id}/analyses",
    response_model=StoredAnalysisSummary,
    status_code=status.HTTP_201_CREATED,
    summary="Save Analysis to Project",
    description="Persists extracted intelligence (key points, actions, decisions, dates, summary) into a project without storing raw conversations.",
)
def save_analysis(project_id: str, payload: ShiftlyAnalysisResult) -> StoredAnalysisSummary:
    try:
        saved_summary = memory_repo.save_analysis(project_id, payload)
        return saved_summary
    except DatabaseConfigurationError as dce:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(dce),
        )
    except ProjectNotFoundError as pne:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(pne),
        )
    except DatabaseOperationError as doe:
        logger.error(f"Database failure while saving analysis: {doe}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to persist analysis to project memory: {str(doe)}",
        )
    except Exception as e:
        logger.exception(f"Unexpected error saving analysis: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Unexpected database error: {str(e)}",
        )


@router.get(
    "/projects/{project_id}/analyses",
    response_model=List[StoredAnalysisSummary],
    summary="List Project Analyses",
    description="Returns chronological analysis history for a project.",
)
def list_project_analyses(project_id: str) -> List[StoredAnalysisSummary]:
    try:
        return memory_repo.list_project_analyses(project_id)
    except DatabaseConfigurationError as dce:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(dce),
        )
    except ProjectNotFoundError as pne:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(pne),
        )
    except Exception as e:
        logger.error(f"Failed to list analyses: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Database error retrieving analyses: {str(e)}",
        )


@router.get(
    "/projects/{project_id}/analyses/{analysis_id}",
    response_model=ShiftlyAnalysisResult,
    summary="Get Complete Stored Analysis",
    description="Re-hydrates the complete extracted intelligence result with all views and verified source references.",
)
def get_analysis(project_id: str, analysis_id: str) -> ShiftlyAnalysisResult:
    try:
        result = memory_repo.get_analysis(project_id, analysis_id)
        if not result:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Analysis '{analysis_id}' not found in project '{project_id}'.",
            )
        return result
    except HTTPException:
        raise
    except DatabaseConfigurationError as dce:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(dce),
        )
    except Exception as e:
        logger.error(f"Failed to get analysis: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Database error: {str(e)}",
        )


@router.get(
    "/projects/{project_id}/search",
    response_model=SearchResponse,
    summary="Search Project Memory",
    description="Performs deterministic text search across stored extracted key points, actions, decisions, and dates.",
)
def search_project_memory(
    project_id: str,
    q: str = Query(..., min_length=1, description="Text query to search within stored intelligence"),
) -> SearchResponse:
    try:
        project = memory_repo.get_project(project_id)
        if not project:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Project '{project_id}' not found.",
            )
        results = memory_repo.search_project_memory(project_id, q)
        return SearchResponse(
            query=q,
            total_results=len(results),
            results=results,
        )
    except HTTPException:
        raise
    except DatabaseConfigurationError as dce:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(dce),
        )
    except Exception as e:
        logger.error(f"Search failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Database search error: {str(e)}",
        )
