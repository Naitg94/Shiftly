"use client";

import { useState, useEffect } from "react";
import {
  ShiftlyAnalysisResult,
  SourceReference,
} from "@/types/analysis";
import {
  ListChecks,
  FileText,
  Table,
  LayoutGrid,
  RotateCcw,
  MessageSquare,
  Sparkles,
  Calendar,
  Gavel,
  CheckSquare,
  Bookmark,
  Check,
  Loader2,
  FolderPlus,
  AlertCircle,
  X,
  ArrowLeft,
  Plus,
} from "lucide-react";
import KeyPointsView from "./views/KeyPointsView";
import SummaryView from "./views/SummaryView";
import TableView from "./views/TableView";
import StructuredView from "./views/StructuredView";
import SourceModal from "./SourceModal";
import Link from "next/link";
import { Project } from "@/types/project";
import { fetchProjects, createProject, saveAnalysisToProject, ApiError } from "@/lib/api";
import { useAuth } from "@/context/AuthContext";

interface ResultsDashboardProps {
  result: ShiftlyAnalysisResult;
  onReset: () => void;
  onBackToMemory?: () => void;
  isFromMemory?: boolean;
}

type ViewMode = "keypoints" | "summary" | "table" | "structured";

export default function ResultsDashboard({
  result,
  onReset,
  onBackToMemory,
  isFromMemory = false,
}: ResultsDashboardProps) {
  const { user } = useAuth();
  const [activeView, setActiveView] = useState<ViewMode>("keypoints");
  const [selectedSource, setSelectedSource] = useState<SourceReference | null>(null);

  // Save to Project State
  const [isSaveModalOpen, setIsSaveModalOpen] = useState(false);
  const [isGuestSaveModalOpen, setIsGuestSaveModalOpen] = useState(false);
  const [projects, setProjects] = useState<Project[]>([]);
  const [selectedProjectId, setSelectedProjectId] = useState<string>("");
  const [isLoadingProjects, setIsLoadingProjects] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const [saveSuccess, setSaveSuccess] = useState<string | null>(null);
  const [saveError, setSaveError] = useState<string | null>(null);

  // Inline new project creation inside modal
  const [showNewProjectInput, setShowNewProjectInput] = useState(false);
  const [newProjectName, setNewProjectName] = useState("");
  const [isCreatingProject, setIsCreatingProject] = useState(false);

  // Close save modal on Escape key
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        if (isSaveModalOpen) setIsSaveModalOpen(false);
        if (isGuestSaveModalOpen) setIsGuestSaveModalOpen(false);
      }
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [isSaveModalOpen, isGuestSaveModalOpen]);

  const tabs: { id: ViewMode; label: string; icon: React.ReactNode }[] = [
    { id: "keypoints", label: "Key Points", icon: <ListChecks className="h-4 w-4" /> },
    { id: "summary", label: "Summary", icon: <FileText className="h-4 w-4" /> },
    { id: "table", label: "Table", icon: <Table className="h-4 w-4" /> },
    { id: "structured", label: "Structured", icon: <LayoutGrid className="h-4 w-4" /> },
  ];

  const handleSaveClick = () => {
    if (!user) {
      setIsGuestSaveModalOpen(true);
      return;
    }
    handleOpenSaveModal();
  };

  const handleOpenSaveModal = async () => {
    setIsSaveModalOpen(true);
    setSaveSuccess(null);
    setSaveError(null);
    setIsLoadingProjects(true);
    try {
      const data = await fetchProjects();
      setProjects(data);
      if (data.length > 0 && !selectedProjectId) {
        setSelectedProjectId(data[0].id);
      }
    } catch {
      setSaveError("Failed to fetch projects list");
    } finally {
      setIsLoadingProjects(false);
    }
  };

  const handleCreateProjectInline = async () => {
    if (!newProjectName.trim()) return;
    setIsCreatingProject(true);
    setSaveError(null);
    try {
      const created = await createProject({ name: newProjectName.trim() });
      setProjects((prev) => [...prev, created]);
      setSelectedProjectId(created.id);
      setNewProjectName("");
      setShowNewProjectInput(false);
    } catch (err: unknown) {
      setSaveError(err instanceof Error ? err.message : "Failed to create project");
    } finally {
      setIsCreatingProject(false);
    }
  };

  const handleSaveToProject = async () => {
    if (!selectedProjectId) {
      setSaveError("Please select or create a project");
      return;
    }
    setIsSaving(true);
    setSaveError(null);
    try {
      const res = await saveAnalysisToProject(selectedProjectId, result);
      const projName = projects.find((p) => p.id === selectedProjectId)?.name || "Project";
      setSaveSuccess(`Saved to "${projName}" successfully!`);
      setTimeout(() => {
        setIsSaveModalOpen(false);
        setSaveSuccess(null);
      }, 1500);
    } catch (err: unknown) {
      let msg = err instanceof Error ? err.message : "Failed to save to project";
      if (err instanceof ApiError) {
        if (err.status === 401) {
          msg = "Your session has expired. Please sign in again.";
        } else if (err.status === 429) {
          msg = "Rate limit reached. Please wait a moment before saving again.";
        } else if (err.status === 504) {
          msg = "Save request timed out. Please try again.";
        } else if (err.status >= 500) {
          msg = "Database service is temporarily unavailable. Please try again.";
        }
      }
      setSaveError(msg);
    } finally {
      setIsSaving(false);
    }
  };

  return (
    <div className="w-full max-w-5xl mx-auto space-y-6 animate-in fade-in duration-200">
      {/* Top Action Bar */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-slate-800 pb-5">
        <div className="space-y-1">
          <div className="flex items-center gap-2">
            <span className="inline-flex items-center gap-1 text-[11px] font-semibold text-emerald-400 bg-emerald-500/10 px-2 py-0.5 rounded-full border border-emerald-500/20">
              <Sparkles className="h-3 w-3" />
              Intelligence Extracted
            </span>
            <span className="text-xs text-slate-500">•</span>
            <span className="text-xs text-slate-400">{result.analyzedAt}</span>
          </div>
          <h2 className="text-xl sm:text-2xl font-bold text-white tracking-tight">
            {result.title}
          </h2>
        </div>

        {/* Action Buttons */}
        <div className="flex items-center gap-2.5 flex-wrap self-start sm:self-auto">
          {isFromMemory && onBackToMemory ? (
            <button
              onClick={onBackToMemory}
              className="inline-flex items-center justify-center gap-2 rounded-xl border border-slate-800 bg-slate-900/80 px-4 py-2 text-xs sm:text-sm font-medium text-slate-200 hover:bg-slate-800 hover:text-white transition-colors shadow-sm"
            >
              <ArrowLeft className="h-3.5 w-3.5" />
              <span>Back to Memory</span>
            </button>
          ) : (
            <button
              onClick={handleSaveClick}
              className="inline-flex items-center justify-center gap-2 rounded-xl border border-blue-500/30 bg-blue-600/10 px-4 py-2 text-xs sm:text-sm font-medium text-blue-400 hover:bg-blue-600 hover:text-white transition-all shadow-sm cursor-pointer"
            >
              <Bookmark className="h-3.5 w-3.5" />
              <span>Save to Project</span>
            </button>
          )}

          {/* Reset / New Analysis */}
          <button
            onClick={onReset}
            className="inline-flex items-center justify-center gap-2 rounded-xl border border-slate-800 bg-slate-900/80 px-4 py-2 text-xs sm:text-sm font-medium text-slate-200 hover:bg-slate-800 hover:text-white transition-colors shadow-sm"
          >
            <RotateCcw className="h-3.5 w-3.5" />
            <span>New Analysis</span>
          </button>
        </div>
      </div>

      {/* Metrics Row */}
      <div className="grid grid-cols-2 sm:grid-cols-5 gap-3">
        {/* Messages Analyzed */}
        <div className="rounded-xl border border-slate-800 bg-slate-900/40 p-3.5 space-y-1">
          <div className="flex items-center gap-1.5 text-xs text-slate-400">
            <MessageSquare className="h-3.5 w-3.5 text-blue-400" />
            <span>Analyzed</span>
          </div>
          <div className="text-xl font-bold text-white font-mono">
            {result.stats.messagesAnalyzed}
            <span className="text-xs font-normal text-slate-500 ml-1">msgs</span>
          </div>
        </div>

        {/* Key Points */}
        <div className="rounded-xl border border-slate-800 bg-slate-900/40 p-3.5 space-y-1">
          <div className="flex items-center gap-1.5 text-xs text-slate-400">
            <Sparkles className="h-3.5 w-3.5 text-blue-400" />
            <span>Key Points</span>
          </div>
          <div className="text-xl font-bold text-white font-mono">
            {result.stats.keyPointsCount}
          </div>
        </div>

        {/* Actions */}
        <div className="rounded-xl border border-slate-800 bg-slate-900/40 p-3.5 space-y-1">
          <div className="flex items-center gap-1.5 text-xs text-slate-400">
            <CheckSquare className="h-3.5 w-3.5 text-amber-400" />
            <span>Actions</span>
          </div>
          <div className="text-xl font-bold text-white font-mono">
            {result.stats.actionsCount}
          </div>
        </div>

        {/* Decisions */}
        <div className="rounded-xl border border-slate-800 bg-slate-900/40 p-3.5 space-y-1">
          <div className="flex items-center gap-1.5 text-xs text-slate-400">
            <Gavel className="h-3.5 w-3.5 text-emerald-400" />
            <span>Decisions</span>
          </div>
          <div className="text-xl font-bold text-white font-mono">
            {result.stats.decisionsCount}
          </div>
        </div>

        {/* Important Dates */}
        <div className="col-span-2 sm:col-span-1 rounded-xl border border-slate-800 bg-slate-900/40 p-3.5 space-y-1">
          <div className="flex items-center gap-1.5 text-xs text-slate-400">
            <Calendar className="h-3.5 w-3.5 text-purple-400" />
            <span>Key Dates</span>
          </div>
          <div className="text-xl font-bold text-white font-mono">
            {result.stats.importantDatesCount}
          </div>
        </div>
      </div>

      {/* Main Results Container */}
      <div className="rounded-2xl border border-slate-800 bg-slate-900/60 shadow-xl shadow-black/40 p-5 sm:p-7 space-y-6">
        {/* View Switcher Tabs */}
        <div className="flex items-center justify-start border-b border-slate-800 pb-4 overflow-x-auto gap-2">
          {tabs.map((tab) => {
            const isActive = activeView === tab.id;
            return (
              <button
                key={tab.id}
                onClick={() => setActiveView(tab.id)}
                className={`flex items-center gap-2 px-4 py-2 rounded-xl text-xs sm:text-sm font-medium transition-all ${
                  isActive
                    ? "bg-blue-600 text-white shadow-md shadow-blue-600/20"
                    : "text-slate-400 hover:text-slate-200 hover:bg-slate-800/80"
                }`}
              >
                {tab.icon}
                <span>{tab.label}</span>
              </button>
            );
          })}
        </div>

        {/* Active View Render */}
        <div className="pt-2">
          {activeView === "keypoints" && (
            <KeyPointsView
              keyPoints={result.keyPoints}
              onOpenSource={(src) => setSelectedSource(src)}
            />
          )}
          {activeView === "summary" && <SummaryView result={result} />}
          {activeView === "table" && (
            <TableView
              result={result}
              onOpenSource={(src) => setSelectedSource(src)}
            />
          )}
          {activeView === "structured" && (
            <StructuredView
              result={result}
              onOpenSource={(src) => setSelectedSource(src)}
            />
          )}
        </div>
      </div>

      {/* Granular Source Modal */}
      <SourceModal
        source={selectedSource}
        onClose={() => setSelectedSource(null)}
      />

      {/* Save to Project Modal */}
      {isSaveModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm p-4 animate-in fade-in duration-150">
          <div className="w-full max-w-md rounded-2xl border border-slate-800 bg-slate-900 p-6 shadow-2xl space-y-4">
            <div className="flex items-center justify-between border-b border-slate-800 pb-3">
              <div className="flex items-center gap-2">
                <Bookmark className="h-5 w-5 text-blue-400" />
                <h3 className="text-base font-bold text-white">Save to Project Memory</h3>
              </div>
              <button
                onClick={() => setIsSaveModalOpen(false)}
                className="text-slate-400 hover:text-white transition-colors"
                aria-label="Close modal"
              >
                <X className="h-4 w-4" />
              </button>
            </div>

            {saveSuccess ? (
              <div className="py-6 text-center space-y-2">
                <div className="mx-auto flex h-12 w-12 items-center justify-center rounded-full bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                  <Check className="h-6 w-6" />
                </div>
                <p className="text-sm font-semibold text-white">{saveSuccess}</p>
              </div>
            ) : (
              <div className="space-y-4">
                {saveError && (
                  <div className="p-2.5 rounded-lg bg-rose-500/10 border border-rose-500/20 text-xs text-rose-300 flex items-center gap-2">
                    <AlertCircle className="h-3.5 w-3.5 shrink-0" />
                    <span>{saveError}</span>
                  </div>
                )}

                <div className="space-y-2">
                  <label className="text-xs font-semibold text-slate-300">
                    Target Project
                  </label>

                  {isLoadingProjects ? (
                    <div className="flex items-center gap-2 text-xs text-slate-400 bg-slate-950 p-3 rounded-xl border border-slate-800">
                      <Loader2 className="h-3.5 w-3.5 animate-spin text-blue-400" />
                      <span>Loading projects...</span>
                    </div>
                  ) : projects.length === 0 && !showNewProjectInput ? (
                    <div className="p-3 rounded-xl border border-slate-800 bg-slate-950 text-xs text-slate-400 space-y-2">
                      <p>No projects found. Create one to save this analysis.</p>
                      <button
                        type="button"
                        onClick={() => setShowNewProjectInput(true)}
                        className="inline-flex items-center gap-1 text-xs text-blue-400 hover:text-blue-300 font-medium"
                      >
                        <FolderPlus className="h-3.5 w-3.5" />
                        <span>Create New Project</span>
                      </button>
                    </div>
                  ) : (
                    <div className="space-y-2">
                      <select
                        value={selectedProjectId}
                        onChange={(e) => setSelectedProjectId(e.target.value)}
                        className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3.5 py-2.5 text-sm text-slate-200 focus:outline-none focus:border-blue-500 transition-colors"
                      >
                        {projects.map((p) => (
                          <option key={p.id} value={p.id}>
                            {p.name}
                          </option>
                        ))}
                      </select>

                      {!showNewProjectInput && (
                        <button
                          type="button"
                          onClick={() => setShowNewProjectInput(true)}
                          className="inline-flex items-center gap-1 text-xs text-slate-400 hover:text-blue-400 transition-colors"
                        >
                          <Plus className="h-3 w-3" />
                          <span>+ Or create a new project</span>
                        </button>
                      )}
                    </div>
                  )}

                  {showNewProjectInput && (
                    <div className="p-3 rounded-xl border border-slate-800 bg-slate-950 space-y-2.5">
                      <label className="text-[11px] font-medium text-slate-400">
                        New Project Name
                      </label>
                      <div className="flex gap-2">
                        <input
                          type="text"
                          value={newProjectName}
                          onChange={(e) => setNewProjectName(e.target.value)}
                          placeholder="e.g. Riverside Office"
                          className="flex-1 bg-slate-900 border border-slate-800 rounded-lg px-3 py-1.5 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-blue-500"
                        />
                        <button
                          type="button"
                          disabled={isCreatingProject || !newProjectName.trim()}
                          onClick={handleCreateProjectInline}
                          className="px-3 py-1.5 rounded-lg bg-blue-600 hover:bg-blue-500 text-white text-xs font-medium disabled:opacity-50"
                        >
                          {isCreatingProject ? (
                            <Loader2 className="h-3 w-3 animate-spin" />
                          ) : (
                            "Create"
                          )}
                        </button>
                        <button
                          type="button"
                          onClick={() => setShowNewProjectInput(false)}
                          className="text-xs text-slate-400 hover:text-white px-1"
                        >
                          Cancel
                        </button>
                      </div>
                    </div>
                  )}
                </div>

                <div className="flex items-center justify-end gap-2 pt-2 border-t border-slate-800">
                  <button
                    type="button"
                    onClick={() => setIsSaveModalOpen(false)}
                    className="px-3.5 py-2 rounded-xl text-xs font-medium text-slate-400 hover:text-white hover:bg-slate-800 transition-colors"
                  >
                    Cancel
                  </button>
                  <button
                    type="button"
                    disabled={isSaving || !selectedProjectId}
                    onClick={handleSaveToProject}
                    className="inline-flex items-center gap-1.5 px-4 py-2 rounded-xl bg-blue-600 hover:bg-blue-500 text-white text-xs font-medium transition-all shadow-md shadow-blue-600/20 disabled:opacity-50"
                  >
                    {isSaving && <Loader2 className="h-3.5 w-3.5 animate-spin" />}
                    <span>Save Intelligence</span>
                  </button>
                </div>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Guest Save to Project Memory Conversion Modal */}
      {isGuestSaveModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/80 backdrop-blur-sm animate-in fade-in duration-200">
          <div className="w-full max-w-md rounded-2xl border border-slate-800 bg-slate-900 shadow-2xl p-6 sm:p-7 space-y-5 animate-in zoom-in-95 duration-150">
            <div className="flex items-center justify-between border-b border-slate-800 pb-3">
              <div className="flex items-center gap-2">
                <div className="h-8 w-8 rounded-xl bg-blue-600/10 border border-blue-500/20 flex items-center justify-center text-blue-400">
                  <Bookmark className="h-4 w-4" />
                </div>
                <h3 className="text-base font-bold text-white">Save to Project Memory</h3>
              </div>
              <button
                onClick={() => setIsGuestSaveModalOpen(false)}
                className="p-1 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800 transition-colors cursor-pointer"
                aria-label="Close modal"
              >
                <X className="h-4 w-4" />
              </button>
            </div>

            <div className="space-y-3 text-sm text-slate-300">
              <p className="leading-relaxed">
                Create a free account or sign in to save this analysis to Project Memory.
              </p>
              <div className="rounded-xl border border-slate-800 bg-slate-950/60 p-3.5 space-y-2 text-xs text-slate-400">
                <div className="flex items-center gap-2 text-slate-300 font-medium">
                  <Sparkles className="h-3.5 w-3.5 text-blue-400" />
                  <span>With a Shiftly account:</span>
                </div>
                <ul className="space-y-1.5 list-disc list-inside text-slate-400 pl-1">
                  <li>Organize analyses into persistent project workspaces</li>
                  <li>Search across all discussions and decisions</li>
                  <li>Analyze larger communications up to 200,000 characters</li>
                </ul>
              </div>
            </div>

            <div className="flex flex-col sm:flex-row items-stretch sm:items-center justify-end gap-2.5 pt-2 border-t border-slate-800">
              <button
                onClick={() => setIsGuestSaveModalOpen(false)}
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
    </div>
  );
}
