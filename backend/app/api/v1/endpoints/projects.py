import logging
from typing import List
from fastapi import APIRouter, Depends, HTTPException, Path, Query, status
from app.db.models import (
    Project,
    ProjectCreate,
    ProjectUpdate,
    AnalysisUpdate,
    StoredAnalysisSummary,
    SearchResponse,
)
from app.db.repository import (
    memory_repo,
    ProjectNotFoundError,
    AnalysisNotFoundError,
    DatabaseOperationError,
    DatabaseTimeoutError,
    DatabaseConnectionError,
    DatabaseConfigurationError,
)
from app.models.schemas import ShiftlyAnalysisResult
from app.core.auth import AuthenticatedUser, get_current_user
from app.core.rate_limiter import rate_limit_projects_write

logger = logging.getLogger("shiftly.api.projects")
router = APIRouter()

SAFE_ID_PATTERN = r"^[a-zA-Z0-9_-]{1,64}$"


def handle_db_exception(e: Exception, operation: str) -> None:
    """
    Standardized, safe database exception mapper.
    Translates repository errors to canonical HTTP responses without leaking
    internal details, database credentials, or stack traces.
    """
    if isinstance(e, HTTPException):
        raise e
    if isinstance(e, ProjectNotFoundError):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    if isinstance(e, AnalysisNotFoundError):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    if isinstance(e, DatabaseTimeoutError):
        logger.error("Database timeout during %s: %s", operation, e)
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail="Database operation timed out. Please try again.",
        )
    if isinstance(e, (DatabaseConnectionError, DatabaseConfigurationError)):
        logger.error("Database service unavailable during %s: %s", operation, e)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database service is temporarily unavailable. Please try again.",
        )
    if isinstance(e, DatabaseOperationError):
        logger.error("Database operation error during %s: %s", operation, e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Database error occurred during operation.",
        )

    logger.exception("Unexpected error during %s: %s", operation, e)
    raise HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail="An unexpected database error occurred.",
    )


from app.core.plans import resolve_entitlement

@router.post(
    "/projects",
    response_model=Project,
    status_code=status.HTTP_201_CREATED,
    summary="Create Project",
    description="Creates a new project container in Project Memory.",
)
def create_project(
    payload: ProjectCreate,
    current_user: AuthenticatedUser = Depends(get_current_user),
    _rate_limit: bool = Depends(rate_limit_projects_write),
) -> Project:
    clean_name = payload.name.strip()
    if not clean_name:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Project name cannot be empty or only whitespace.",
        )

    # Enforce plan project limit
    entitlement = resolve_entitlement(current_user)
    limits = entitlement.limits
    current_count = memory_repo.count_user_projects(user_id=current_user.id, user_token=current_user.token)
    if current_count >= limits.max_projects:
        logger.warning(
            "project_creation_rejected_limit_reached user_id=%s count=%d limit=%d",
            current_user.id,
            current_count,
            limits.max_projects,
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Project limit reached. Your plan allows up to {limits.max_projects} projects.",
        )

    logger.info("project_save_started user_id=%s", current_user.id)
    try:
        project = memory_repo.create_project(
            name=clean_name,
            description=payload.description,
            user_id=current_user.id,
            user_token=current_user.token,
        )
        logger.info("project_save_completed project_id=%s user_id=%s", project.id, current_user.id)
        return project
    except Exception as e:
        handle_db_exception(e, "create_project")


@router.get(
    "/projects",
    response_model=List[Project],
    summary="List Projects",
    description="Retrieves all projects stored in Project Memory ordered by creation date.",
)
def list_projects(
    current_user: AuthenticatedUser = Depends(get_current_user),
) -> List[Project]:
    try:
        return memory_repo.list_projects(user_id=current_user.id, user_token=current_user.token)
    except Exception as e:
        handle_db_exception(e, "list_projects")


@router.get(
    "/projects/{project_id}",
    response_model=Project,
    summary="Get Project Details",
    description="Retrieves a specific project by ID.",
)
def get_project(
    project_id: str = Path(..., pattern=SAFE_ID_PATTERN, description="Safe alphanumeric project identifier"),
    current_user: AuthenticatedUser = Depends(get_current_user),
) -> Project:
    try:
        project = memory_repo.get_project(project_id, user_id=current_user.id, user_token=current_user.token)
        if not project:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Project with ID '{project_id}' was not found.",
            )
        return project
    except Exception as e:
        handle_db_exception(e, "get_project")


@router.patch(
    "/projects/{project_id}",
    response_model=Project,
    summary="Update Project Name",
    description="Renames an existing project without altering its ID or attached analyses.",
)
def update_project(
    project_id: str = Path(..., pattern=SAFE_ID_PATTERN, description="Safe alphanumeric project identifier"),
    payload: ProjectUpdate = ...,
    current_user: AuthenticatedUser = Depends(get_current_user),
    _rate_limit: bool = Depends(rate_limit_projects_write),
) -> Project:
    logger.info("project_rename_started project_id=%s user_id=%s", project_id, current_user.id)
    try:
        updated = memory_repo.update_project_name(
            project_id=project_id,
            name=payload.name,
            user_id=current_user.id,
            user_token=current_user.token,
        )
        logger.info("project_rename_completed project_id=%s user_id=%s", project_id, current_user.id)
        return updated
    except ValueError as ve:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(ve),
        )
    except Exception as e:
        handle_db_exception(e, "update_project")


@router.delete(
    "/projects/{project_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete Project",
    description="Deletes a project and cascades deletion to all associated analyses.",
)
def delete_project(
    project_id: str = Path(..., pattern=SAFE_ID_PATTERN, description="Safe alphanumeric project identifier"),
    current_user: AuthenticatedUser = Depends(get_current_user),
):
    logger.info("project_delete_started project_id=%s user_id=%s", project_id, current_user.id)
    try:
        memory_repo.delete_project(project_id, user_id=current_user.id, user_token=current_user.token)
        logger.info("project_delete_completed project_id=%s user_id=%s", project_id, current_user.id)
        return None
    except Exception as e:
        handle_db_exception(e, "delete_project")


@router.post(
    "/projects/{project_id}/analyses",
    response_model=StoredAnalysisSummary,
    status_code=status.HTTP_201_CREATED,
    summary="Save Analysis to Project",
    description="Persists extracted intelligence into a project without storing raw conversations.",
)
def save_analysis(
    project_id: str = Path(..., pattern=SAFE_ID_PATTERN, description="Safe alphanumeric project identifier"),
    payload: ShiftlyAnalysisResult = ...,
    current_user: AuthenticatedUser = Depends(get_current_user),
    _rate_limit: bool = Depends(rate_limit_projects_write),
) -> StoredAnalysisSummary:
    logger.info("analysis_save_started project_id=%s user_id=%s", project_id, current_user.id)
    try:
        saved_summary = memory_repo.save_analysis(
            project_id,
            payload,
            user_id=current_user.id,
            user_token=current_user.token,
        )
        logger.info(
            "analysis_save_completed analysis_id=%s project_id=%s user_id=%s",
            saved_summary.id,
            project_id,
            current_user.id,
        )
        return saved_summary
    except Exception as e:
        handle_db_exception(e, "save_analysis")


@router.get(
    "/projects/{project_id}/analyses",
    response_model=List[StoredAnalysisSummary],
    summary="List Project Analyses",
    description="Returns chronological analysis history for a project.",
)
def list_project_analyses(
    project_id: str = Path(..., pattern=SAFE_ID_PATTERN, description="Safe alphanumeric project identifier"),
    current_user: AuthenticatedUser = Depends(get_current_user),
) -> List[StoredAnalysisSummary]:
    try:
        return memory_repo.list_project_analyses(project_id, user_id=current_user.id, user_token=current_user.token)
    except Exception as e:
        handle_db_exception(e, "list_project_analyses")


@router.get(
    "/projects/{project_id}/analyses/{analysis_id}",
    response_model=ShiftlyAnalysisResult,
    summary="Get Complete Stored Analysis",
    description="Re-hydrates the complete extracted intelligence result with all views and verified source references.",
)
def get_analysis(
    project_id: str = Path(..., pattern=SAFE_ID_PATTERN, description="Safe alphanumeric project identifier"),
    analysis_id: str = Path(..., pattern=SAFE_ID_PATTERN, description="Safe alphanumeric analysis identifier"),
    current_user: AuthenticatedUser = Depends(get_current_user),
) -> ShiftlyAnalysisResult:
    try:
        result = memory_repo.get_analysis(project_id, analysis_id, user_id=current_user.id, user_token=current_user.token)
        if not result:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Analysis '{analysis_id}' not found in project '{project_id}'.",
            )
        return result
    except Exception as e:
        handle_db_exception(e, "get_analysis")


@router.get(
    "/projects/{project_id}/intelligence",
    response_model=ShiftlyAnalysisResult,
    summary="Get Aggregated Project Intelligence",
    description="Returns the accumulated, deduplicated intelligence for all analyses in a project.",
)
def get_project_intelligence(
    project_id: str = Path(..., pattern=SAFE_ID_PATTERN, description="Safe alphanumeric project identifier"),
    current_user: AuthenticatedUser = Depends(get_current_user),
) -> ShiftlyAnalysisResult:
    try:
        return memory_repo.get_project_aggregated_intelligence(
            project_id, user_id=current_user.id, user_token=current_user.token
        )
    except Exception as e:
        handle_db_exception(e, "get_project_intelligence")


@router.patch(
    "/projects/{project_id}/analyses/{analysis_id}",
    response_model=StoredAnalysisSummary,
    summary="Update Analysis Title",
    description="Renames an existing analysis title without altering its intelligence or source evidence.",
)
def update_analysis(
    project_id: str = Path(..., pattern=SAFE_ID_PATTERN, description="Safe alphanumeric project identifier"),
    analysis_id: str = Path(..., pattern=SAFE_ID_PATTERN, description="Safe alphanumeric analysis identifier"),
    payload: AnalysisUpdate = ...,
    current_user: AuthenticatedUser = Depends(get_current_user),
    _rate_limit: bool = Depends(rate_limit_projects_write),
) -> StoredAnalysisSummary:
    logger.info("analysis_rename_started project_id=%s analysis_id=%s user_id=%s", project_id, analysis_id, current_user.id)
    try:
        updated = memory_repo.update_analysis_title(
            project_id=project_id,
            analysis_id=analysis_id,
            title=payload.title,
            user_id=current_user.id,
            user_token=current_user.token,
        )
        logger.info("analysis_rename_completed project_id=%s analysis_id=%s user_id=%s", project_id, analysis_id, current_user.id)
        return updated
    except ValueError as ve:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(ve),
        )
    except Exception as e:
        handle_db_exception(e, "update_analysis")


@router.delete(
    "/projects/{project_id}/analyses/{analysis_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete Analysis",
    description="Deletes a specific analysis and cascades deletion to all child intelligence items.",
)
def delete_analysis(
    project_id: str = Path(..., pattern=SAFE_ID_PATTERN, description="Safe alphanumeric project identifier"),
    analysis_id: str = Path(..., pattern=SAFE_ID_PATTERN, description="Safe alphanumeric analysis identifier"),
    current_user: AuthenticatedUser = Depends(get_current_user),
):
    logger.info("analysis_delete_started analysis_id=%s project_id=%s user_id=%s", analysis_id, project_id, current_user.id)
    try:
        memory_repo.delete_analysis(project_id, analysis_id, user_id=current_user.id, user_token=current_user.token)
        logger.info("analysis_delete_completed analysis_id=%s project_id=%s user_id=%s", analysis_id, project_id, current_user.id)
        return None
    except Exception as e:
        handle_db_exception(e, "delete_analysis")


@router.get(
    "/projects/{project_id}/search",
    response_model=SearchResponse,
    summary="Search Project Memory",
    description="Performs deterministic text search across stored extracted key points, actions, decisions, and dates.",
)
def search_project_memory(
    project_id: str = Path(..., pattern=SAFE_ID_PATTERN, description="Safe alphanumeric project identifier"),
    q: str = Query(..., min_length=1, max_length=200, description="Text query to search within stored intelligence"),
    current_user: AuthenticatedUser = Depends(get_current_user),
) -> SearchResponse:
    clean_q = q.strip()
    if not clean_q:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Search query cannot be empty or whitespace only.",
        )
    try:
        project = memory_repo.get_project(project_id, user_id=current_user.id, user_token=current_user.token)
        if not project:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Project '{project_id}' not found.",
            )
        results = memory_repo.search_project_memory(project_id, clean_q, user_id=current_user.id, user_token=current_user.token)
        return SearchResponse(
            query=clean_q,
            total_results=len(results),
            results=results,
        )
    except Exception as e:
        handle_db_exception(e, "search_project_memory")
