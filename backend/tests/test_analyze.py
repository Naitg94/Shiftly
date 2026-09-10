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

client = TestClient(app)

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


if __name__ == "__main__":
    test_health_endpoint()
    test_analyze_empty_input()
    test_analyze_missing_key_behavior()
    test_chunking_and_normalization()
    test_merge_and_deduplication()
    test_gemini_extraction_pipeline()
    print("All backend tests passed successfully!")
