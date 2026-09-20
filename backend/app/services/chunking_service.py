import re
from typing import List, Optional
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


def score_key_point(kp: KeyPointItem) -> float:
    """
    Scores a key point based on Shiftly's extraction semantics.
    Higher score indicates higher project consequence/importance.
    """
    score = 0.0
    text = kp.point.lower()

    # 1. Category weighting
    cat = (kp.category or "").lower()
    if cat == "decision":
        score += 10.0
    elif cat == "action":
        score += 8.0
    elif cat == "update":
        score += 5.0
    elif cat == "risk":
        score += 6.0
    else:
        score += 3.0

    # 2. Decisions & explicit approvals
    if any(w in text for w in [
        "approved", "approval", "agreed", "agree", "decision", "decided",
        "confirmed", "sign-off", "signed off", "finalized", "accepted", "resolved"
    ]):
        score += 4.0

    # 3. Confirmed commitments, critical deadlines, milestones
    if any(w in text for w in [
        "will deliver", "committed", "deadline", "milestone", "due by", "by friday",
        "by monday", "by tuesday", "by wednesday", "by thursday", "scheduled for",
        "must complete", "action item", "assigned to", "deliver"
    ]):
        score += 3.5

    # 4. Important changes & scope/cost impacts
    if any(w in text for w in [
        "change order", "scope change", "revised", "revision", "delay", "budget",
        "cost", "critical", "blocking", "blocked", "priority", "requirement",
        "inspection", "specification", "drawings", "package"
    ]):
        score += 3.0

    # 5. Consequential concrete facts (measurements, dates, currency, numbers)
    if re.search(r"\b\d+([.,]\d+)?\s*(mm|cm|m|km|kg|lbs|%|k|m|hours|days|weeks|pm|am)\b", text):
        score += 2.0
    if re.search(r"(\$|â‚¬|Â£|â‚¹|\b\d{1,2}/\d{1,2}\b|\boct\b|\bnov\b|\bdec\b|\bjan\b|\bfeb\b|\bmar\b|\bapr\b|\bmay\b|\bjun\b|\bjul\b|\baug\b|\bsep\b)", text):
        score += 2.0

    # 6. Valid, substantive source citation bonus
    if kp.source and kp.source.excerpt and len(kp.source.excerpt.strip()) > 10:
        score += 1.0

    # 7. Penalties for low-value greetings or off-topic chatter
    if any(w in text for w in [
        "good morning", "good afternoon", "hello", "hi there", "thanks", "thank you",
        "nice to meet", "how are you", "sounds good", "great job", "thumbs up"
    ]):
        score -= 6.0

    # 8. Penalty for speculative, non-committal or uncertain chatter
    if any(w in text for w in [
        "maybe", "perhaps", "might be", "not sure", "just wondering", "possibly", "could be"
    ]):
        score -= 4.0

    # 9. Penalty for extremely short phrases lacking context (< 15 chars)
    if len(text.strip()) < 15:
        score -= 3.0

    return score


def select_meaningful_key_points(key_points: List[KeyPointItem]) -> List[KeyPointItem]:
    """
    Retains all genuinely important, non-redundant key points without arbitrary caps.
    1. Filters out low-value greetings, conversational fluff, and trivial filler based on semantic scoring.
    2. Deduplicates identical or near-duplicate key points using lexical overlap.
    3. Re-indexes IDs to kp-1, kp-2, ...
    4. Preserves all source references and grounding.
    """
    if not key_points:
        return []

    meaningful: List[KeyPointItem] = []
    seen_texts: List[str] = []

    for kp in key_points:
        # Quality/relevance filter: filter out points that score <= 0.0 (e.g. pure greetings, filler)
        if score_key_point(kp) <= 0.0:
            continue

        # Deduplication using lexical overlap
        if not _is_near_duplicate(kp.point, seen_texts, threshold=0.75):
            seen_texts.append(kp.point)
            meaningful.append(kp)

    # Re-index IDs sequentially
    for idx, item in enumerate(meaningful, start=1):
        item.id = f"kp-{idx}"

    return meaningful


def select_top_key_points(key_points: List[KeyPointItem], max_points: Optional[int] = None) -> List[KeyPointItem]:
    """Deprecated alias for select_meaningful_key_points. Retains all meaningful points without arbitrary cap."""
    return select_meaningful_key_points(key_points)


def merge_analysis_results(results: List[ShiftlyAnalysisResult]) -> ShiftlyAnalysisResult:
    """
    Merges multiple ShiftlyAnalysisResult objects into a single cohesive result,
    deduplicating key points, actions, decisions, and dates using normalized
    string matching and deterministic lexical overlap similarity.
    Retains all meaningful keyPoints without arbitrary caps.
    """
    if not results:
        raise ValueError("Cannot merge empty results list.")

    if len(results) == 1:
        # Re-verify and sync stats with extracted list lengths
        res = results[0]
        res.keyPoints = select_meaningful_key_points(res.keyPoints)
        res.stats.keyPointsCount = len(res.keyPoints)
        res.stats.actionsCount = len(res.actions)
        res.stats.decisionsCount = len(res.decisions)
        res.stats.importantDatesCount = len(res.importantDates)
        return res

    base = results[0]
    all_summaries: List[str] = [r.summary.strip() for r in results if r.summary.strip()]

    # Deduplicate Key Points retaining all meaningful items without arbitrary caps
    merged_kp: List[KeyPointItem] = []
    for r in results:
        merged_kp.extend(r.keyPoints)
    merged_kp = select_meaningful_key_points(merged_kp)

    # Deduplicate & consolidate Actions across chunks
    merged_actions: List[ActionItem] = []
    for r in results:
        for act in r.actions:
            matched_act = None
            for existing in merged_actions:
                # Direct match or high token overlap on action task
                if _normalize_key(act.action) == _normalize_key(existing.action) or (
                    _word_tokens(act.action) and _word_tokens(existing.action) and
                    len(_word_tokens(act.action).intersection(_word_tokens(existing.action))) /
                    len(_word_tokens(act.action).union(_word_tokens(existing.action))) >= 0.70
                ):
                    matched_act = existing
                    break

            if matched_act:
                # Consolidate: if new act has assigned person and existing was Unassigned, update
                if (not matched_act.responsiblePerson or matched_act.responsiblePerson in ("Unassigned", "Unknown")) and (act.responsiblePerson and act.responsiblePerson not in ("Unassigned", "Unknown")):
                    matched_act.responsiblePerson = act.responsiblePerson
                # Consolidate: if new act has explicit deadline and existing didn't, update
                if not matched_act.deadline and act.deadline:
                    matched_act.deadline = act.deadline
                # Consolidate: priority
                if act.priority == "High":
                    matched_act.priority = "High"
                # Consolidate source if new one has longer/better excerpt
                if act.source and act.source.excerpt and (not matched_act.source or not matched_act.source.excerpt or len(act.source.excerpt) > len(matched_act.source.excerpt)):
                    matched_act.source = act.source
            else:
                act.id = f"act-{len(merged_actions) + 1}"
                merged_actions.append(act)

    # Deduplicate & consolidate Decisions across chunks
    merged_decisions: List[DecisionItem] = []
    for r in results:
        for dec in r.decisions:
            matched_dec = None
            for existing in merged_decisions:
                if _normalize_key(dec.decision) == _normalize_key(existing.decision) or (
                    _word_tokens(dec.decision) and _word_tokens(existing.decision) and
                    len(_word_tokens(dec.decision).intersection(_word_tokens(existing.decision))) /
                    len(_word_tokens(dec.decision).union(_word_tokens(existing.decision))) >= 0.70
                ):
                    matched_dec = existing
                    break

            if matched_dec:
                if (not matched_dec.approvedBy or matched_dec.approvedBy in ("Unknown", "—")) and (dec.approvedBy and dec.approvedBy not in ("Unknown", "—")):
                    matched_dec.approvedBy = dec.approvedBy
                if not matched_dec.date and dec.date:
                    matched_dec.date = dec.date
                if dec.source and dec.source.excerpt and (not matched_dec.source or not matched_dec.source.excerpt or len(dec.source.excerpt) > len(matched_dec.source.excerpt)):
                    matched_dec.source = dec.source
            else:
                dec.id = f"dec-{len(merged_decisions) + 1}"
                merged_decisions.append(dec)

    # Deduplicate & consolidate Important Dates across chunks
    merged_dates: List[ImportantDateItem] = []
    for r in results:
        for dt in r.importantDates:
            matched_dt = None
            norm_date = _normalize_key(dt.date)
            norm_title = _normalize_key(dt.title)
            for existing in merged_dates:
                if norm_date and norm_date == _normalize_key(existing.date):
                    if norm_title == _normalize_key(existing.title) or _is_near_duplicate(dt.title, [existing.title], threshold=0.60):
                        matched_dt = existing
                        break
                elif norm_title and norm_title == _normalize_key(existing.title):
                    matched_dt = existing
                    break

            if matched_dt:
                if len(dt.significance or "") > len(matched_dt.significance or ""):
                    matched_dt.significance = dt.significance
                if dt.source and dt.source.excerpt and (not matched_dt.source or not matched_dt.source.excerpt or len(dt.source.excerpt) > len(matched_dt.source.excerpt)):
                    matched_dt.source = dt.source
            else:
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

    # Cohesive synthesized summary from all chunks (deduplicating identical/near-duplicate sentences)
    summary_sentences: List[str] = []
    for s in all_summaries:
        for sent in re.split(r"(?<=[.!?])\s+", s):
            sent_clean = sent.strip()
            if sent_clean and not _is_near_duplicate(sent_clean, summary_sentences, threshold=0.75):
                summary_sentences.append(sent_clean)
    combined_summary = " ".join(summary_sentences) if summary_sentences else (base.summary or "")

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
