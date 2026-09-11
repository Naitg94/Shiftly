import time
import logging
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, status
from app.core.config import settings
from app.models.schemas import AnalyzeRequest, ShiftlyAnalysisResult
from app.services.gemini_service import analyze_communication
from app.services.file_processing_service import (
    process_uploaded_file,
    MAX_FILE_SIZE_BYTES,
    UnsupportedFileTypeError,
    FileOversizedError,
    EmptyFileError,
    NoSelectableTextPDFError,
    InvalidWhatsAppZipError,
    ZipSecurityError,
    ZipBombError,
    EmailParsingError,
    FileProcessingError,
)
from app.core.auth import AuthenticatedUser, get_optional_current_user
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
    current_user: Optional[AuthenticatedUser] = Depends(get_optional_current_user),
    _rate_limit: bool = Depends(rate_limit_analyze),
) -> ShiftlyAnalysisResult:
    # 1. Validation: Empty or blank text
    if not payload.text or not payload.text.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The communication text cannot be empty. Please paste or provide a conversation to analyze.",
        )

    user_label = current_user.id if current_user else "guest"

    # 2. Server-side character length enforcement
    text_length = len(payload.text)
    if current_user is None:
        if text_length > settings.GUEST_MAX_TEXT_CHAR_COUNT:
            logger.warning(
                "guest_analysis_rejected_oversized chars=%d limit=%d",
                text_length,
                settings.GUEST_MAX_TEXT_CHAR_COUNT,
            )
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=(
                    f"This analysis is too large for guest mode ({text_length:,} characters, "
                    f"maximum {settings.GUEST_MAX_TEXT_CHAR_COUNT:,} characters). "
                    f"Create a free account or sign in to analyze up to {settings.MAX_INPUT_TEXT_CHARS:,} "
                    f"characters and save results to Project Memory."
                ),
            )
    else:
        if text_length > settings.MAX_INPUT_TEXT_CHARS:
            logger.warning(
                "authenticated_analysis_rejected_oversized chars=%d limit=%d user_id=%s",
                text_length,
                settings.MAX_INPUT_TEXT_CHARS,
                current_user.id,
            )
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=f"Text exceeds maximum allowed length of {settings.MAX_INPUT_TEXT_CHARS:,} characters.",
            )

    start_t = time.perf_counter()
    logger.info("analysis_started type=text chars=%d user_id=%s", text_length, user_label)

    # 3. Execution through Gemini extraction & chunking pipeline
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
            user_label,
        )
        return result
    except ValueError as ve:
        duration_ms = (time.perf_counter() - start_t) * 1000.0
        logger.error("analysis_failed type=text duration_ms=%.2f error=%s user_id=%s", duration_ms, ve, user_label)
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
        logger.error("analysis_failed type=text timeout duration_ms=%.2f user_id=%s: %s", duration_ms, user_label, te)
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail="The extraction request timed out. Please try again or analyze a shorter segment.",
        )
    except RuntimeError as re:
        duration_ms = (time.perf_counter() - start_t) * 1000.0
        logger.error("analysis_failed type=text runtime_error duration_ms=%.2f user_id=%s: %s", duration_ms, user_label, re)
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
        logger.exception("Unexpected error during communication analysis (duration_ms=%.2f, user_id=%s)", duration_ms, user_label)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred while analyzing the communication.",
        )


@router.post(
    "/analyze/file",
    response_model=ShiftlyAnalysisResult,
    summary="Analyze Communication File (WhatsApp ZIP, Email .eml, PDF, DOCX, TXT / Chat)",
    description="Extracts text and source locations from an uploaded communication document or archive, then processes it through the Gemini extraction pipeline.",
)
async def analyze_file(
    file: UploadFile = File(...),
    current_user: Optional[AuthenticatedUser] = Depends(get_optional_current_user),
    _rate_limit: bool = Depends(rate_limit_analyze),
) -> ShiftlyAnalysisResult:
    # 1. Validate file presence
    if not file or not file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No file was uploaded. Please select a valid document (WhatsApp ZIP, Email .eml, PDF, DOCX, or TXT / Chat).",
        )

    user_label = current_user.id if current_user else "guest"
    start_t = time.perf_counter()
    logger.info("analysis_started type=file filename=%s user_id=%s", file.filename, user_label)

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
    except ZipBombError as zbe:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=str(zbe),
        )
    except ZipSecurityError as zse:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(zse),
        )
    except InvalidWhatsAppZipError as iwze:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(iwze),
        )
    except EmailParsingError as epe:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(epe),
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

    # 4. Enforce extracted text character limit BEFORE calling Gemini
    extracted_chars = len(extracted.full_text)
    if current_user is None:
        if extracted_chars > settings.GUEST_MAX_TEXT_CHAR_COUNT:
            logger.warning(
                "guest_file_analysis_rejected_oversized filename=%s chars=%d limit=%d",
                file.filename,
                extracted_chars,
                settings.GUEST_MAX_TEXT_CHAR_COUNT,
            )
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=(
                    f"This document's extracted text is too large for guest mode ({extracted_chars:,} characters, "
                    f"maximum {settings.GUEST_MAX_TEXT_CHAR_COUNT:,} characters). "
                    f"Create a free account or sign in to analyze larger documents and save results to Project Memory."
                ),
            )
    else:
        if extracted_chars > settings.MAX_INPUT_TEXT_CHARS:
            logger.warning(
                "authenticated_file_analysis_rejected_oversized filename=%s chars=%d limit=%d user_id=%s",
                file.filename,
                extracted_chars,
                settings.MAX_INPUT_TEXT_CHARS,
                current_user.id,
            )
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=f"Extracted document text exceeds maximum allowed length of {settings.MAX_INPUT_TEXT_CHARS:,} characters.",
            )

    # 5. Process through existing Step 2 AI extraction & chunking pipeline
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
            user_label,
        )
        return result
    except ValueError as ve:
        duration_ms = (time.perf_counter() - start_t) * 1000.0
        logger.error("analysis_failed type=file filename=%s duration_ms=%.2f error=%s user_id=%s", file.filename, duration_ms, ve, user_label)
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
        logger.error("analysis_failed type=file timeout filename=%s duration_ms=%.2f user_id=%s: %s", file.filename, duration_ms, user_label, te)
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail="The extraction request timed out. Please try again or analyze a shorter document.",
        )
    except RuntimeError as re:
        duration_ms = (time.perf_counter() - start_t) * 1000.0
        logger.error("analysis_failed type=file runtime_error filename=%s duration_ms=%.2f user_id=%s: %s", file.filename, duration_ms, user_label, re)
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
        logger.exception("Unexpected error during file communication analysis (filename=%s, duration_ms=%.2f, user_id=%s)", file.filename, duration_ms, user_label)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred while analyzing the document.",
        )
