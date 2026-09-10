import logging
from fastapi import APIRouter, HTTPException, status
from app.models.schemas import AnalyzeRequest, ShiftlyAnalysisResult
from app.services.gemini_service import analyze_communication

logger = logging.getLogger("shiftly.api.analyze")
router = APIRouter()


@router.post(
    "/analyze",
    response_model=ShiftlyAnalysisResult,
    summary="Analyze Unstructured Communication",
    description="Extracts structured key points, actions, decisions, and dates from raw project communication using Gemini.",
)
def analyze(payload: AnalyzeRequest) -> ShiftlyAnalysisResult:
    # 1. Validation: Empty or blank text
    if not payload.text or not payload.text.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The communication text cannot be empty. Please paste or provide a conversation to analyze.",
        )

    # 2. Execution through Gemini extraction & chunking pipeline
    try:
        result = analyze_communication(payload.text)
        return result
    except ValueError as ve:
        err_str = str(ve)
        if "GEMINI_API_KEY" in err_str:
            logger.warning("Attempted extraction without configured GEMINI_API_KEY")
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Gemini API key is not configured on the backend. Please add GEMINI_API_KEY in backend/.env to enable live AI extraction.",
            )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=err_str,
        )
    except TimeoutError as te:
        logger.error(f"Timeout while calling Gemini: {te}")
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail="The extraction request timed out. Please try again or analyze a shorter segment.",
        )
    except RuntimeError as re:
        logger.error(f"Runtime error in extraction: {re}")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"AI extraction provider error: {str(re)}",
        )
    except Exception as e:
        logger.exception("Unexpected error during communication analysis")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An unexpected error occurred while analyzing the communication: {str(e)}",
        )
