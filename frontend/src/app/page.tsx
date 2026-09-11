'use client';

import { useState } from 'react';
import Link from 'next/link';
import Navbar from '@/components/Navbar';
import InputSection from '@/components/InputSection';
import ProcessingState from '@/components/ProcessingState';
import ResultsDashboard from '@/components/ResultsDashboard';
import ProjectMemory from '@/components/ProjectMemory';
import { MOCK_ANALYSIS_RESULT } from '@/data/mockData';
import { ShiftlyAnalysisResult } from '@/types/analysis';
import { Layers, Database, Sparkles, X } from 'lucide-react';
import { useAuth } from '@/context/AuthContext';
import { analyzeText, analyzeFile, ApiError } from '@/lib/api';

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
  const { user } = useAuth();

  const [mainTab, setMainTab] = useState<MainTab>('analyze');
  const [stage, setStage] = useState<AppStage>('input');
  const [inputText, setInputText] = useState('');
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [activeTab, setActiveTab] = useState<'paste' | 'upload'>('paste');
  const [analysisResult, setAnalysisResult] = useState<ShiftlyAnalysisResult>(EMPTY_ANALYSIS_RESULT);
  const [isApiDone, setIsApiDone] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [isGuestOversizedError, setIsGuestOversizedError] = useState(false);
  const [showGuestMemoryModal, setShowGuestMemoryModal] = useState(false);

  // Memory view states
  const [isViewingMemoryResult, setIsViewingMemoryResult] = useState(false);

  const handleStartAnalysis = async () => {
    setErrorMessage(null);
    setIsGuestOversizedError(false);
    setIsApiDone(false);
    // Immediately clear previous analysis state to prevent stale results on failure
    setAnalysisResult(EMPTY_ANALYSIS_RESULT);
    setStage('processing');

    try {
      let data: ShiftlyAnalysisResult;
      if (activeTab === 'upload') {
        if (!selectedFile) {
          throw new Error('Please select a file to analyze.');
        }
        data = await analyzeFile(selectedFile);
      } else {
        if (!inputText.trim()) {
          throw new Error('Please paste a conversation to analyze.');
        }
        data = await analyzeText(inputText);
      }

      setAnalysisResult(data);
      setIsApiDone(true);
    } catch (err: unknown) {
      let msg = 'Failed to connect to Shiftly API service. Please try again.';
      let isGuestOversized = false;
      if (err instanceof ApiError) {
        if (err.status === 413) {
          msg = err.message || 'Input exceeds the maximum allowed size.';
          if (!user || err.message.toLowerCase().includes('guest')) {
            isGuestOversized = true;
          }
        } else if (err.status === 401) {
          msg = 'Your session has expired. Please sign in again to continue.';
        } else if (err.status === 429) {
          msg = err.message || 'Rate limit reached. Please wait a moment before trying again.';
        } else if (err.status === 504) {
          msg = err.message || 'Analysis request timed out. Please try again or analyze a shorter segment.';
        } else if (err.status >= 500) {
          msg = 'Service is temporarily unavailable. Please try again shortly.';
        } else {
          msg = err.message;
        }
      } else if (err instanceof Error) {
        msg = err.message;
      }
      setErrorMessage(msg);
      setIsGuestOversizedError(isGuestOversized);
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
    setIsGuestOversizedError(false);
    setIsApiDone(false);
    setIsViewingMemoryResult(false);
    setAnalysisResult(EMPTY_ANALYSIS_RESULT);
  };

  const handleUseDemoPreset = () => {
    setAnalysisResult(MOCK_ANALYSIS_RESULT);
    setErrorMessage(null);
    setIsGuestOversizedError(false);
    setStage('results');
  };

  const handleTabChange = (tab: MainTab) => {
    if (tab === 'memory' && !user) {
      setShowGuestMemoryModal(true);
      return;
    }
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
                isGuestOversized={isGuestOversizedError}
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

      {/* Guest Project Memory Modal */}
      {showGuestMemoryModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/80 backdrop-blur-sm animate-in fade-in duration-200">
          <div className="w-full max-w-md rounded-2xl border border-slate-800 bg-slate-900 shadow-2xl p-6 sm:p-7 space-y-5 animate-in zoom-in-95 duration-150">
            <div className="flex items-center justify-between border-b border-slate-800 pb-3">
              <div className="flex items-center gap-2">
                <div className="h-8 w-8 rounded-xl bg-blue-600/10 border border-blue-500/20 flex items-center justify-center text-blue-400">
                  <Database className="h-4 w-4" />
                </div>
                <h3 className="text-base font-bold text-white">Project Memory</h3>
              </div>
              <button
                onClick={() => setShowGuestMemoryModal(false)}
                className="p-1 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800 transition-colors"
                aria-label="Close modal"
              >
                <X className="h-4 w-4" />
              </button>
            </div>

            <div className="space-y-3 text-sm text-slate-300">
              <p className="leading-relaxed">
                Project Memory is an authenticated capability that preserves extracted intelligence across your projects.
              </p>
              <div className="rounded-xl border border-slate-800 bg-slate-950/60 p-3.5 space-y-2 text-xs text-slate-400">
                <div className="flex items-center gap-2 text-slate-300 font-medium">
                  <Sparkles className="h-3.5 w-3.5 text-blue-400" />
                  <span>With Project Memory:</span>
                </div>
                <ul className="space-y-1.5 list-disc list-inside text-slate-400 pl-1">
                  <li>Organize analyses into persistent project workspaces</li>
                  <li>Search across all discussions and decisions</li>
                  <li>Recall past meeting actions and approvals</li>
                </ul>
              </div>
            </div>

            <div className="flex flex-col sm:flex-row items-stretch sm:items-center justify-end gap-2.5 pt-2 border-t border-slate-800">
              <button
                onClick={() => setShowGuestMemoryModal(false)}
                className="px-4 py-2 rounded-xl text-xs font-medium text-slate-400 hover:text-slate-200 hover:bg-slate-800 transition-colors cursor-pointer"
              >
                Continue as Guest
              </button>
              <Link
                href="/login"
                className="px-4 py-2 rounded-xl text-xs font-semibold border border-slate-700 bg-slate-800 text-slate-200 hover:bg-slate-700 text-center transition-colors cursor-pointer"
              >
                Log In
              </Link>
              <Link
                href="/signup"
                className="px-4 py-2 rounded-xl text-xs font-semibold bg-blue-600 hover:bg-blue-500 text-white shadow-sm shadow-blue-500/20 text-center transition-colors cursor-pointer"
              >
                Create Free Account
              </Link>
            </div>
          </div>
        </div>
      )}

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
