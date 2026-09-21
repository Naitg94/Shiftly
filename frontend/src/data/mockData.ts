import { ShiftlyAnalysisResult } from "@/types/analysis";

export const SAMPLE_CONVERSATION_RAW = `[10/12/2024, 08:34] David Miller (Client): Morning team. Did anyone get a chance to review the revised glazing package from yesterday? We really can't afford to push the envelope installation into November because of rainy season.
[10/12/2024, 08:42] Elena Vance (Lead Architect): Good morning David. Yes, Studio Forma reviewed rev.C. We have a small issue with the acoustic laminate on the north facade — it doesn't meet the city sound ordinance by 2 dB.
[10/12/2024, 08:49] Marcus Brody (General Contractor): Hey all. We had the supplier on the phone this morning. If Elena signs off on the triple-pane alternate (Model AGC-400) by Thursday 4 PM, they can still guarantee delivery by November 3rd. Otherwise lead time extends 4 weeks.
[10/12/2024, 09:05] David Miller (Client): Elena, what's the cost difference on the triple-pane alternate?
[10/12/2024, 09:12] Elena Vance (Lead Architect): It's about $14,200 more across all 3 floors, but it exceeds the energy code and solves the acoustic rating issue completely.
[10/12/2024, 09:18] David Miller (Client): Approved. Let's do it. I'd rather spend the $14.2k than lose a month on schedule. Elena, please issue Change Order #04 today.
[10/12/2024, 09:22] Elena Vance (Lead Architect): Understood. I will draft Change Order #04 and send it to David for formal signature by 5 PM today.
[10/12/2024, 09:45] Marcus Brody (General Contractor): Great. That leaves the foundation slab pour. The concrete batch plant says they're ready for Tuesday Oct 15th, but Sophia Chen hasn't stamped the rebar inspection yet.
[10/12/2024, 10:10] Sophia Chen (Structural Engineer): Just saw this. I was on site yesterday afternoon. Marcus, your crew needs to add two #8 ties on column C-4 before I can sign off. Once that's done, I'll submit the stamped inspection report by Monday Oct 14 at 12:00 PM.
[10/12/2024, 10:15] Marcus Brody (General Contractor): Got it Sophia. I'll have the rebar crew fix C-4 first thing Saturday morning.
[10/12/2024, 10:30] David Miller (Client): What about the municipal permit for the crane erection on Elm Street? Has the road closure notice been published?
[10/12/2024, 11:05] Marcus Brody (General Contractor): The city traffic bureau confirmed receipt. They require a 72-hour public notice. Marcus will submit the traffic control plan and insurance certificate by Friday Oct 18. Crane mobilization is locked in for October 24th.
[10/12/2024, 11:20] Elena Vance (Lead Architect): Note for the interior finishes: David picked the Brushed Nordic Ash veneer for the lobby ceiling during our walkthrough. We are proceeding with that specification.
[10/12/2024, 11:25] David Miller (Client): Yes, confirmed. We loved the grain on that sample.
[10/12/2024, 11:40] Marcus Brody (General Contractor): Thanks team. So to recap, we hold the slab pour date for Oct 15 provided Sophia's sign-off lands Monday noon.
[10/12/2024, 11:42] Sophia Chen (Structural Engineer): Confirmed. See you Monday.`;

export const MOCK_ANALYSIS_RESULT: ShiftlyAnalysisResult = {
  id: "analysis-proj-elm-402",
  title: "Elm St. Commercial Renovation — Coordination Log",
  analyzedAt: "October 12, 2024 • 11:45 AM",
  stats: {
    messagesAnalyzed: 16,
    participantsCount: 4,
    keyPointsCount: 5,
    actionsCount: 4,
    decisionsCount: 3,
    importantDatesCount: 4,
    pendingDecisionsCount: 0,
  },
  summary:
    "The team resolved the envelope glazing delay by upgrading to triple-pane alternate AGC-400 (+ $14.2k) with delivery locked for November 3. Foundation slab pour is scheduled for October 15 pending column C-4 rebar remediation and structural sign-off on October 14. Crane mobilization is targeted for October 24 following municipal traffic filings.",
  keyPoints: [
    {
      id: "kp-1",
      point: "Glazing package revised to triple-pane alternate (Model AGC-400) to meet acoustic ordinances and avoid a 4-week delay.",
      category: "Envelope / Facade",
      source: {
        id: "src-1",
        sourceType: "Chat Export",
        sourceName: "Elm St. Site Coordination Channel",
        date: "Oct 12, 2024 - 08:49 AM",
        sender: "Marcus Brody (General Contractor)",
        messageRef: "Message #3",
        excerpt:
          "If Elena signs off on the triple-pane alternate (Model AGC-400) by Thursday 4 PM, they can still guarantee delivery by November 3rd. Otherwise lead time extends 4 weeks.",
      },
    },
    {
      id: "kp-2",
      point: "Foundation concrete slab pour is contingent on rebar tie additions on column C-4 and engineering sign-off.",
      category: "Structural",
      source: {
        id: "src-2",
        sourceType: "Chat Export",
        sourceName: "Elm St. Site Coordination Channel",
        date: "Oct 12, 2024 - 10:10 AM",
        sender: "Sophia Chen (Structural Engineer)",
        messageRef: "Message #9",
        excerpt:
          "Marcus, your crew needs to add two #8 ties on column C-4 before I can sign off. Once that's done, I'll submit the stamped inspection report by Monday Oct 14 at 12:00 PM.",
      },
    },
    {
      id: "kp-3",
      point: "Elm Street crane mobilization requires a 72-hour municipal notice and traffic management plan filing.",
      category: "Permitting & Site Logistics",
      source: {
        id: "src-3",
        sourceType: "Chat Export",
        sourceName: "Elm St. Site Coordination Channel",
        date: "Oct 12, 2024 - 11:05 AM",
        sender: "Marcus Brody (General Contractor)",
        messageRef: "Message #12",
        excerpt:
          "The city traffic bureau confirmed receipt. They require a 72-hour public notice. Marcus will submit the traffic control plan and insurance certificate by Friday Oct 18.",
      },
    },
    {
      id: "kp-4",
      point: "Client authorized a $14,200 budget increase to prioritize schedule retention and acoustic compliance.",
      category: "Commercial / Budget",
      source: {
        id: "src-4",
        sourceType: "Chat Export",
        sourceName: "Elm St. Site Coordination Channel",
        date: "Oct 12, 2024 - 09:18 AM",
        sender: "David Miller (Client)",
        messageRef: "Message #6",
        excerpt:
          "Approved. Let's do it. I'd rather spend the $14.2k than lose a month on schedule. Elena, please issue Change Order #04 today.",
      },
    },
    {
      id: "kp-5",
      point: "Lobby ceiling finish selected as Brushed Nordic Ash veneer.",
      category: "Finishes",
      source: {
        id: "src-5",
        sourceType: "Chat Export",
        sourceName: "Elm St. Site Coordination Channel",
        date: "Oct 12, 2024 - 11:20 AM",
        sender: "Elena Vance (Lead Architect)",
        messageRef: "Message #13",
        excerpt:
          "David picked the Brushed Nordic Ash veneer for the lobby ceiling during our walkthrough. We are proceeding with that specification.",
      },
    },
  ],
  actions: [
    {
      id: "act-1",
      action: "Draft and transmit Change Order #04 for client execution",
      responsiblePerson: "Elena Vance (Lead Architect)",
      deadline: "Oct 12, 2024 • 5:00 PM",
      priority: "High",
      source: {
        id: "src-act-1",
        sourceType: "Chat Export",
        sourceName: "Elm St. Site Coordination Channel",
        date: "Oct 12, 2024 - 09:22 AM",
        sender: "Elena Vance (Lead Architect)",
        messageRef: "Message #7",
        excerpt:
          "I will draft Change Order #04 and send it to David for formal signature by 5 PM today.",
      },
    },
    {
      id: "act-2",
      action: "Install two #8 ties on column C-4 rebar cage",
      responsiblePerson: "Marcus Brody (General Contractor)",
      deadline: "Oct 13, 2024 (Saturday morning)",
      priority: "High",
      source: {
        id: "src-act-2",
        sourceType: "Chat Export",
        sourceName: "Elm St. Site Coordination Channel",
        date: "Oct 12, 2024 - 10:15 AM",
        sender: "Marcus Brody (General Contractor)",
        messageRef: "Message #10",
        excerpt: "I'll have the rebar crew fix C-4 first thing Saturday morning.",
      },
    },
    {
      id: "act-3",
      action: "Submit stamped foundation rebar inspection report",
      responsiblePerson: "Sophia Chen (Structural Engineer)",
      deadline: "Oct 14, 2024 • 12:00 PM",
      priority: "High",
      source: {
        id: "src-act-3",
        sourceType: "Chat Export",
        sourceName: "Elm St. Site Coordination Channel",
        date: "Oct 12, 2024 - 10:10 AM",
        sender: "Sophia Chen (Structural Engineer)",
        messageRef: "Message #9",
        excerpt: "Once that's done, I'll submit the stamped inspection report by Monday Oct 14 at 12:00 PM.",
      },
    },
    {
      id: "act-4",
      action: "File traffic control plan and insurance certificate with city bureau",
      responsiblePerson: "Marcus Brody (General Contractor)",
      deadline: "Oct 18, 2024",
      priority: "Normal",
      source: {
        id: "src-act-4",
        sourceType: "Chat Export",
        sourceName: "Elm St. Site Coordination Channel",
        date: "Oct 12, 2024 - 11:05 AM",
        sender: "Marcus Brody (General Contractor)",
        messageRef: "Message #12",
        excerpt: "Marcus will submit the traffic control plan and insurance certificate by Friday Oct 18.",
      },
    },
  ],
  decisions: [
    {
      id: "dec-1",
      decision: "Approved $14,200 Change Order #04 for triple-pane glazing alternate (AGC-400)",
      approvedBy: "David Miller (Client)",
      date: "Oct 12, 2024",
      source: {
        id: "src-dec-1",
        sourceType: "Chat Export",
        sourceName: "Elm St. Site Coordination Channel",
        date: "Oct 12, 2024 - 09:18 AM",
        sender: "David Miller (Client)",
        messageRef: "Message #6",
        excerpt:
          "Approved. Let's do it. I'd rather spend the $14.2k than lose a month on schedule. Elena, please issue Change Order #04 today.",
      },
    },
    {
      id: "dec-2",
      decision: "Confirmed foundation slab pour will proceed on Tuesday Oct 15 pending Monday engineering sign-off",
      approvedBy: "Marcus Brody & Sophia Chen",
      date: "Oct 12, 2024",
      source: {
        id: "src-dec-2",
        sourceType: "Chat Export",
        sourceName: "Elm St. Site Coordination Channel",
        date: "Oct 12, 2024 - 11:40 AM",
        sender: "Marcus Brody (General Contractor)",
        messageRef: "Message #15",
        excerpt:
          "So to recap, we hold the slab pour date for Oct 15 provided Sophia's sign-off lands Monday noon.",
      },
    },
    {
      id: "dec-3",
      decision: "Selected Brushed Nordic Ash veneer specification for lobby ceiling",
      approvedBy: "David Miller (Client)",
      date: "Oct 12, 2024",
      source: {
        id: "src-dec-3",
        sourceType: "Chat Export",
        sourceName: "Elm St. Site Coordination Channel",
        date: "Oct 12, 2024 - 11:25 AM",
        sender: "David Miller (Client)",
        messageRef: "Message #14",
        excerpt: "Yes, confirmed. We loved the grain on that sample.",
      },
    },
  ],
  importantDates: [
    {
      id: "dt-1",
      title: "Stamped Rebar Inspection Submission",
      date: "Oct 14, 2024 • 12:00 PM",
      significance: "Prerequisite milestone before batch plant delivers concrete for foundation",
      source: {
        id: "src-dt-1",
        sourceType: "Chat Export",
        sourceName: "Elm St. Site Coordination Channel",
        date: "Oct 12, 2024 - 10:10 AM",
        sender: "Sophia Chen (Structural Engineer)",
        messageRef: "Message #9",
        excerpt: "Once that's done, I'll submit the stamped inspection report by Monday Oct 14 at 12:00 PM.",
      },
    },
    {
      id: "dt-2",
      title: "Foundation Slab Pour",
      date: "Oct 15, 2024",
      significance: "Critical path concrete pour across ground-level footprint",
      source: {
        id: "src-dt-2",
        sourceType: "Chat Export",
        sourceName: "Elm St. Site Coordination Channel",
        date: "Oct 12, 2024 - 09:45 AM",
        sender: "Marcus Brody (General Contractor)",
        messageRef: "Message #8",
        excerpt: "The concrete batch plant says they're ready for Tuesday Oct 15th, but Sophia Chen hasn't stamped the rebar inspection yet.",
      },
    },
    {
      id: "dt-3",
      title: "Traffic Control Plan Filing Deadline",
      date: "Oct 18, 2024",
      significance: "Required to satisfy city 72-hour public notice ahead of street closure",
      source: {
        id: "src-dt-3",
        sourceType: "Chat Export",
        sourceName: "Elm St. Site Coordination Channel",
        date: "Oct 12, 2024 - 11:05 AM",
        sender: "Marcus Brody (General Contractor)",
        messageRef: "Message #12",
        excerpt: "Marcus will submit the traffic control plan and insurance certificate by Friday Oct 18.",
      },
    },
    {
      id: "dt-4",
      title: "Elm Street Crane Mobilization",
      date: "Oct 24, 2024",
      significance: "Heavy rigging equipment arrives on site for exterior envelope erection",
      source: {
        id: "src-dt-4",
        sourceType: "Chat Export",
        sourceName: "Elm St. Site Coordination Channel",
        date: "Oct 12, 2024 - 11:05 AM",
        sender: "Marcus Brody (General Contractor)",
        messageRef: "Message #12",
        excerpt: "Crane mobilization is locked in for October 24th.",
      },
    },
  ],
  pendingDecisions: [],
};
