from typing import List, Optional, Literal
from pydantic import BaseModel, Field, field_validator


class SourceReference(BaseModel):
    id: str = Field(..., description="Unique identifier for the source citation, e.g. src-1")
    sourceType: Literal["Chat Export", "Email Thread", "Meeting Transcript", "Document"] = Field(
        default="Chat Export",
        description="Type of source communication"
    )
    sourceName: str = Field(..., description="Name or title of thread/channel/document")
    date: str = Field(..., description="Timestamp or date of the source message")
    sender: str = Field(..., description="Sender or participant who authored the statement")
    messageRef: str = Field(..., description="Identifier or reference, e.g. Message #4 or Line 22")
    excerpt: str = Field(..., description="Exact concise quote or sentence from the source text")


class KeyPointItem(BaseModel):
    id: str = Field(..., description="Unique identifier, e.g. kp-1")
    point: str = Field(..., description="Concise statement of key information or factual update")
    category: Optional[str] = Field(default=None, description="Topic category, e.g. Commercial, Structural, Logistics")
    source: SourceReference = Field(..., description="Citation linking directly to source conversation")


class ActionItem(BaseModel):
    id: str = Field(..., description="Unique identifier, e.g. act-1")
    action: str = Field(..., description="Specific committed task or action to be completed")
    responsiblePerson: str = Field(..., description="Name of person assigned, or 'Unassigned' if none")
    deadline: Optional[str] = Field(default=None, description="Explicit due date/time if stated in conversation, else null")
    priority: Optional[Literal["High", "Normal", "Low"]] = Field(default="Normal", description="Inferred priority based on urgency words")
    source: SourceReference = Field(..., description="Citation linking to source message")


class DecisionItem(BaseModel):
    id: str = Field(..., description="Unique identifier, e.g. dec-1")
    decision: str = Field(..., description="Concrete decision or approval that was finalized")
    approvedBy: str = Field(..., description="Person or party who approved or agreed")
    date: Optional[str] = Field(default=None, description="Date decision was made if stated")
    source: SourceReference = Field(..., description="Citation linking to source message")


class ImportantDateItem(BaseModel):
    id: str = Field(..., description="Unique identifier, e.g. dt-1")
    title: str = Field(..., description="Name of the milestone, event, or deadline")
    date: str = Field(..., description="Specific date or timeframe mentioned")
    significance: str = Field(..., description="Why this date matters to the project")
    source: SourceReference = Field(..., description="Citation linking to source message")


class AnalysisStats(BaseModel):
    messagesAnalyzed: int = Field(default=0, description="Estimated count of messages or communication units analyzed")
    participantsCount: int = Field(default=0, description="Count of distinct participants identified")
    keyPointsCount: int = Field(default=0, description="Number of key points extracted")
    actionsCount: int = Field(default=0, description="Number of action items extracted")
    decisionsCount: int = Field(default=0, description="Number of decisions extracted")
    importantDatesCount: int = Field(default=0, description="Number of important dates extracted")


class ShiftlyAnalysisResult(BaseModel):
    id: str = Field(..., description="Unique ID for this analysis run")
    title: str = Field(..., description="Concise project title or topic inferred from communication")
    analyzedAt: str = Field(..., description="Formatted date and time of analysis")
    stats: AnalysisStats = Field(..., description="Summary counts and metrics")
    summary: str = Field(..., description="High-level executive summary paragraph (2-4 sentences)")
    keyPoints: List[KeyPointItem] = Field(default_factory=list, description="List of key points")
    actions: List[ActionItem] = Field(default_factory=list, description="List of action items")
    decisions: List[DecisionItem] = Field(default_factory=list, description="List of decisions and approvals")
    importantDates: List[ImportantDateItem] = Field(default_factory=list, description="List of milestone dates")


class AnalyzeRequest(BaseModel):
    text: str = Field(
        ...,
        min_length=1,
        max_length=200_000,
        description="Raw text of the conversation, chat, email thread, or transcript",
    )

