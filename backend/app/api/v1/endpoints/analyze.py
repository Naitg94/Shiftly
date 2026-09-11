import logging
from fastapi import APIRouter, HTTPException, UploadFile, File, status
from app.models.schemas import AnalyzeRequest, ShiftlyAnalysisResult
from app.services.gemini_service import analyze_communication
from app.services.file_processing_service import (
    process_uploaded_file,
    UnsupportedFileTypeError,
    FileOversizedError,
    EmptyFileError,
    NoSelectableTextPDFError,
    FileProcessingError,
)

logger = logging.getLogger("shiftly.api.analyze")
router = APIRouter()


@router.post(
    "/analyze",
    response_model=ShiftlyAnalysisResult,
    summary="Analyze Unstructured Communication (Pasted Text)",
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


@router.post(
    "/analyze/file",
    response_model=ShiftlyAnalysisResult,
    summary="Analyze Communication File (TXT, PDF, DOCX, Chat Export)",
    description="Extracts text and source locations from an uploaded document, then processes it through the Gemini extraction pipeline.",
)
async def analyze_file(file: UploadFile = File(...)) -> ShiftlyAnalysisResult:
    # 1. Validate file presence
    if not file or not file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No file was uploaded. Please select a valid document (TXT, PDF, DOCX, or Chat Export).",
        )

    # 2. Read file content safely into memory
    try:
        content = await file.read()
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
        logger.error(f"Timeout while calling Gemini on file extraction: {te}")
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail="The extraction request timed out. Please try again or analyze a shorter document.",
        )
    except RuntimeError as re:
        logger.error(f"Runtime error in file extraction: {re}")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"AI extraction provider error: {str(re)}",
        )
    except Exception as e:
        logger.exception("Unexpected error during file communication analysis")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An unexpected error occurred while analyzing the document: {str(e)}",
        )
