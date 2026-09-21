import os
import pytest
from fastapi.testclient import TestClient

os.environ["TEST_USE_SQLITE"] = "true"

from app.main import app
from app.models.schemas import (
    ShiftlyAnalysisResult,
    AnalysisStats,
    PendingDecisionItem,
    DecisionItem,
    ActionItem,
    KeyPointItem,
    ImportantDateItem,
    SourceReference,
)
from app.services.chunking_service import merge_analysis_results
from app.services.gemini_service import validate_and_align_sources
from app.db.repository import memory_repo

client = TestClient(app, headers={"Authorization": "Bearer test-token-123"})

TEST_SRC_1 = SourceReference(
    id="src-pd-1",
    sourceType="Chat Export",
    sourceName="#project-apollo",
    date="Nov 14, 2024",
    sender="Marcus Chen (Lead Architect)",
    messageRef="Msg #42",
    excerpt="We still need client sign-off on the exterior cladding material before placing the order.",
)

TEST_SRC_2 = SourceReference(
    id="src-pd-2",
    sourceType="Chat Export",
    sourceName="#project-apollo",
    date="Nov 14, 2024",
    sender="Sarah Connor (PM)",
    messageRef="Msg #45",
    excerpt="Should we go with Option A (Zinc) or Option B (Composite)? Marcus is waiting on David's decision.",
)

TEST_SRC_3 = SourceReference(
    id="src-pd-3",
    sourceType="Email Thread",
    sourceName="Structural Review",
    date="Nov 15, 2024",
    sender="David Miller (Client)",
    messageRef="Msg #50",
    excerpt="Approved Option A Zinc cladding. Let's move forward.",
)


def test_pending_decision_schema():
    """Verify PendingDecisionItem schema validation and default values."""
    pd = PendingDecisionItem(
        id="pd-101",
        decision="Awaiting David's selection between Zinc and Composite cladding",
        source=TEST_SRC_1,
    )
    assert pd.status == "Pending"
    assert pd.decision.startswith("Awaiting")
    assert pd.source.sender == "Marcus Chen (Lead Architect)"

    result = ShiftlyAnalysisResult(
        id="res-pd-1",
        title="Cladding Review",
        analyzedAt="Nov 14, 2024",
        stats=AnalysisStats(
            messagesAnalyzed=5,
            pendingDecisionsCount=1,
        ),
        summary="Awaiting cladding selection.",
        pendingDecisions=[pd],
    )
    assert len(result.pendingDecisions) == 1
    assert result.stats.pendingDecisionsCount == 1
    dump = result.model_dump()
    assert dump["pendingDecisions"][0]["status"] == "Pending"
    assert dump["stats"]["pendingDecisionsCount"] == 1


def test_merge_pending_decisions_deduplication():
    """Verify that chunking merge consolidates and deduplicates pending decisions above similarity threshold."""
    r1 = ShiftlyAnalysisResult(
        id="chunk-1",
        title="Apollo Discussion Part 1",
        analyzedAt="Now",
        stats=AnalysisStats(messagesAnalyzed=10, pendingDecisionsCount=1),
        summary="Part 1 summary",
        pendingDecisions=[
            PendingDecisionItem(
                id="pd-c1",
                decision="Selection of exterior cladding material between Zinc and Composite awaiting client approval",
                source=TEST_SRC_1,
            )
        ],
    )

    r2 = ShiftlyAnalysisResult(
        id="chunk-2",
        title="Apollo Discussion Part 2",
        analyzedAt="Now",
        stats=AnalysisStats(messagesAnalyzed=12, pendingDecisionsCount=1),
        summary="Part 2 summary",
        pendingDecisions=[
            PendingDecisionItem(
                id="pd-c2",
                decision="Selection of exterior cladding material between Zinc and Composite awaiting client approval",
                source=TEST_SRC_2,
            )
        ],
    )

    merged = merge_analysis_results([r1, r2])
    # Should deduplicate into 1 pending decision
    assert len(merged.pendingDecisions) == 1
    assert merged.stats.pendingDecisionsCount == 1
    assert "exterior cladding" in merged.pendingDecisions[0].decision.lower()


def test_merge_pending_decisions_distinct():
    """Verify that chunking merge preserves genuinely distinct pending decisions."""
    r1 = ShiftlyAnalysisResult(
        id="chunk-1",
        title="Part 1",
        analyzedAt="Now",
        stats=AnalysisStats(messagesAnalyzed=10, pendingDecisionsCount=1),
        summary="Part 1",
        pendingDecisions=[
            PendingDecisionItem(
                id="pd-1",
                decision="Choice of HVAC supplier (Trane vs Carrier) awaiting engineering review",
                source=TEST_SRC_1,
            )
        ],
    )

    r2 = ShiftlyAnalysisResult(
        id="chunk-2",
        title="Part 2",
        analyzedAt="Now",
        stats=AnalysisStats(messagesAnalyzed=10, pendingDecisionsCount=1),
        summary="Part 2",
        pendingDecisions=[
            PendingDecisionItem(
                id="pd-2",
                decision="Permit submission timing awaiting municipal board schedule confirmation",
                source=TEST_SRC_2,
            )
        ],
    )

    merged = merge_analysis_results([r1, r2])
    assert len(merged.pendingDecisions) == 2
    assert merged.stats.pendingDecisionsCount == 2


def test_pending_decisions_db_persistence_and_search():
    """Verify saving analysis with pending decisions in repository, retrieval, and search."""
    user_id = "test-user-pd-999"
    proj = memory_repo.create_project(name="Project Apollo", description="High-rise construction", user_id=user_id)
    project_id = proj.id

    analysis = ShiftlyAnalysisResult(
        id="apollo-analysis-1",
        title="Apollo Façade Review",
        analyzedAt="Nov 14, 2024",
        stats=AnalysisStats(
            messagesAnalyzed=20,
            keyPointsCount=1,
            actionsCount=1,
            decisionsCount=1,
            importantDatesCount=1,
            pendingDecisionsCount=2,
        ),
        summary="Facade materials discussed; zinc cladding approved, window acoustic rating pending.",
        keyPoints=[
            KeyPointItem(id="kp-1", point="Zinc cladding meets aesthetic guidelines.", source=TEST_SRC_1)
        ],
        actions=[
            ActionItem(id="act-1", action="Request acoustic test report", responsiblePerson="Marcus", deadline="Nov 20", source=TEST_SRC_1)
        ],
        decisions=[
            DecisionItem(id="dec-1", decision="Approved Option A Zinc cladding", approvedBy="David Miller", date="Nov 15", source=TEST_SRC_3)
        ],
        importantDates=[
            ImportantDateItem(id="dt-1", title="Acoustic Report Deadline", date="Nov 20, 2024", significance="Before glass fabrication", source=TEST_SRC_1)
        ],
        pendingDecisions=[
            PendingDecisionItem(
                id="pd-1",
                decision="Selection of acoustic glass thickness awaiting consultant recommendation",
                status="Pending",
                source=TEST_SRC_1,
            ),
            PendingDecisionItem(
                id="pd-2",
                decision="Final choice between motorized or manual sunshades awaiting cost analysis",
                status="Pending",
                source=TEST_SRC_2,
            ),
        ],
    )

    saved_summary = memory_repo.save_analysis(project_id, analysis, user_id=user_id)
    assert saved_summary is not None
    saved_id = saved_summary.id

    # Retrieve analysis
    retrieved = memory_repo.get_analysis(project_id, saved_id, user_id=user_id)
    assert retrieved is not None
    assert len(retrieved.pendingDecisions) == 2
    assert retrieved.stats.pendingDecisionsCount == 2
    pds = {p.decision for p in retrieved.pendingDecisions}
    assert "Selection of acoustic glass thickness awaiting consultant recommendation" in pds
    assert "Final choice between motorized or manual sunshades awaiting cost analysis" in pds

    # Verify source reference preserved
    for pd in retrieved.pendingDecisions:
        assert pd.source is not None
        assert pd.source.sourceName is not None

    # Test Project Memory Search finds pending decisions
    search_res = memory_repo.search_project_memory(project_id, "sunshades", user_id=user_id)
    assert len(search_res) > 0
    match = search_res[0]
    assert match.item_type == "Pending Decision"
    assert "sunshades" in match.content.lower()


def test_project_aggregated_intelligence():
    """Verify aggregated project intelligence merges multiple analyses including pending decisions."""
    user_id = "test-user-agg-123"
    proj = memory_repo.create_project(name="Project Aggregation", description="Multi-phase", user_id=user_id)
    project_id = proj.id

    a1 = ShiftlyAnalysisResult(
        id="analysis-a1",
        title="Phase 1 Meeting",
        analyzedAt="Nov 1, 2024",
        stats=AnalysisStats(messagesAnalyzed=10, pendingDecisionsCount=1, decisionsCount=1),
        summary="Phase 1 kickoff",
        decisions=[DecisionItem(id="d1", decision="Kickoff approved", approvedBy="David", date="Nov 1", source=TEST_SRC_1)],
        pendingDecisions=[
            PendingDecisionItem(id="pd-a1", decision="Selection of foundation contractor awaiting bids", source=TEST_SRC_1)
        ],
    )

    a2 = ShiftlyAnalysisResult(
        id="analysis-a2",
        title="Phase 2 Meeting",
        analyzedAt="Nov 8, 2024",
        stats=AnalysisStats(messagesAnalyzed=15, pendingDecisionsCount=1, decisionsCount=1),
        summary="Phase 2 planning",
        decisions=[DecisionItem(id="d2", decision="Structural grid approved", approvedBy="Elena", date="Nov 8", source=TEST_SRC_2)],
        pendingDecisions=[
            PendingDecisionItem(id="pd-a2", decision="HVAC rooftop unit placement awaiting noise survey", source=TEST_SRC_2)
        ],
    )

    memory_repo.save_analysis(project_id, a1, user_id=user_id)
    memory_repo.save_analysis(project_id, a2, user_id=user_id)

    agg = memory_repo.get_project_aggregated_intelligence(project_id, user_id=user_id)
    assert agg is not None
    assert len(agg.pendingDecisions) == 2
    assert agg.stats.pendingDecisionsCount == 2
    assert len(agg.decisions) == 2
    assert agg.stats.decisionsCount == 2


def test_project_intelligence_endpoint():
    """Verify GET /api/projects/{project_id}/intelligence HTTP endpoint."""
    res_proj = client.post("/api/projects", json={"name": "Endpoint Test Project"})
    assert res_proj.status_code == 201
    proj_id = res_proj.json()["id"]

    res_int = client.get(f"/api/projects/{proj_id}/intelligence")
    assert res_int.status_code == 200
    data = res_int.json()
    assert "pendingDecisions" in data
    assert "stats" in data
    assert data["stats"]["pendingDecisionsCount"] == 0
    assert data["pendingDecisions"] == []
