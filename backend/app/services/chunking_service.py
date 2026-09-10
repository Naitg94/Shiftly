import re
from typing import List
from app.models.schemas import (
    ShiftlyAnalysisResult,
    KeyPointItem,
    ActionItem,
    DecisionItem,
    ImportantDateItem,
    AnalysisStats,
)


def normalize_text(text: str) -> str:
    """Normalize input text by standardizing line endings and removing control characters."""
    if not text:
        return ""
    # Standardize line endings
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    # Remove null bytes and non-printable control characters (except tab and newline)
    text = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]", "", text)
    # Collapse 3 or more newlines to 2
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def estimate_messages_count(text: str) -> int:
    """Estimate the number of messages based on typical chat/email patterns."""
    lines = text.split("\n")
    # Pattern matching timestamps like [10/12/2024, 08:34] or 10/12/24 8:34 AM or sender lines
    msg_pattern = re.compile(
        r"^(\[?\d{1,4}[-/.]\d{1,2}[-/.]\d{1,4}[,\s]+|\d{1,2}:\d{2}|From:|To:|On .+ wrote:|[A-Z][a-zA-Z\s]{1,30}:)"
    )
    count = 0
    for line in lines:
        if msg_pattern.search(line.strip()):
            count += 1
    # Fallback to non-empty paragraphs if pattern didn't catch enough
    if count < 2:
        paragraphs = [p for p in text.split("\n\n") if p.strip()]
        return max(1, len(paragraphs))
    return count


def split_into_chunks(text: str, max_chars: int = 15000, overlap_chars: int = 1200) -> List[str]:
    """
    Splits text into chunks preserving line/message boundaries where possible.
    If text is under max_chars, returns a single-item list without unnecessary chunking.
    """
    if len(text) <= max_chars:
        return [text]

    lines = text.split("\n")
    chunks: List[str] = []
    current_chunk_lines: List[str] = []
    current_len = 0

    for line in lines:
        line_len = len(line) + 1  # include newline
        if current_len + line_len > max_chars and current_chunk_lines:
            # Finalize current chunk
            chunk_str = "\n".join(current_chunk_lines).strip()
            chunks.append(chunk_str)

            # Keep tail lines for overlap to maintain message context
            overlap_lines: List[str] = []
            overlap_len = 0
            for prev_line in reversed(current_chunk_lines):
                if overlap_len + len(prev_line) + 1 <= overlap_chars:
                    overlap_lines.insert(0, prev_line)
                    overlap_len += len(prev_line) + 1
                else:
                    break

            current_chunk_lines = list(overlap_lines)
            current_len = overlap_len

        current_chunk_lines.append(line)
        current_len += line_len

    if current_chunk_lines:
        chunk_str = "\n".join(current_chunk_lines).strip()
        if chunk_str:
            chunks.append(chunk_str)

    return chunks if chunks else [text]


def _normalize_key(text: str) -> str:
    """Helper to generate a normalized key for deduplication."""
    return re.sub(r"[^\w\s]", "", text.lower()).strip()


def _word_tokens(text: str) -> set:
    """Extract set of significant word tokens (length >= 3)."""
    return set(re.findall(r"\b\w{3,}\b", text.lower()))


def _is_near_duplicate(text: str, existing_texts: list, threshold: float = 0.75) -> bool:
    """Checks if text is identical or near-duplicate to any text in existing_texts."""
    norm_new = _normalize_key(text)
    new_tokens = _word_tokens(text)
    
    for existing in existing_texts:
        if norm_new == _normalize_key(existing):
            return True
        existing_tokens = _word_tokens(existing)
        if new_tokens and existing_tokens:
            overlap = len(new_tokens.intersection(existing_tokens)) / len(new_tokens.union(existing_tokens))
            if overlap >= threshold:
                return True
    return False


def merge_analysis_results(results: List[ShiftlyAnalysisResult]) -> ShiftlyAnalysisResult:
    """
    Merges multiple ShiftlyAnalysisResult objects into a single cohesive result,
    deduplicating key points, actions, decisions, and dates using normalized
    string matching and deterministic lexical overlap similarity.
    """
    if not results:
        raise ValueError("Cannot merge empty results list.")

    if len(results) == 1:
        # Re-verify and sync stats with extracted list lengths
        res = results[0]
        res.stats.keyPointsCount = len(res.keyPoints)
        res.stats.actionsCount = len(res.actions)
        res.stats.decisionsCount = len(res.decisions)
        res.stats.importantDatesCount = len(res.importantDates)
        return res

    base = results[0]
    all_summaries: List[str] = [r.summary.strip() for r in results if r.summary.strip()]

    # Deduplicate Key Points
    seen_kp_texts: List[str] = []
    merged_kp: List[KeyPointItem] = []
    for r in results:
        for kp in r.keyPoints:
            if not _is_near_duplicate(kp.point, seen_kp_texts, threshold=0.75):
                seen_kp_texts.append(kp.point)
                kp.id = f"kp-{len(merged_kp) + 1}"
                merged_kp.append(kp)

    # Deduplicate Actions
    seen_act_keys: List[str] = []
    merged_actions: List[ActionItem] = []
    for r in results:
        for act in r.actions:
            act_key = f"{act.action} ({act.responsiblePerson})"
            if not _is_near_duplicate(act_key, seen_act_keys, threshold=0.75):
                seen_act_keys.append(act_key)
                act.id = f"act-{len(merged_actions) + 1}"
                merged_actions.append(act)

    # Deduplicate Decisions
    seen_dec_texts: List[str] = []
    merged_decisions: List[DecisionItem] = []
    for r in results:
        for dec in r.decisions:
            if not _is_near_duplicate(dec.decision, seen_dec_texts, threshold=0.75):
                seen_dec_texts.append(dec.decision)
                dec.id = f"dec-{len(merged_decisions) + 1}"
                merged_decisions.append(dec)

    # Deduplicate Important Dates
    seen_dates: set = set()
    merged_dates: List[ImportantDateItem] = []
    for r in results:
        for dt in r.importantDates:
            key = _normalize_key(f"{dt.date}_{dt.title}")
            if key and key not in seen_dates:
                seen_dates.add(key)
                dt.id = f"dt-{len(merged_dates) + 1}"
                merged_dates.append(dt)

    total_msgs = sum(r.stats.messagesAnalyzed for r in results)
    max_participants = max((r.stats.participantsCount for r in results), default=2)

    merged_stats = AnalysisStats(
        messagesAnalyzed=total_msgs,
        participantsCount=max_participants,
        keyPointsCount=len(merged_kp),
        actionsCount=len(merged_actions),
        decisionsCount=len(merged_decisions),
        importantDatesCount=len(merged_dates),
    )

    # Cohesive synthesized summary
    combined_summary = " ".join(all_summaries) if len(all_summaries) <= 3 else f"{all_summaries[0]} Additionally, {all_summaries[-1]}"

    return ShiftlyAnalysisResult(
        id=base.id,
        title=base.title,
        analyzedAt=base.analyzedAt,
        stats=merged_stats,
        summary=combined_summary,
        keyPoints=merged_kp,
        actions=merged_actions,
        decisions=merged_decisions,
        importantDates=merged_dates,
    )
