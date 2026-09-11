import json
import logging
import os
import re
import time
from typing import List, Optional, Any
from datetime import datetime
from google import genai
from google.genai import types
from google.genai.errors import APIError
import httpx
from app.core.config import settings
from app.models.schemas import ShiftlyAnalysisResult
from app.services.chunking_service import (
    normalize_text,
    split_into_chunks,
    merge_analysis_results,
    estimate_messages_count,
    select_top_key_points,
)

logger = logging.getLogger("shiftly.gemini")

SYSTEM_INSTRUCTION = """You are Shiftly's Communication Intelligence Extraction Engine.
Your tagline is: "Find what matters."

Your sole task is INFORMATION EXTRACTION from unstructured project communication (such as chat transcripts, Slack/Teams threads, emails, meeting notes).

RULES & CORE PRINCIPLES:
1. EXTRACT ONLY EXPLICIT FACTS: Extract only information that is explicitly stated in the conversation. Do not invent, infer unsupported facts, or guess. If a person, date, or decision is not explicitly supported by the text, return 'Unassigned' or omit rather than guessing.
2. DISCARD NOISE: Ignore greetings, pleasantries, filler words, emoji reactions, repetitive confirmations, and off-topic banter.
3. DISTINGUISH ACTIONS VS DISCUSSION: Extract committed tasks as Actions (who is doing what by when). Distinguish between mere ideas/proposals and committed tasks.
4. DISTINGUISH DECISIONS VS DEBATE: Extract concrete agreements, sign-offs, and approvals as Decisions.
5. PRESERVE ACCURATE SOURCES: For every extracted key point, action, decision, and important date, provide a SourceReference containing:
   - sourceType: 'Chat Export', 'Email Thread', 'Meeting Transcript', or 'Document'
   - sourceName: The project or conversation name
   - date: The timestamp/date of the message if available
   - sender: The person who sent the message
   - messageRef: Reference tag, e.g. 'Message #4' or 'Line 12'
   - excerpt: An exact concise sentence/quote from the text that proves the extraction.
6. QUALITY OVER QUANTITY: Prefer fewer high-value, actionable points over trivial chatter. In keyPoints, extract AT MOST the 5 most important high-level takeaways (decisions, commitments, major changes). If only 2 or 3 genuinely important points exist, return 2 or 3. Never exceed 5 key points.
7. STRICT BOUNDARIES - DO NOT ADD:
   - Do NOT add risk scores or predictions.
   - Do NOT detect conflicts or sentiment.
   - Do NOT predict missing information.
   - Do NOT generate unsolicited recommendations.
   - Do NOT behave as a conversational chatbot.
8. DO NOT INVENT DATES OR FACTS:
   - If the conversation does not contain an explicit date or timestamp, do NOT guess or make up a date (such as 2023 or today's date).
   - In SourceReference.date: If no explicit message timestamp/date exists in the source text, use '—' or omit.
   - If a deadline is stated as 'Friday, September 11' or 'tomorrow', preserve that exact text. Never convert it into an arbitrary calendar date (like 2023-09-08).
"""


MAX_ALLOWED_CHUNKS = 15


def get_gemini_client() -> genai.Client:
    """Returns an initialized Google GenAI client."""
    if not settings.GEMINI_API_KEY:
        raise ValueError(
            "GEMINI_API_KEY is not configured. Please set GEMINI_API_KEY in backend/.env"
        )
    return genai.Client(api_key=settings.GEMINI_API_KEY)


def extract_chunk(
    client: genai.Client,
    chunk_text: str,
    chunk_index: int = 1,
    total_chunks: int = 1,
) -> ShiftlyAnalysisResult:
    """Extracts structured intelligence from a single text chunk using Gemini."""
    prompt = f"""Extract all critical project information from the following communication log.

COMMUNICATION LOG (Part {chunk_index} of {total_chunks}):
---
{chunk_text}
---

Produce a complete structured extraction matching the requested JSON schema."""

    start_t = time.perf_counter()
    logger.info("gemini_chunk_extraction_started chunk_index=%d total_chunks=%d", chunk_index, total_chunks)
    try:
        response = client.models.generate_content(
            model=settings.GEMINI_MODEL,
            contents=prompt,
            config=types.GenerateContentConfig(
                system_instruction=SYSTEM_INSTRUCTION,
                response_mime_type="application/json",
                response_schema=ShiftlyAnalysisResult,
                temperature=0.1,
                http_options=types.HttpOptions(timeout=60000.0),
            ),
        )

        if not response.text:
            raise ValueError("Gemini returned an empty response.")

        # Validate with Pydantic
        result = ShiftlyAnalysisResult.model_validate_json(response.text)
        duration_ms = (time.perf_counter() - start_t) * 1000.0
        logger.info(
            "gemini_chunk_extraction_completed chunk_index=%d total_chunks=%d duration_ms=%.2f key_points=%d actions=%d decisions=%d dates=%d",
            chunk_index,
            total_chunks,
            duration_ms,
            len(result.keyPoints),
            len(result.actions),
            len(result.decisions),
            len(result.importantDates),
        )
        return result

    except APIError as e:
        duration_ms = (time.perf_counter() - start_t) * 1000.0
        logger.error(f"Gemini API error during extraction (duration_ms={duration_ms:.2f}): {e}")
        err_msg = str(e)
        if getattr(e, "code", None) == 429 or "429" in err_msg or "RESOURCE_EXHAUSTED" in err_msg or "quota" in err_msg.lower():
            raise RuntimeError("AI extraction quota or rate limit exceeded. Please wait a moment before trying again.") from e
        raise RuntimeError(f"Gemini API communication error: {getattr(e, 'message', str(e))}") from e
    except (httpx.TimeoutException, TimeoutError) as te:
        duration_ms = (time.perf_counter() - start_t) * 1000.0
        logger.error(f"Timeout calling Gemini (duration_ms={duration_ms:.2f}): {te}")
        raise TimeoutError("Gemini extraction timed out.") from te
    except httpx.RequestError as re_err:
        duration_ms = (time.perf_counter() - start_t) * 1000.0
        logger.error(f"Network error calling Gemini (duration_ms={duration_ms:.2f}): {re_err}")
        raise RuntimeError(f"Network error communicating with AI service: {re_err}") from re_err
    except (json.JSONDecodeError, ValueError) as ve:
        duration_ms = (time.perf_counter() - start_t) * 1000.0
        logger.error(f"Error parsing Gemini extraction result structure (duration_ms={duration_ms:.2f}): {ve}")
        raise RuntimeError("AI service returned an unparseable response structure.") from ve
    except Exception as e:
        duration_ms = (time.perf_counter() - start_t) * 1000.0
        logger.error(f"Error during Gemini extraction (duration_ms={duration_ms:.2f}): {e}")
        raise




def validate_and_align_sources(
    result: ShiftlyAnalysisResult,
    raw_text: str,
    source_blocks: Optional[List[Any]] = None,
    default_source_name: Optional[str] = None,
    default_source_type: Optional[str] = None,
) -> ShiftlyAnalysisResult:
    """
    Validates and aligns every extracted item's source citation against the original text or
    source file ContentBlocks (preserving page numbers, paragraph indices, line numbers).
    """
    lines = [line.strip() for line in raw_text.split("\n") if line.strip()]

    def align_source(src):
        if not src:
            return src

        # Case 1: Source blocks provided (from PDF, DOCX, TXT file extraction)
        if source_blocks:
            src_words = set(re.findall(r"\b\w{3,}\b", (src.excerpt or "").lower()))
            best_block = None
            best_score = 0.0

            for block in source_blocks:
                block_lower = block.text.lower()
                excerpt_clean = (src.excerpt or "").strip().lower()

                # Direct substring match
                if excerpt_clean and (excerpt_clean in block_lower or block_lower in excerpt_clean):
                    best_block = block
                    best_score = 1.0
                    break

                # Overlap match
                block_words = set(re.findall(r"\b\w{3,}\b", block_lower))
                if src_words and block_words:
                    score = len(src_words.intersection(block_words)) / max(1, len(src_words))
                    if score > best_score:
                        best_score = score
                        best_block = block

            if best_block and best_score >= 0.35:
                src.sourceName = default_source_name or best_block.source_name
                src.sourceType = default_source_type or best_block.source_type
                src.messageRef = best_block.location
                if best_block.sender and (not src.sender or src.sender in {"Unassigned", "Unknown", "Document"}):
                    src.sender = best_block.sender
                # Align excerpt to the actual dialogue/sentence
                if ":" in best_block.text and not best_block.text.startswith("http"):
                    parts = best_block.text.split(":", 1)
                    src.excerpt = parts[1].strip()
                    if not src.sender or src.sender in {"Unassigned", "Unknown", "Document"}:
                        src.sender = parts[0].strip()
                else:
                    src.excerpt = best_block.text
                return src

            # Fallback if no block matched cleanly: still set filename and source type
            if default_source_name:
                src.sourceName = default_source_name
            if default_source_type:
                src.sourceType = default_source_type
            return src

        # Case 2: Pasted conversation (line snapping)
        if not src.excerpt:
            return src

        if src.excerpt.strip().lower() in raw_text.lower():
            return src

        src_words = set(re.findall(r"\b\w{3,}\b", src.excerpt.lower()))
        if not src_words:
            return src

        best_line = None
        best_score = 0.0
        for line in lines:
            line_words = set(re.findall(r"\b\w{3,}\b", line.lower()))
            if line_words:
                score = len(src_words.intersection(line_words)) / max(1, len(src_words))
                if score > best_score:
                    best_score = score
                    best_line = line

        if best_line and best_score >= 0.4:
            if ":" in best_line:
                speaker, dialogue = best_line.split(":", 1)
                src.excerpt = dialogue.strip()
                if not src.sender or src.sender == "Unassigned":
                    src.sender = speaker.strip()
            else:
                src.excerpt = best_line

        return src

    for kp in result.keyPoints:
        align_source(kp.source)
    for act in result.actions:
        align_source(act.source)
    for dec in result.decisions:
        align_source(dec.source)
    for dt in result.importantDates:
        align_source(dt.source)

    return result


def analyze_communication(
    raw_text: str,
    source_blocks: Optional[List[Any]] = None,
    default_source_name: Optional[str] = None,
    default_source_type: Optional[str] = None,
) -> ShiftlyAnalysisResult:
    """
    Main entrypoint: normalizes text, chunks if necessary, runs Gemini extraction,
    and merges/deduplicates multiple chunks into a unified ShiftlyAnalysisResult.
    Accepts optional source_blocks to accurately preserve file locations.
    """
    cleaned_text = normalize_text(raw_text)
    if not cleaned_text:
        raise ValueError("Provided text is empty or contains only whitespace.")

    client = get_gemini_client()
    chunks = split_into_chunks(cleaned_text, max_chars=15000, overlap_chars=1000)
    if len(chunks) > MAX_ALLOWED_CHUNKS:
        raise ValueError(
            f"Communication is too large to analyze in a single request ({len(chunks)} chunks exceeds the limit of {MAX_ALLOWED_CHUNKS}). Please analyze a shorter segment or document."
        )

    logger.info(f"Processing text ({len(cleaned_text)} chars) into {len(chunks)} chunk(s)")

    chunk_results: list[ShiftlyAnalysisResult] = []
    for idx, chunk in enumerate(chunks, start=1):
        res = extract_chunk(client, chunk, chunk_index=idx, total_chunks=len(chunks))
        chunk_results.append(res)

    final_result = merge_analysis_results(chunk_results)

    # Validate and snap source references to original conversation or file blocks
    final_result = validate_and_align_sources(
        final_result,
        cleaned_text,
        source_blocks=source_blocks,
        default_source_name=default_source_name,
        default_source_type=default_source_type,
    )

    # Set document title if analyzing a named file and model title is generic
    if default_source_name and (not final_result.title or final_result.title == "Shiftly Analysis"):
        clean_name = os.path.splitext(default_source_name)[0].replace("_", " ").title()
        final_result.title = f"{clean_name} Analysis"

    # Ensure metadata timestamps and realistic message estimates
    estimated_msgs = estimate_messages_count(cleaned_text)
    final_result.stats.messagesAnalyzed = max(final_result.stats.messagesAnalyzed, estimated_msgs)
    final_result.analyzedAt = datetime.now().strftime("%B %d, %Y • %I:%M %p")

    # Sanitize hallucinated dates if raw text does not contain any calendar year
    has_explicit_year = bool(re.search(r"\b(20\d{2}|19\d{2})\b", cleaned_text))
    if not has_explicit_year:
        for kp in final_result.keyPoints:
            if kp.source and kp.source.date and re.search(r"\b(20\d{2}|19\d{2})\b", kp.source.date):
                kp.source.date = "—"
        for act in final_result.actions:
            if act.deadline and re.search(r"\b20\d{2}[-/]\d{1,2}[-/]\d{1,2}\b", act.deadline):
                # If deadline was converted to e.g. 2023-09-11, check if text has the month/day name
                cleaned_deadline = re.sub(r"\b20\d{2}[-/]\d{1,2}[-/]\d{1,2}\b", "", act.deadline).strip(" ,-")
                act.deadline = cleaned_deadline if cleaned_deadline else None
            if act.source and act.source.date and re.search(r"\b(20\d{2}|19\d{2})\b", act.source.date):
                act.source.date = "—"
        for dec in final_result.decisions:
            if dec.date and re.search(r"\b(20\d{2}|19\d{2})\b", dec.date):
                dec.date = None
            if dec.source and dec.source.date and re.search(r"\b(20\d{2}|19\d{2})\b", dec.source.date):
                dec.source.date = "—"
        for dt in final_result.importantDates:
            if dt.date and re.search(r"\b20\d{2}[-/]\d{1,2}[-/]\d{1,2}\b", dt.date):
                cleaned_dt = re.sub(r"\b20\d{2}[-/]\d{1,2}[-/]\d{1,2}\b", "", dt.date).strip(" ,-")
                if cleaned_dt:
                    dt.date = cleaned_dt
            if dt.source and dt.source.date and re.search(r"\b(20\d{2}|19\d{2})\b", dt.source.date):
                dt.source.date = "—"

    # Enforce deterministic cap on keyPoints (at most 5 items)
    final_result.keyPoints = select_top_key_points(final_result.keyPoints, max_points=5)
    final_result.stats.keyPointsCount = len(final_result.keyPoints)

    return final_result

