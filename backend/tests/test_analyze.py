from fastapi.testclient import TestClient
from app.main import app
from app.services.chunking_service import (
    normalize_text,
    split_into_chunks,
    merge_analysis_results,
    estimate_messages_count,
)
from app.models.schemas import (
    ShiftlyAnalysisResult,
    AnalysisStats,
    KeyPointItem,
    ActionItem,
    DecisionItem,
    ImportantDateItem,
    SourceReference,
)

import os
os.environ["TEST_USE_SQLITE"] = "true"

client = TestClient(app, headers={"Authorization": "Bearer test-token-123"})

SAMPLE_CONVERSATION = """[10/12/2024, 08:34] David Miller (Client): Morning team. Did anyone get a chance to review the revised glazing package?
[10/12/2024, 08:42] Elena Vance (Lead Architect): Yes, we have an issue with the acoustic laminate on north facade.
[10/12/2024, 08:49] Marcus Brody (Contractor): If Elena signs off on triple-pane alternate AGC-400 by Thursday 4 PM, delivery is guaranteed by Nov 3.
[10/12/2024, 09:18] David Miller (Client): Approved. Let's do it. Elena, please issue Change Order #04 today.
[10/12/2024, 09:22] Elena Vance (Lead Architect): Understood. I will draft Change Order #04 and send to David by 5 PM today.
[10/12/2024, 10:10] Sophia Chen (Engineer): Rebar crew needs two #8 ties on column C-4 before I sign off. I'll submit the report by Monday Oct 14 at 12 PM."""


def test_health_endpoint():
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["service"] == "shiftly-backend"
    assert "gemini_configured" in data


def test_analyze_empty_input():
    response = client.post("/api/analyze", json={"text": "   "})
    assert response.status_code == 400
    assert "cannot be empty" in response.json()["detail"]


def test_analyze_missing_key_behavior():
    response = client.post("/api/analyze", json={"text": SAMPLE_CONVERSATION})
    # If GEMINI_API_KEY is not set in env, it should return 503 with helpful setup instructions
    # If set, it returns 200 with ShiftlyAnalysisResult
    assert response.status_code in [200, 503]
    if response.status_code == 503:
        assert "GEMINI_API_KEY" in response.json()["detail"]
    elif response.status_code == 200:
        data = response.json()
        assert "keyPoints" in data
        assert "actions" in data
        assert "decisions" in data


def test_chunking_and_normalization():
    raw = "  Line 1\r\n\r\n\r\n\r\nLine 2\r\n  "
    normalized = normalize_text(raw)
    assert "\r" not in normalized
    assert "\n\n\n" not in normalized
    assert normalized == "Line 1\n\nLine 2"

    # Small text should produce 1 chunk
    chunks = split_into_chunks(SAMPLE_CONVERSATION, max_chars=10000)
    assert len(chunks) == 1

    # Large text should split across boundary
    big_text = (SAMPLE_CONVERSATION + "\n\n") * 20
    big_chunks = split_into_chunks(big_text, max_chars=1500, overlap_chars=200)
    assert len(big_chunks) > 1


def test_merge_and_deduplication():
    src = SourceReference(
        id="src-1",
        sourceType="Chat Export",
        sourceName="Project Log",
        date="Oct 12",
        sender="Elena",
        messageRef="Msg #1",
        excerpt="Draft change order",
    )

    r1 = ShiftlyAnalysisResult(
        id="res-1",
        title="Project A",
        analyzedAt="Now",
        stats=AnalysisStats(messagesAnalyzed=6, keyPointsCount=1, actionsCount=1, decisionsCount=0, importantDatesCount=0),
        summary="Summary part 1",
        keyPoints=[KeyPointItem(id="kp-1", point="Facade glazing upgraded to triple-pane.", source=src)],
        actions=[ActionItem(id="act-1", action="Draft Change Order #04", responsiblePerson="Elena", deadline="5 PM", source=src)],
        decisions=[],
        importantDates=[],
    )

    r2 = ShiftlyAnalysisResult(
        id="res-2",
        title="Project A",
        analyzedAt="Now",
        stats=AnalysisStats(messagesAnalyzed=6, keyPointsCount=1, actionsCount=1, decisionsCount=1, importantDatesCount=0),
        summary="Summary part 2",
        keyPoints=[
            # Duplicate point
            KeyPointItem(id="kp-dup", point="Facade glazing upgraded to triple-pane.", source=src),
            KeyPointItem(id="kp-new", point="Rebar ties required on column C-4.", source=src),
        ],
        actions=[
            # Duplicate action
            ActionItem(id="act-dup", action="Draft Change Order #04", responsiblePerson="Elena", deadline="5 PM", source=src),
        ],
        decisions=[
            DecisionItem(id="dec-1", decision="Approved Change Order #04", approvedBy="David Miller", date="Oct 12", source=src),
        ],
        importantDates=[],
    )

    merged = merge_analysis_results([r1, r2])
    # Duplicate key point and duplicate action should be filtered out
    assert len(merged.keyPoints) == 2
    assert len(merged.actions) == 1
    assert len(merged.decisions) == 1
    assert merged.stats.keyPointsCount == 2
    assert merged.stats.actionsCount == 1
    assert merged.stats.decisionsCount == 1


def test_gemini_extraction_pipeline():
    from unittest.mock import MagicMock
    from app.services.gemini_service import extract_chunk
    
    mock_client = MagicMock()
    mock_response = MagicMock()
    # Realistic Gemini response JSON
    mock_response.text = '''{
        "id": "gemini-test-1",
        "title": "Elm St. Coordination",
        "analyzedAt": "October 12, 2024",
        "stats": {
            "messagesAnalyzed": 6,
            "participantsCount": 3,
            "keyPointsCount": 1,
            "actionsCount": 1,
            "decisionsCount": 1,
            "importantDatesCount": 1
        },
        "summary": "Glazing was upgraded to triple-pane alternate and Change Order #04 issued.",
        "keyPoints": [
            {
                "id": "kp-1",
                "point": "Triple-pane alternate AGC-400 avoids 4-week lead time.",
                "category": "Glazing",
                "source": {
                    "id": "src-1",
                    "sourceType": "Chat Export",
                    "sourceName": "Elm St. Site Coordination Channel",
                    "date": "Oct 12",
                    "sender": "Marcus Brody",
                    "messageRef": "Message #3",
                    "excerpt": "delivery is guaranteed by Nov 3"
                }
            }
        ],
        "actions": [
            {
                "id": "act-1",
                "action": "Draft Change Order #04 and send to client",
                "responsiblePerson": "Elena Vance",
                "deadline": "5:00 PM today",
                "priority": "High",
                "source": {
                    "id": "src-2",
                    "sourceType": "Chat Export",
                    "sourceName": "Elm St. Site Coordination Channel",
                    "date": "Oct 12",
                    "sender": "Elena Vance",
                    "messageRef": "Message #5",
                    "excerpt": "I will draft Change Order #04"
                }
            }
        ],
        "decisions": [
            {
                "id": "dec-1",
                "decision": "Approved triple pane upgrade",
                "approvedBy": "David Miller",
                "date": "Oct 12",
                "source": {
                    "id": "src-3",
                    "sourceType": "Chat Export",
                    "sourceName": "Elm St. Site Coordination Channel",
                    "date": "Oct 12",
                    "sender": "David Miller",
                    "messageRef": "Message #4",
                    "excerpt": "Approved. Let's do it."
                }
            }
        ],
        "importantDates": [
            {
                "id": "dt-1",
                "title": "Delivery guarantee date",
                "date": "Nov 3",
                "significance": "Avoids 4-week lead time slip",
                "source": {
                    "id": "src-4",
                    "sourceType": "Chat Export",
                    "sourceName": "Elm St. Site Coordination Channel",
                    "date": "Oct 12",
                    "sender": "Marcus Brody",
                    "messageRef": "Message #3",
                    "excerpt": "delivery is guaranteed by Nov 3"
                }
            }
        ]
    }'''
    mock_client.models.generate_content.return_value = mock_response

    result = extract_chunk(mock_client, SAMPLE_CONVERSATION)
    assert result.id == "gemini-test-1"
    assert len(result.keyPoints) == 1
    assert result.keyPoints[0].point == "Triple-pane alternate AGC-400 avoids 4-week lead time."
    assert len(result.actions) == 1
    assert result.actions[0].responsiblePerson == "Elena Vance"
    assert len(result.decisions) == 1
    assert result.decisions[0].approvedBy == "David Miller"


def test_key_points_cap_and_selection():
    from app.services.chunking_service import (
        select_meaningful_key_points,
        select_top_key_points,
        merge_analysis_results,
    )

    src = SourceReference(
        id="src-1",
        sourceType="Chat Export",
        sourceName="Site Channel",
        date="Oct 12",
        sender="Elena",
        messageRef="Msg 1",
        excerpt="Important proof quote from source",
    )

    # A. 2 important points -> exactly 2 key points
    two_pts = [
        KeyPointItem(id="kp-1", point="Approved Change Order #05 for structural beams.", category="Decision", source=src),
        KeyPointItem(id="kp-2", point="Deliver steel framing by Friday 4 PM.", category="Action", source=src),
    ]
    res_2 = select_meaningful_key_points(two_pts)
    assert len(res_2) == 2
    assert res_2[0].id == "kp-1"
    assert res_2[1].id == "kp-2"
    assert res_2[0].source.excerpt == "Important proof quote from source"

    # B. 5 important points -> exactly 5
    five_pts = [
        KeyPointItem(id="kp-1", point="Structural calculations approved for foundation slab.", category="Decision", source=src),
        KeyPointItem(id="kp-2", point="HVAC duct routing coordinated with ceiling contractor.", category="Update", source=src),
        KeyPointItem(id="kp-3", point="Fire safety permits issued by city inspectors.", category="Update", source=src),
        KeyPointItem(id="kp-4", point="Electrical conduit installation scheduled for East Wing.", category="Action", source=src),
        KeyPointItem(id="kp-5", point="Plumbing rough-in inspection passed with zero citations.", category="Update", source=src),
    ]
    res_5 = select_meaningful_key_points(five_pts)
    assert len(res_5) == 5

    # C. Filtering: greetings, banter, and filler filtered out without arbitrary cap
    ten_pts = [
        KeyPointItem(id="kp-1", point="Good morning everyone, happy Monday.", category="Information", source=src),
        KeyPointItem(id="kp-2", point="Approved revised structural package for East Wing.", category="Decision", source=src),
        KeyPointItem(id="kp-3", point="Thanks for the update earlier.", category="Information", source=src),
        KeyPointItem(id="kp-4", point="Will deliver HVAC chillers by Friday 3 PM deadline.", category="Action", source=src),
        KeyPointItem(id="kp-5", point="Maybe we could think about new paint colors perhaps.", category="Information", source=src),
        KeyPointItem(id="kp-6", point="Change Order #09 signed off, adding $15,000 to foundation budget.", category="Decision", source=src),
        KeyPointItem(id="kp-7", point="Fire damper inspection scheduled for Oct 24 milestone.", category="Action", source=src),
        KeyPointItem(id="kp-8", point="Critical acoustic barrier specifications confirmed at 55 dB.", category="Update", source=src),
        KeyPointItem(id="kp-9", point="Just wondering about lunch options today.", category="Information", source=src),
        KeyPointItem(id="kp-10", point="Facade glazing thickness revised to 24 mm.", category="Update", source=src),
        KeyPointItem(id="kp-11", point="Sounds good to me.", category="Information", source=src),
        KeyPointItem(id="kp-12", point="Hi there team.", category="Information", source=src),
    ]
    res_filtered = select_meaningful_key_points(ten_pts)
    # 6 genuinely meaningful points retained (no arbitrary cap to 5)
    assert len(res_filtered) == 6
    # Confirm trivial greetings and banter were excluded
    points_text = [kp.point for kp in res_filtered]
    assert not any("morning" in p.lower() for p in points_text)
    assert not any("lunch" in p.lower() for p in points_text)
    assert not any("thanks" in p.lower() for p in points_text)
    # Confirm high-value decision and action items were retained
    assert any("structural package" in p.lower() for p in points_text)
    assert any("change order #09" in p.lower() for p in points_text)
    # Confirm IDs are sequentially re-indexed
    assert [kp.id for kp in res_filtered] == ["kp-1", "kp-2", "kp-3", "kp-4", "kp-5", "kp-6"]
    # Retained key points still have valid source alignment
    for kp in res_filtered:
        assert kp.source is not None
        assert kp.source.excerpt == "Important proof quote from source"

    # D. 8 distinct important points -> all 8 retained (no arbitrary cap)
    distinct_8 = [
        "Approved structural drawings for foundation slab.",
        "Finalized HVAC chiller placement with mechanical engineer.",
        "Electrical permit approved by municipal building safety department.",
        "Plumbing rough-in inspection passed with zero citations.",
        "Roofing membrane installation scheduled for completion by Friday.",
        "Facade glazing specifications confirmed at 24 mm laminated glass.",
        "Fire damper testing coordinated with site superintendent.",
        "Landscaping and drainage grading plan signed off by civil team.",
    ]
    eight_pts = [
        KeyPointItem(id=f"kp-{i}", point=topic, category="Decision", source=src)
        for i, topic in enumerate(distinct_8, start=1)
    ]
    res_8 = select_meaningful_key_points(eight_pts)
    assert len(res_8) == 8

    # E. 15 distinct important points -> all 15 retained (no arbitrary cap)
    distinct_15 = distinct_8 + [
        "Acoustic wall insulation verified at 55 dB rating.",
        "Elevator shaft alignment certified by elevator contractor.",
        "Emergency generator fuel tank delivery confirmed for Tuesday.",
        "Security card reader hardware approved for all exterior portals.",
        "Fiber optic telecommunications conduit pulled into server room.",
        "Stormwater retention basin excavation completed and inspected.",
        "Paving subcontractor contract executed for main parking area.",
    ]
    fifteen_pts = [
        KeyPointItem(id=f"kp-{i}", point=topic, category="Action", source=src)
        for i, topic in enumerate(distinct_15, start=1)
    ]
    res_15 = select_meaningful_key_points(fifteen_pts)
    assert len(res_15) == 15

    # F. Duplicate points deduplicated
    dup_pts = [
        KeyPointItem(id="kp-1", point="Approved Change Order #05 for structural beams.", category="Decision", source=src),
        KeyPointItem(id="kp-2", point="Approved Change Order #05 for structural beams.", category="Decision", source=src),
        KeyPointItem(id="kp-3", point="approved change order #05 for structural beams", category="Decision", source=src),
        KeyPointItem(id="kp-4", point="Deliver steel framing by Friday 4 PM.", category="Action", source=src),
    ]
    res_dup = select_meaningful_key_points(dup_pts)
    assert len(res_dup) == 2

    # G. Actions/decisions/dates and key points preserved during merge without arbitrary truncation
    r_multi = ShiftlyAnalysisResult(
        id="r-multi",
        title="Large Test Analysis",
        analyzedAt="Now",
        stats=AnalysisStats(messagesAnalyzed=50, keyPointsCount=8, actionsCount=8, decisionsCount=7, importantDatesCount=6),
        summary="Summary of test",
        keyPoints=eight_pts,
        actions=[
            ActionItem(id=f"act-{i}", action=f"Task #{i}", responsiblePerson=f"Person {i}", source=src)
            for i in range(1, 9)
        ],
        decisions=[
            DecisionItem(id=f"dec-{i}", decision=f"Decision #{i}", approvedBy=f"Lead {i}", source=src)
            for i in range(1, 7 + 1)
        ],
        importantDates=[
            ImportantDateItem(id=f"dt-{i}", title=f"Date #{i}", date=f"Oct {i}", significance=f"Milestone {i}", source=src)
            for i in range(1, 6 + 1)
        ],
    )
    merged_res = merge_analysis_results([r_multi])
    assert len(merged_res.keyPoints) == 8
    assert merged_res.stats.keyPointsCount == 8
    # Actions, decisions, dates must remain untruncated
    assert len(merged_res.actions) == 8
    assert merged_res.stats.actionsCount == 8
    assert len(merged_res.decisions) == 7
    assert merged_res.stats.decisionsCount == 7
    assert len(merged_res.importantDates) == 6
    assert merged_res.stats.importantDatesCount == 6


if __name__ == "__main__":
    test_health_endpoint()
    test_analyze_empty_input()
    test_analyze_missing_key_behavior()
    test_chunking_and_normalization()
    test_merge_and_deduplication()
    test_gemini_extraction_pipeline()
    test_key_points_cap_and_selection()
    print("All backend tests passed successfully!")
