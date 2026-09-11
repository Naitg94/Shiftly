'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import Navbar from '@/components/Navbar';
import InputSection from '@/components/InputSection';
import ProcessingState from '@/components/ProcessingState';
import ResultsDashboard from '@/components/ResultsDashboard';
import ProjectMemory from '@/components/ProjectMemory';
import { MOCK_ANALYSIS_RESULT } from '@/data/mockData';
import { ShiftlyAnalysisResult } from '@/types/analysis';
import { Layers, Loader2 } from 'lucide-react';
import { useAuth } from '@/context/AuthContext';
import { supabase } from '@/lib/supabaseClient';

type AppStage = 'input' | 'processing' | 'results';
type MainTab = 'analyze' | 'memory';

const EMPTY_ANALYSIS_RESULT: ShiftlyAnalysisResult = {
  id: '',
  title: 'Untitled Analysis',
  analyzedAt: '',
  stats: {
    messagesAnalyzed: 0,
    participantsCount: 0,
    keyPointsCount: 0,
    actionsCount: 0,
    decisionsCount: 0,
    importantDatesCount: 0,
  },
  summary: '',
  keyPoints: [],
  actions: [],
  decisions: [],
  importantDates: [],
};

export default function Home() {
  const router = useRouter();
  const { user, isLoading: isAuthLoading } = useAuth();

  const [mainTab, setMainTab] = useState<MainTab>('analyze');
  const [stage, setStage] = useState<AppStage>('input');
  const [inputText, setInputText] = useState('');
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [activeTab, setActiveTab] = useState<'paste' | 'upload'>('paste');
  const [analysisResult, setAnalysisResult] = useState<ShiftlyAnalysisResult>(EMPTY_ANALYSIS_RESULT);
  const [isApiDone, setIsApiDone] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  // Memory view states
  const [isViewingMemoryResult, setIsViewingMemoryResult] = useState(false);

  // Route protection guard
  useEffect(() => {
    if (!isAuthLoading && !user) {
      router.replace('/login');
    }
  }, [user, isAuthLoading, router]);

  if (isAuthLoading || !user) {
    return (
      <div className="min-h-screen bg-slate-950 flex flex-col items-center justify-center space-y-3">
        <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-blue-600 text-white font-bold text-xl shadow-lg shadow-blue-500/20">
          S
        </div>
        <div className="flex items-center gap-2 text-xs text-slate-400">
          <Loader2 className="h-4 w-4 animate-spin text-blue-500" />
          <span>Restoring session...</span>
        </div>
      </div>
    );
  }

  const handleStartAnalysis = async () => {
    setErrorMessage(null);
    setIsApiDone(false);
    // Immediately clear previous analysis state to prevent stale results on failure
    setAnalysisResult(EMPTY_ANALYSIS_RESULT);
    setStage('processing');

    const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

    try {
      // Get current auth token
      const { data: sessionData } = await supabase.auth.getSession();
      const token = sessionData.session?.access_token;
      const authHeader: Record<string, string> = token
        ? { Authorization: `Bearer ${token}` }
        : {};

      let response: Response;

      if (activeTab === 'upload') {
        if (!selectedFile) {
          throw new Error('Please select a file to analyze.');
        }
        const formData = new FormData();
        formData.append('file', selectedFile);

        response = await fetch(`${apiUrl}/api/analyze/file`, {
          method: 'POST',
          headers: {
            ...authHeader,
          },
          body: formData,
        });
      } else {
        if (!inputText.trim()) {
          throw new Error('Please paste a conversation to analyze.');
        }
        response = await fetch(`${apiUrl}/api/analyze`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            ...authHeader,
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

        if (response.status === 401) {
          detail = 'Your session has expired. Please sign in again to continue.';
        } else if (response.status === 429) {
          detail = detail || 'Rate limit reached. Please wait a moment before trying again.';
        } else if (response.status === 504) {
          detail = detail || 'Analysis request timed out. Please try again or analyze a shorter segment.';
        } else if (response.status >= 500) {
          detail = detail || 'Service is temporarily unavailable. Please try again shortly.';
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
          : 'Failed to connect to Shiftly backend server at http://localhost:8000';
      setErrorMessage(msg);
      setAnalysisResult(EMPTY_ANALYSIS_RESULT);
      setStage('input');
      setIsApiDone(false);
    }
  };

  const handleProcessingComplete = () => {
    setStage('results');
  };

  const handleReset = () => {
    setStage('input');
    setInputText('');
    setSelectedFile(null);
    setErrorMessage(null);
    setIsApiDone(false);
    setIsViewingMemoryResult(false);
    setAnalysisResult(EMPTY_ANALYSIS_RESULT);
  };

  const handleUseDemoPreset = () => {
    setAnalysisResult(MOCK_ANALYSIS_RESULT);
    setErrorMessage(null);
    setStage('results');
  };

  const handleTabChange = (tab: MainTab) => {
    setMainTab(tab);
    if (tab === 'analyze') {
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
        {mainTab === 'analyze' ? (
          <>
            {stage === 'input' && (
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

            {stage === 'processing' && (
              <ProcessingState
                isDone={isApiDone}
                onComplete={handleProcessingComplete}
              />
            )}

            {stage === 'results' && (
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
