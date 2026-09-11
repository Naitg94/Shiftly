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
    if re.search(r"(\$|€|£|₹|\b\d{1,2}/\d{1,2}\b|\boct\b|\bnov\b|\bdec\b|\bjan\b|\bfeb\b|\bmar\b|\bapr\b|\bmay\b|\bjun\b|\bjul\b|\baug\b|\bsep\b)", text):
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


def select_top_key_points(key_points: List[KeyPointItem], max_points: int = 5) -> List[KeyPointItem]:
    """
    Enforces a strict deterministic cap of at most max_points (default 5).
    1. Deduplicates identical or near-duplicate key points first.
    2. If distinct count <= max_points (e.g. 0, 1, 2, 3, 5), returns all distinct points.
    3. If distinct count > max_points, ranks points using extraction semantics and returns top max_points.
    4. Re-indexes IDs to kp-1, kp-2, ...
    5. Preserves all source references.
    """
    if not key_points:
        return []

    # Step 1: Deduplicate key points using lexical overlap
    deduped: List[KeyPointItem] = []
    seen_texts: List[str] = []
    for kp in key_points:
        if not _is_near_duplicate(kp.point, seen_texts, threshold=0.75):
            seen_texts.append(kp.point)
            deduped.append(kp)

    # Step 2: If <= max_points, keep all and re-index
    if len(deduped) <= max_points:
        for idx, item in enumerate(deduped, start=1):
            item.id = f"kp-{idx}"
        return deduped

    # Step 3: Rank points with stable sort
    scored = [(score_key_point(kp), idx, kp) for idx, kp in enumerate(deduped)]
    # Higher score first; on tie, preserve original order (idx ascending)
    scored.sort(key=lambda x: (-x[0], x[1]))

    top_items = [item[2] for item in scored[:max_points]]

    # Step 4: Re-index IDs
    for idx, item in enumerate(top_items, start=1):
        item.id = f"kp-{idx}"

    return top_items


def merge_analysis_results(results: List[ShiftlyAnalysisResult]) -> ShiftlyAnalysisResult:
    """
    Merges multiple ShiftlyAnalysisResult objects into a single cohesive result,
    deduplicating key points, actions, decisions, and dates using normalized
    string matching and deterministic lexical overlap similarity.
    Enforces a deterministic cap of AT MOST 5 items on keyPoints.
    """
    if not results:
        raise ValueError("Cannot merge empty results list.")

    if len(results) == 1:
        # Re-verify and sync stats with extracted list lengths
        res = results[0]
        res.keyPoints = select_top_key_points(res.keyPoints, max_points=5)
        res.stats.keyPointsCount = len(res.keyPoints)
        res.stats.actionsCount = len(res.actions)
        res.stats.decisionsCount = len(res.decisions)
        res.stats.importantDatesCount = len(res.importantDates)
        return res

    base = results[0]
    all_summaries: List[str] = [r.summary.strip() for r in results if r.summary.strip()]

    # Deduplicate Key Points and apply strict 5-item cap
    merged_kp: List[KeyPointItem] = []
    for r in results:
        merged_kp.extend(r.keyPoints)
    merged_kp = select_top_key_points(merged_kp, max_points=5)

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
