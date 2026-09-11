"use client";

import { useState } from "react";
import Navbar from "@/components/Navbar";
import InputSection from "@/components/InputSection";
import ProcessingState from "@/components/ProcessingState";
import ResultsDashboard from "@/components/ResultsDashboard";
import ProjectMemory from "@/components/ProjectMemory";
import { MOCK_ANALYSIS_RESULT } from "@/data/mockData";
import { ShiftlyAnalysisResult } from "@/types/analysis";
import { Layers } from "lucide-react";

type AppStage = "input" | "processing" | "results";
type MainTab = "analyze" | "memory";

const EMPTY_ANALYSIS_RESULT: ShiftlyAnalysisResult = {
  id: "",
  title: "Untitled Analysis",
  analyzedAt: "",
  stats: {
    messagesAnalyzed: 0,
    participantsCount: 0,
    keyPointsCount: 0,
    actionsCount: 0,
    decisionsCount: 0,
    importantDatesCount: 0,
  },
  summary: "",
  keyPoints: [],
  actions: [],
  decisions: [],
  importantDates: [],
};

export default function Home() {
  const [mainTab, setMainTab] = useState<MainTab>("analyze");
  const [stage, setStage] = useState<AppStage>("input");
  const [inputText, setInputText] = useState("");
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [activeTab, setActiveTab] = useState<"paste" | "upload">("paste");
  const [analysisResult, setAnalysisResult] = useState<ShiftlyAnalysisResult>(EMPTY_ANALYSIS_RESULT);
  const [isApiDone, setIsApiDone] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  // Memory view states
  const [isViewingMemoryResult, setIsViewingMemoryResult] = useState(false);

  const handleStartAnalysis = async () => {
    setErrorMessage(null);
    setIsApiDone(false);
    setStage("processing");

    const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

    try {
      let response: Response;

      if (activeTab === "upload") {
        if (!selectedFile) {
          throw new Error("Please select a file to analyze.");
        }
        const formData = new FormData();
        formData.append("file", selectedFile);

        response = await fetch(`${apiUrl}/api/analyze/file`, {
          method: "POST",
          body: formData,
        });
      } else {
        if (!inputText.trim()) {
          throw new Error("Please paste a conversation to analyze.");
        }
        response = await fetch(`${apiUrl}/api/analyze`, {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({ text: inputText }),
        });
      }

      if (!response.ok) {
        let detail = `Error ${response.status}: ${response.statusText}`;
        try {
          const errJson = await response.json();
          if (errJson.detail) {
            detail = errJson.detail;
          }
        } catch {
          // fallback
        }
        throw new Error(detail);
      }

      const data: ShiftlyAnalysisResult = await response.json();
      setAnalysisResult(data);
      setIsApiDone(true);
    } catch (err: unknown) {
      const msg =
        err instanceof Error
          ? err.message
          : "Failed to connect to Shiftly backend server at http://localhost:8000";
      setErrorMessage(msg);
      setStage("input");
      setIsApiDone(false);
    }
  };

  const handleProcessingComplete = () => {
    setStage("results");
  };

  const handleReset = () => {
    setStage("input");
    setInputText("");
    setSelectedFile(null);
    setErrorMessage(null);
    setIsApiDone(false);
    setIsViewingMemoryResult(false);
    setAnalysisResult(EMPTY_ANALYSIS_RESULT);
  };

  const handleUseDemoPreset = () => {
    setAnalysisResult(MOCK_ANALYSIS_RESULT);
    setErrorMessage(null);
    setStage("results");
  };

  const handleTabChange = (tab: MainTab) => {
    setMainTab(tab);
    if (tab === "analyze") {
      setIsViewingMemoryResult(false);
    }
  };

  const handleLoadMemoryAnalysis = (loaded: ShiftlyAnalysisResult) => {
    setAnalysisResult(loaded);
    setIsViewingMemoryResult(true);
  };

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col font-sans selection:bg-blue-600 selection:text-white">
      {/* SaaS Navigation */}
      <Navbar
        activeTab={mainTab}
        onTabChange={handleTabChange}
        onReset={handleReset}
      />

      {/* Main Content Body */}
      <main className="flex-1 w-full max-w-6xl mx-auto px-4 sm:px-6 py-6 sm:py-10 flex flex-col justify-start">
        {mainTab === "analyze" ? (
          <>
            {stage === "input" && (
              <InputSection
                inputText={inputText}
                setInputText={setInputText}
                selectedFile={selectedFile}
                setSelectedFile={setSelectedFile}
                activeTab={activeTab}
                setActiveTab={setActiveTab}
                onAnalyze={handleStartAnalysis}
                errorMessage={errorMessage}
                onUseDemoPreset={handleUseDemoPreset}
              />
            )}

            {stage === "processing" && (
              <ProcessingState
                isDone={isApiDone}
                onComplete={handleProcessingComplete}
              />
            )}

            {stage === "results" && (
              <ResultsDashboard
                result={analysisResult}
                onReset={handleReset}
              />
            )}
          </>
        ) : (
          <>
            {isViewingMemoryResult ? (
              <ResultsDashboard
                result={analysisResult}
                onReset={handleReset}
                isFromMemory={true}
                onBackToMemory={() => setIsViewingMemoryResult(false)}
              />
            ) : (
              <ProjectMemory
                onLoadAnalysis={handleLoadMemoryAnalysis}
              />
            )}
          </>
        )}
      </main>

      {/* Minimal Footer */}
      <footer className="w-full border-t border-slate-900 bg-slate-950/50 py-6 text-xs text-slate-500">
        <div className="mx-auto max-w-6xl px-4 sm:px-6 flex flex-col sm:flex-row items-center justify-between gap-3">
          <div className="flex items-center gap-2">
            <span className="font-semibold text-slate-300">Shiftly</span>
            <span>—</span>
            <span>Find what matters.</span>
          </div>
          <div className="flex items-center gap-1 text-[11px] text-slate-500">
            <Layers className="h-3 w-3 text-slate-500" />
            <span>Communication Intelligence Layer</span>
          </div>
        </div>
      </footer>
    </div>
  );
}
