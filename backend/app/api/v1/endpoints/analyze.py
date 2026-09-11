import time
import logging
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, status
from app.models.schemas import AnalyzeRequest, ShiftlyAnalysisResult
from app.services.gemini_service import analyze_communication
from app.services.file_processing_service import (
    process_uploaded_file,
    MAX_FILE_SIZE_BYTES,
    UnsupportedFileTypeError,
    FileOversizedError,
    EmptyFileError,
    NoSelectableTextPDFError,
    FileProcessingError,
)
from app.core.auth import AuthenticatedUser, get_current_user
from app.core.rate_limiter import rate_limit_analyze

logger = logging.getLogger("shiftly.api.analyze")
router = APIRouter()


@router.post(
    "/analyze",
    response_model=ShiftlyAnalysisResult,
    summary="Analyze Unstructured Communication (Pasted Text)",
    description="Extracts structured key points, actions, decisions, and dates from raw project communication using Gemini.",
)
def analyze(
    payload: AnalyzeRequest,
    current_user: AuthenticatedUser = Depends(get_current_user),
    _rate_limit: bool = Depends(rate_limit_analyze),
) -> ShiftlyAnalysisResult:
    # 1. Validation: Empty or blank text
    if not payload.text or not payload.text.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The communication text cannot be empty. Please paste or provide a conversation to analyze.",
        )

    start_t = time.perf_counter()
    logger.info("analysis_started type=text chars=%d user_id=%s", len(payload.text), current_user.id)

    # 2. Execution through Gemini extraction & chunking pipeline
    try:
        result = analyze_communication(payload.text)
        duration_ms = (time.perf_counter() - start_t) * 1000.0
        logger.info(
            "analysis_completed type=text duration_ms=%.2f key_points=%d actions=%d decisions=%d dates=%d user_id=%s",
            duration_ms,
            len(result.keyPoints),
            len(result.actions),
            len(result.decisions),
            len(result.importantDates),
            current_user.id,
        )
        return result
    except ValueError as ve:
        duration_ms = (time.perf_counter() - start_t) * 1000.0
        logger.error("analysis_failed type=text duration_ms=%.2f error=%s user_id=%s", duration_ms, ve, current_user.id)
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
        duration_ms = (time.perf_counter() - start_t) * 1000.0
        logger.error("analysis_failed type=text timeout duration_ms=%.2f user_id=%s: %s", duration_ms, current_user.id, te)
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail="The extraction request timed out. Please try again or analyze a shorter segment.",
        )
    except RuntimeError as re:
        duration_ms = (time.perf_counter() - start_t) * 1000.0
        logger.error("analysis_failed type=text runtime_error duration_ms=%.2f user_id=%s: %s", duration_ms, current_user.id, re)
        err_msg = str(re)
        if "quota" in err_msg.lower() or "rate limit" in err_msg.lower():
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=err_msg,
            )
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"AI extraction provider error: {err_msg}",
        )
    except Exception as e:
        duration_ms = (time.perf_counter() - start_t) * 1000.0
        logger.exception("Unexpected error during communication analysis (duration_ms=%.2f, user_id=%s)", duration_ms, current_user.id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred while analyzing the communication.",
        )


@router.post(
    "/analyze/file",
    response_model=ShiftlyAnalysisResult,
    summary="Analyze Communication File (TXT, PDF, DOCX, Chat Export)",
    description="Extracts text and source locations from an uploaded document, then processes it through the Gemini extraction pipeline.",
)
async def analyze_file(
    file: UploadFile = File(...),
    current_user: AuthenticatedUser = Depends(get_current_user),
    _rate_limit: bool = Depends(rate_limit_analyze),
) -> ShiftlyAnalysisResult:
    # 1. Validate file presence
    if not file or not file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No file was uploaded. Please select a valid document (TXT, PDF, DOCX, or Chat Export).",
        )

    start_t = time.perf_counter()
    logger.info("analysis_started type=file filename=%s user_id=%s", file.filename, current_user.id)

    # 2. Read file content safely in chunks with strict size enforcement
    try:
        chunk_size = 1024 * 1024  # 1MB
        chunks = []
        total_bytes = 0
        while True:
            chunk = await file.read(chunk_size)
            if not chunk:
                break
            total_bytes += len(chunk)
            if total_bytes > MAX_FILE_SIZE_BYTES:
                raise HTTPException(
                    status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                    detail=f"Uploaded file exceeds maximum allowed size of {MAX_FILE_SIZE_BYTES // (1024 * 1024)} MB.",
                )
            chunks.append(chunk)
        content = b"".join(chunks)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to read uploaded file: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to read uploaded file: {str(e)}",
        )
    finally:
        await file.close()

    # 3. File extraction and location mapping
    try:
        extracted = process_uploaded_file(content, file.filename)
    except UnsupportedFileTypeError as ufte:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=str(ufte),
        )
    except FileOversizedError as foe:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=str(foe),
        )
    except NoSelectableTextPDFError as nste:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(nste),
        )
    except EmptyFileError as efe:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(efe),
        )
    except FileProcessingError as fpe:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File processing error: {str(fpe)}",
        )

    # 4. Process through existing Step 2 AI extraction & chunking pipeline
    try:
        result = analyze_communication(
            raw_text=extracted.full_text,
            source_blocks=extracted.blocks,
            default_source_name=extracted.filename,
            default_source_type=extracted.source_type,
        )
        duration_ms = (time.perf_counter() - start_t) * 1000.0
        logger.info(
            "analysis_completed type=file filename=%s duration_ms=%.2f key_points=%d actions=%d decisions=%d dates=%d user_id=%s",
            file.filename,
            duration_ms,
            len(result.keyPoints),
            len(result.actions),
            len(result.decisions),
            len(result.importantDates),
            current_user.id,
        )
        return result
    except ValueError as ve:
        duration_ms = (time.perf_counter() - start_t) * 1000.0
        logger.error("analysis_failed type=file filename=%s duration_ms=%.2f error=%s user_id=%s", file.filename, duration_ms, ve, current_user.id)
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
        duration_ms = (time.perf_counter() - start_t) * 1000.0
        logger.error("analysis_failed type=file timeout filename=%s duration_ms=%.2f user_id=%s: %s", file.filename, duration_ms, current_user.id, te)
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail="The extraction request timed out. Please try again or analyze a shorter document.",
        )
    except RuntimeError as re:
        duration_ms = (time.perf_counter() - start_t) * 1000.0
        logger.error("analysis_failed type=file runtime_error filename=%s duration_ms=%.2f user_id=%s: %s", file.filename, duration_ms, current_user.id, re)
        err_msg = str(re)
        if "quota" in err_msg.lower() or "rate limit" in err_msg.lower():
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=err_msg,
            )
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"AI extraction provider error: {err_msg}",
        )
    except Exception as e:
        duration_ms = (time.perf_counter() - start_t) * 1000.0
        logger.exception("Unexpected error during file communication analysis (filename=%s, duration_ms=%.2f, user_id=%s)", file.filename, duration_ms, current_user.id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred while analyzing the document.",
        )
