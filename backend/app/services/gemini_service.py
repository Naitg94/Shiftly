import json
import logging
import os
import re
from typing import List, Optional, Any
from datetime import datetime
from google import genai
from google.genai import types
from google.genai.errors import APIError
from app.core.config import settings
from app.models.schemas import ShiftlyAnalysisResult
from app.services.chunking_service import (
    normalize_text,
    split_into_chunks,
    merge_analysis_results,
    estimate_messages_count,
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
6. QUALITY OVER QUANTITY: Prefer fewer high-value, actionable points over trivial chatter.
7. STRICT BOUNDARIES - DO NOT ADD:
   - Do NOT add risk scores or predictions.
   - Do NOT detect conflicts or sentiment.
   - Do NOT predict missing information.
   - Do NOT generate unsolicited recommendations.
   - Do NOT behave as a conversational chatbot.
"""


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

    try:
        response = client.models.generate_content(
            model=settings.GEMINI_MODEL,
            contents=prompt,
            config=types.GenerateContentConfig(
                system_instruction=SYSTEM_INSTRUCTION,
                response_mime_type="application/json",
                response_schema=ShiftlyAnalysisResult,
                temperature=0.1,
            ),
        )

        if not response.text:
            raise ValueError("Gemini returned an empty response.")

        # Validate with Pydantic
        result = ShiftlyAnalysisResult.model_validate_json(response.text)
        return result

    except APIError as e:
        logger.error(f"Gemini API error during extraction: {e}")
        raise RuntimeError(f"Gemini API communication error: {e.message}") from e
    except Exception as e:
        logger.error(f"Error parsing Gemini extraction result: {e}")
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

    return final_result

