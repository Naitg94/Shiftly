import os
import pytest

os.environ["TEST_USE_SQLITE"] = "true"

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
from app.services.chunking_service import (
    resolve_decision_lifecycle,
    filter_spurious_approvals,
    deduplicate_important_dates,
    merge_analysis_results,
)

SRC_1 = SourceReference(
    id="src-iq-1",
    sourceType="Chat Export",
    sourceName="#riverside-project",
    date="Oct 12, 2024",
    sender="Marcus Chen",
    messageRef="Msg #10",
    excerpt="Branding team hasn't confirmed the signage wording yet.",
)

SRC_2 = SourceReference(
    id="src-iq-2",
    sourceType="Chat Export",
    sourceName="#riverside-project",
    date="Oct 12, 2024",
    sender="Elena Rostova",
    messageRef="Msg #35",
    excerpt="Branding confirmed: wording will be 'Riverside Technology Group'.",
)

SRC_3 = SourceReference(
    id="src-iq-3",
    sourceType="Chat Export",
    sourceName="#riverside-project",
    date="Oct 12, 2024",
    sender="Tom Davis",
    messageRef="Msg #40",
    excerpt="Coffee approved for tomorrow's team sync!",
)

SRC_4 = SourceReference(
    id="src-iq-4",
    sourceType="Chat Export",
    sourceName="#riverside-project",
    date="Oct 12, 2024",
    sender="Sarah Connor",
    messageRef="Msg #55",
    excerpt="VP Finance approved the Q4 infrastructure budget of $450k.",
)


def test_decision_lifecycle_resolution():
    """Verify that when an earlier pending decision is resolved later by a decision,
    the pending decision is removed and the decision takes precedence."""
    pending = [
        PendingDecisionItem(
            id="pd-1",
            decision="Signage wording confirmation from branding team",
            source=SRC_1,
        ),
        PendingDecisionItem(
            id="pd-2",
            decision="Awaiting confirmation on HVAC unit selection",
            source=SRC_1,
        ),
    ]

    decisions = [
        DecisionItem(
            id="dec-1",
            decision="Confirmed signage wording: Riverside Technology Group",
            approvedBy="Elena Rostova",
            date="Oct 12",
            source=SRC_2,
        )
    ]

    filtered_pending = resolve_decision_lifecycle(decisions, pending)

    # pd-1 matches "signage wording" in dec-1, so pd-1 must be removed
    assert len(filtered_pending) == 1
    assert filtered_pending[0].id == "pd-2"
    assert "HVAC" in filtered_pending[0].decision


def test_filter_spurious_approvals():
    """Verify that casual banter ('Coffee approved', 'Lunch approved') is strictly filtered out."""
    decisions = [
        DecisionItem(
            id="dec-c1",
            decision="Coffee approved for tomorrow's team sync",
            approvedBy="Tom Davis",
            source=SRC_3,
        ),
        DecisionItem(
            id="dec-c2",
            decision="Lunch order approved from Chipotle",
            approvedBy="Sarah",
            source=SRC_3,
        ),
        DecisionItem(
            id="dec-c3",
            decision="Pizza approved for lunch break",
            approvedBy="Team",
            source=SRC_3,
        ),
        DecisionItem(
            id="dec-c4",
            decision="Approval pending for exterior lighting",
            approvedBy="Unknown",
            source=SRC_3,
        ),
        DecisionItem(
            id="dec-legit-1",
            decision="VP Finance approved the Q4 infrastructure budget of $450k",
            approvedBy="VP Finance",
            source=SRC_4,
        ),
        DecisionItem(
            id="dec-legit-2",
            decision="Selected Italian porcelain tile for the lobby flooring",
            approvedBy="Marcus Chen",
            source=SRC_1,
        ),
    ]

    clean_decisions = filter_spurious_approvals(decisions)

    # All 4 spurious items must be filtered out; 2 legitimate items remain
    assert len(clean_decisions) == 2
    assert any("budget" in d.decision.lower() for d in clean_decisions)
    assert any("porcelain tile" in d.decision.lower() for d in clean_decisions)


def test_semantic_date_deduplication():
    """Verify that duplicate/near-duplicate milestone dates for the same event are deduplicated."""
    dates = [
        ImportantDateItem(
            id="dt-1",
            title="Final Project Submission Target",
            date="September 20, 2024",
            significance="Final delivery of project deliverables",
            source=SRC_1,
        ),
        ImportantDateItem(
            id="dt-2",
            title="Final Project Submission Date",
            date="September 20, 2024",
            significance="Submission deadline for all team artifacts",
            source=SRC_2,
        ),
        ImportantDateItem(
            id="dt-3",
            title="Client Kickoff Meeting",
            date="October 1, 2024",
            significance="Initial alignment with client stakeholders",
            source=SRC_4,
        ),
    ]

    deduped = deduplicate_important_dates(dates)

    # dt-1 and dt-2 refer to the same milestone on September 20, 2024
    assert len(deduped) == 2
    date_strs = [d.date for d in deduped]
    assert "September 20, 2024" in date_strs
    assert "October 1, 2024" in date_strs


def test_merge_analysis_results_full_pipeline():
    """Verify that merge_analysis_results applies lifecycle resolution, approval filtering,
    and date deduplication end-to-end."""
    r1 = ShiftlyAnalysisResult(
        id="chunk-1",
        title="Riverside Project Review Part 1",
        analyzedAt="Now",
        stats=AnalysisStats(
            messagesAnalyzed=20,
            pendingDecisionsCount=1,
            decisionsCount=2,
            importantDatesCount=1,
        ),
        summary="Summary chunk 1",
        keyPoints=[
            KeyPointItem(
                id="kp-1",
                point="Entrance layout under consideration is Revision B",
                source=SRC_1,
            )
        ],
        actions=[
            ActionItem(
                id="act-1",
                action="Review entrance layout Revision B",
                responsiblePerson="Marcus Chen",
                deadline="Oct 15",
                source=SRC_1,
            )
        ],
        decisions=[
            DecisionItem(
                id="dec-spurious",
                decision="Coffee approved for morning standup",
                approvedBy="Tom Davis",
                source=SRC_3,
            ),
            DecisionItem(
                id="dec-legit-1",
                decision="Selected Italian porcelain tile for lobby flooring",
                approvedBy="Marcus Chen",
                source=SRC_1,
            ),
        ],
        importantDates=[
            ImportantDateItem(
                id="dt-1",
                title="Project Submission Target",
                date="September 20, 2024",
                significance="Submission target",
                source=SRC_1,
            )
        ],
        pendingDecisions=[
            PendingDecisionItem(
                id="pd-1",
                decision="Signage wording confirmation from branding team",
                source=SRC_1,
            )
        ],
    )

    r2 = ShiftlyAnalysisResult(
        id="chunk-2",
        title="Riverside Project Review Part 2",
        analyzedAt="Now",
        stats=AnalysisStats(
            messagesAnalyzed=25,
            pendingDecisionsCount=0,
            decisionsCount=1,
            importantDatesCount=1,
        ),
        summary="Summary chunk 2",
        keyPoints=[
            KeyPointItem(
                id="kp-2",
                point="Finalized entrance layout updated to Revision C per client sign-off",
                source=SRC_2,
            )
        ],
        actions=[
            ActionItem(
                id="act-2",
                action="Prepare architectural drawings for Revision C",
                responsiblePerson="Marcus Chen",
                deadline="Oct 20",
                source=SRC_2,
            )
        ],
        decisions=[
            DecisionItem(
                id="dec-legit-2",
                decision="Confirmed signage wording: Riverside Technology Group",
                approvedBy="Elena Rostova",
                source=SRC_2,
            )
        ],
        importantDates=[
            ImportantDateItem(
                id="dt-2",
                title="Final Project Submission Date",
                date="September 20, 2024",
                significance="Hard deadline",
                source=SRC_2,
            )
        ],
        pendingDecisions=[],
    )

    merged = merge_analysis_results([r1, r2])

    # 1. Spurious coffee decision removed
    assert not any("coffee" in d.decision.lower() for d in merged.decisions)

    # 2. Legitimate decisions preserved
    assert any("porcelain tile" in d.decision.lower() for d in merged.decisions)
    assert any("signage wording" in d.decision.lower() for d in merged.decisions)

    # 3. Decision lifecycle: pd-1 was resolved by dec-legit-2, so pendingDecisions must be empty!
    assert len(merged.pendingDecisions) == 0
    assert merged.stats.pendingDecisionsCount == 0

    # 4. Dates deduplicated from 2 down to 1
    assert len(merged.importantDates) == 1
    assert merged.stats.importantDatesCount == 1
    assert merged.importantDates[0].date == "September 20, 2024"
