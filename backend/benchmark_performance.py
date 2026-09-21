import os
import time
import statistics
from typing import List

os.environ["TEST_USE_SQLITE"] = "true"

from app.models.schemas import (
    ShiftlyAnalysisResult,
    AnalysisStats,
    KeyPointItem,
    ActionItem,
    DecisionItem,
    ImportantDateItem,
    PendingDecisionItem,
    SourceReference,
)
from app.services.chunking_service import (
    normalize_text,
    estimate_messages_count,
    merge_analysis_results,
    deduplicate_important_dates,
    select_meaningful_key_points,
)
from app.services.gemini_service import validate_and_align_sources
from app.db.repository import memory_repo, _init_local_db

# Generate test datasets
SHORT_CONVERSATION = """[10:00] Alice: We need to finalize the launch date.
[10:02] Bob: October 15 works for marketing.
[10:05] Alice: Agreed. October 15 is the official launch date.
[10:06] Charlie: I will deploy to staging by October 10.
[10:10] David: Approved by VP Engineering."""

MEDIUM_CONVERSATION = "\n".join([
    f"[{10 + i // 60:02d}:{i % 60:02d}] User{i % 5}: Discussing milestone item {i} regarding infrastructure and design specs."
    for i in range(35)
])

LONG_CONVERSATION = "\n".join([
    f"[{8 + i // 60:02d}:{i % 60:02d}] Participant_{i % 8}: Construction update {i} - reviewing entrance layout, electrical wiring, and HVAC specifications for phase {i % 4 + 1}."
    for i in range(665)
])

def run_benchmarks(label: str):
    print(f"\n==================================================")
    print(f"BENCHMARK RUN: {label}")
    print(f"==================================================")

    # 1. Normalization & Estimation
    for name, text in [("Short (5 msgs)", SHORT_CONVERSATION), ("Medium (35 msgs)", MEDIUM_CONVERSATION), ("Long (665 msgs)", LONG_CONVERSATION)]:
        times = []
        for _ in range(50):
            t0 = time.perf_counter()
            norm = normalize_text(text)
            est = estimate_messages_count(norm)
            times.append((time.perf_counter() - t0) * 1000.0)
        print(f"[Norm + Est] {name}: avg={statistics.mean(times):.3f}ms, min={min(times):.3f}ms, max={max(times):.3f}ms")

    # 2. Source Alignment Benchmark
    # Create sample analysis result with 20 items
    src_ref = SourceReference(
        id="src-1",
        sourceType="Chat Export",
        sourceName="Project Log",
        date="10:05",
        sender="Alice",
        messageRef="Msg #3",
        excerpt="October 15 is the official launch date",
    )
    res = ShiftlyAnalysisResult(
        id="res-bench-1",
        title="Benchmark Analysis",
        analyzedAt="Now",
        stats=AnalysisStats(messagesAnalyzed=665),
        summary="Summary of project work.",
        keyPoints=[
            KeyPointItem(id=f"kp-{i}", point=f"Key factual milestone update {i}", source=src_ref)
            for i in range(10)
        ],
        actions=[
            ActionItem(id=f"act-{i}", action=f"Complete task number {i}", responsiblePerson="Alice", deadline="Oct 15", source=src_ref)
            for i in range(8)
        ],
        decisions=[
            DecisionItem(id=f"dec-{i}", decision=f"Selected option {i} for reception lighting", approvedBy="David", date="Oct 12", source=src_ref)
            for i in range(5)
        ],
        importantDates=[
            ImportantDateItem(id=f"dt-{i}", title=f"Milestone target {i}", date=f"October {i + 1}", significance="Delivery date", source=src_ref)
            for i in range(5)
        ],
        pendingDecisions=[
            PendingDecisionItem(id=f"pd-{i}", decision=f"Awaiting confirmation on item {i}", source=src_ref)
            for i in range(4)
        ],
    )

    for name, text in [("Short (5 msgs)", SHORT_CONVERSATION), ("Medium (35 msgs)", MEDIUM_CONVERSATION), ("Long (665 msgs)", LONG_CONVERSATION)]:
        times = []
        for _ in range(30):
            # Deepcopy model
            r_copy = res.model_copy(deep=True)
            t0 = time.perf_counter()
            validate_and_align_sources(r_copy, text)
            times.append((time.perf_counter() - t0) * 1000.0)
        print(f"[Source Alignment] {name}: avg={statistics.mean(times):.3f}ms, min={min(times):.3f}ms, max={max(times):.3f}ms")

    # 3. Chunk Merge & Deduplication Benchmark
    chunks = [res.model_copy(deep=True) for _ in range(4)]
    times = []
    for _ in range(30):
        c_copies = [c.model_copy(deep=True) for c in chunks]
        t0 = time.perf_counter()
        merged = merge_analysis_results(c_copies)
        times.append((time.perf_counter() - t0) * 1000.0)
    print(f"[Chunk Merge & Dedup] 4 chunks (128 items total): avg={statistics.mean(times):.3f}ms, min={min(times):.3f}ms, max={max(times):.3f}ms")

    # 4. Database Operations Benchmark (SQLite test mode)
    _init_local_db(clear=True)
    proj = memory_repo.create_project("Benchmark Project", "Project for performance tests", user_id="user-bench-1")

    # Benchmark save_analysis
    times = []
    for i in range(10):
        r_save = res.model_copy(deep=True)
        r_save.id = f"bench-analysis-{i}"
        t0 = time.perf_counter()
        memory_repo.save_analysis(proj.id, r_save, user_id="user-bench-1")
        times.append((time.perf_counter() - t0) * 1000.0)
    print(f"[DB Save Analysis]: avg={statistics.mean(times):.3f}ms, min={min(times):.3f}ms, max={max(times):.3f}ms")

    # Benchmark get_project_aggregated_intelligence
    times = []
    for _ in range(10):
        t0 = time.perf_counter()
        agg = memory_repo.get_project_aggregated_intelligence(proj.id, user_id="user-bench-1")
        times.append((time.perf_counter() - t0) * 1000.0)
    print(f"[DB Aggregated Intelligence] (10 analyses): avg={statistics.mean(times):.3f}ms, min={min(times):.3f}ms, max={max(times):.3f}ms")

    # Benchmark search_project_memory
    times = []
    for q in ["milestone", "option", "October", "task"]:
        t0 = time.perf_counter()
        s_res = memory_repo.search_project_memory(proj.id, q, user_id="user-bench-1")
        times.append((time.perf_counter() - t0) * 1000.0)
    print(f"[DB Search Memory]: avg={statistics.mean(times):.3f}ms, min={min(times):.3f}ms, max={max(times):.3f}ms")

if __name__ == "__main__":
    run_benchmarks("BASELINE BEFORE OPTIMIZATION")
