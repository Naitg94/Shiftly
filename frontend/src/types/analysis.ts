export interface SourceReference {
  id: string;
  sourceType: "Chat Export" | "Email Thread" | "Meeting Transcript" | "Document";
  sourceName: string;
  date: string;
  sender: string;
  messageRef: string;
  excerpt: string;
}

export interface KeyPointItem {
  id: string;
  point: string;
  category?: string;
  source: SourceReference;
}

export interface ActionItem {
  id: string;
  action: string;
  responsiblePerson: string;
  deadline?: string;
  priority?: "High" | "Normal" | "Low";
  source: SourceReference;
}

export interface DecisionItem {
  id: string;
  decision: string;
  approvedBy: string;
  date?: string;
  source: SourceReference;
}

export interface ImportantDateItem {
  id: string;
  title: string;
  date: string;
  significance: string;
  source: SourceReference;
}

export interface ShiftlyAnalysisResult {
  id: string;
  title: string;
  analyzedAt: string;
  stats: {
    messagesAnalyzed: number;
    participantsCount: number;
    keyPointsCount: number;
    actionsCount: number;
    decisionsCount: number;
    importantDatesCount: number;
  };
  summary: string;
  keyPoints: KeyPointItem[];
  actions: ActionItem[];
  decisions: DecisionItem[];
  importantDates: ImportantDateItem[];
}
