"use client";

import { useState, useEffect, useCallback } from "react";
import {
  Folder,
  Plus,
  Search,
  Calendar,
  Sparkles,
  CheckSquare,
  Gavel,
  ArrowRight,
  Loader2,
  FolderPlus,
  AlertCircle,
  Database,
  FileText,
  X,
} from "lucide-react";
import { Project, StoredAnalysisSummary, SearchResultItem } from "@/types/project";
import {
  fetchProjects,
  createProject,
  fetchAnalyses,
  fetchAnalysis,
  searchProjectIntelligence,
} from "@/lib/api";
import { ShiftlyAnalysisResult } from "@/types/analysis";

interface ProjectMemoryProps {
  onLoadAnalysis: (result: ShiftlyAnalysisResult) => void;
}

export default function ProjectMemory({ onLoadAnalysis }: ProjectMemoryProps) {
  const [projects, setProjects] = useState<Project[]>([]);
  const [selectedProjectId, setSelectedProjectId] = useState<string>("");
  const [analyses, setAnalyses] = useState<StoredAnalysisSummary[]>([]);
  const [searchQuery, setSearchQuery] = useState("");
  const [searchResults, setSearchResults] = useState<SearchResultItem[]>([]);
  const [isSearching, setIsSearching] = useState(false);
  const [isLoadingProjects, setIsLoadingProjects] = useState(true);
  const [isLoadingAnalyses, setIsLoadingAnalyses] = useState(false);
  const [isLoadingDetail, setIsLoadingDetail] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  // New Project Modal State
  const [isCreateModalOpen, setIsCreateModalOpen] = useState(false);
  const [newProjectName, setNewProjectName] = useState("");
  const [newProjectDesc, setNewProjectDesc] = useState("");
  const [isCreatingProject, setIsCreatingProject] = useState(false);
  const [createError, setCreateError] = useState<string | null>(null);

  // Initial load of projects
  const loadProjects = useCallback(async (selectId?: string) => {
    setIsLoadingProjects(true);
    setErrorMessage(null);
    try {
      const data = await fetchProjects();
      setProjects(data);
      if (selectId) {
        setSelectedProjectId(selectId);
      } else if (data.length > 0 && !selectedProjectId) {
        setSelectedProjectId(data[0].id);
      }
    } catch (err: unknown) {
      setErrorMessage(
        err instanceof Error ? err.message : "Failed to connect to backend for projects"
      );
    } finally {
      setIsLoadingProjects(false);
    }
  }, [selectedProjectId]);

  useEffect(() => {
    loadProjects();
  }, [loadProjects]);

  // Load analyses when selected project changes
  const loadAnalysesForProject = useCallback(async (projId: string) => {
    if (!projId) {
      setAnalyses([]);
      return;
    }
    setIsLoadingAnalyses(true);
    setErrorMessage(null);
    try {
      const data = await fetchAnalyses(projId);
      setAnalyses(data);
    } catch (err: unknown) {
      setErrorMessage(
        err instanceof Error ? err.message : "Failed to load analyses for this project"
      );
    } finally {
      setIsLoadingAnalyses(false);
    }
  }, []);

  useEffect(() => {
    if (selectedProjectId) {
      loadAnalysesForProject(selectedProjectId);
      setSearchQuery("");
      setSearchResults([]);
    }
  }, [selectedProjectId, loadAnalysesForProject]);

  // Search within selected project
  const handleSearch = async (query: string) => {
    setSearchQuery(query);
    if (!query.trim()) {
      setSearchResults([]);
      return;
    }
    if (!selectedProjectId) return;

    setIsSearching(true);
    try {
      const res = await searchProjectIntelligence(selectedProjectId, query.trim());
      setSearchResults(res.results);
    } catch {
      // silently handle search errors
    } finally {
      setIsSearching(false);
    }
  };

  // Handle creating a new project
  const handleCreateProject = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newProjectName.trim()) {
      setCreateError("Project name is required");
      return;
    }
    setIsCreatingProject(true);
    setCreateError(null);
    try {
      const created = await createProject({
        name: newProjectName.trim(),
        description: newProjectDesc.trim() || undefined,
      });
      setNewProjectName("");
      setNewProjectDesc("");
      setIsCreateModalOpen(false);
      await loadProjects(created.id);
    } catch (err: unknown) {
      setCreateError(
        err instanceof Error ? err.message : "Failed to create project"
      );
    } finally {
      setIsCreatingProject(false);
    }
  };

  // View an analysis
  const handleOpenAnalysis = async (analysisId: string) => {
    if (!selectedProjectId) return;
    setIsLoadingDetail(true);
    try {
      const fullAnalysis = await fetchAnalysis(selectedProjectId, analysisId);
      onLoadAnalysis(fullAnalysis);
    } catch (err: unknown) {
      setErrorMessage(
        err instanceof Error ? err.message : "Failed to load full analysis"
      );
    } finally {
      setIsLoadingDetail(false);
    }
  };

  const selectedProject = projects.find((p) => p.id === selectedProjectId);

  return (
    <div className="w-full max-w-5xl mx-auto space-y-6 animate-in fade-in duration-200">
      {/* Header & Project Selector */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-slate-800 pb-5">
        <div className="space-y-1">
          <div className="flex items-center gap-2">
            <span className="inline-flex items-center gap-1 text-[11px] font-semibold text-blue-400 bg-blue-500/10 px-2 py-0.5 rounded-full border border-blue-500/20">
              <Database className="h-3 w-3" />
              Project Memory
            </span>
            <span className="text-xs text-slate-500">•</span>
            <span className="text-xs text-slate-400">Persistent Intelligence</span>
          </div>
          <h2 className="text-xl sm:text-2xl font-bold text-white tracking-tight">
            Project Workspace
          </h2>
        </div>

        {/* Project Selector & Actions */}
        <div className="flex items-center gap-2.5 flex-wrap">
          {isLoadingProjects ? (
            <div className="flex items-center gap-2 text-xs text-slate-400 bg-slate-900 px-3 py-2 rounded-xl border border-slate-800">
              <Loader2 className="h-3.5 w-3.5 animate-spin text-blue-400" />
              <span>Loading projects...</span>
            </div>
          ) : (
            <select
              value={selectedProjectId}
              onChange={(e) => setSelectedProjectId(e.target.value)}
              className="bg-slate-900 border border-slate-800 rounded-xl px-3 py-2 text-sm text-slate-200 focus:outline-none focus:border-blue-500 transition-colors cursor-pointer max-w-[220px] sm:max-w-xs truncate"
            >
              {projects.length === 0 ? (
                <option value="">No projects found</option>
              ) : (
                projects.map((p) => (
                  <option key={p.id} value={p.id}>
                    {p.name}
                  </option>
                ))
              )}
            </select>
          )}

          <button
            onClick={() => setIsCreateModalOpen(true)}
            className="inline-flex items-center gap-1.5 px-3.5 py-2 rounded-xl bg-blue-600 hover:bg-blue-500 text-white text-xs sm:text-sm font-medium transition-all shadow-md shadow-blue-600/20"
          >
            <Plus className="h-4 w-4" />
            <span>New Project</span>
          </button>
        </div>
      </div>

      {/* Global Error Banner */}
      {errorMessage && (
        <div className="flex items-start gap-2.5 p-3.5 rounded-xl border border-rose-500/20 bg-rose-500/10 text-xs text-rose-300">
          <AlertCircle className="h-4 w-4 text-rose-400 shrink-0 mt-0.5" />
          <span>{errorMessage}</span>
        </div>
      )}

      {/* No Projects State */}
      {!isLoadingProjects && projects.length === 0 && (
        <div className="rounded-2xl border border-dashed border-slate-800 bg-slate-900/30 p-10 text-center space-y-4">
          <div className="mx-auto flex h-12 w-12 items-center justify-center rounded-2xl bg-blue-600/10 text-blue-400 border border-blue-500/20">
            <FolderPlus className="h-6 w-6" />
          </div>
          <div className="space-y-1">
            <h3 className="text-base font-semibold text-white">No projects yet</h3>
            <p className="text-xs text-slate-400 max-w-sm mx-auto">
              Create your first project to organize communication analyses, track action items, and search project decisions.
            </p>
          </div>
          <button
            onClick={() => setIsCreateModalOpen(true)}
            className="inline-flex items-center gap-1.5 px-4 py-2 rounded-xl bg-blue-600 hover:bg-blue-500 text-white text-xs font-medium transition-all shadow-md shadow-blue-600/20"
          >
            <Plus className="h-4 w-4" />
            <span>Create First Project</span>
          </button>
        </div>
      )}

      {/* Project Selected View */}
      {selectedProject && (
        <div className="space-y-5">
          {/* Project Details Banner */}
          <div className="rounded-2xl border border-slate-800 bg-slate-900/60 p-5 space-y-4">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
              <div className="space-y-0.5">
                <div className="flex items-center gap-2">
                  <Folder className="h-4 w-4 text-blue-400" />
                  <h3 className="text-lg font-bold text-white tracking-tight">
                    {selectedProject.name}
                  </h3>
                </div>
                {selectedProject.description && (
                  <p className="text-xs text-slate-400 pl-6">
                    {selectedProject.description}
                  </p>
                )}
              </div>
              <div className="text-xs text-slate-400 font-mono bg-slate-800/60 px-2.5 py-1 rounded-lg self-start sm:self-auto border border-slate-700/50">
                {analyses.length} {analyses.length === 1 ? "analysis" : "analyses"} saved
              </div>
            </div>

            {/* Search Input */}
            <div className="relative">
              <Search className="absolute left-3.5 top-1/2 -translate-y-1/2 h-4 w-4 text-slate-400" />
              <input
                type="text"
                value={searchQuery}
                onChange={(e) => handleSearch(e.target.value)}
                placeholder="Search key points, actions, decisions, deadlines across this project..."
                className="w-full bg-slate-950 border border-slate-800 rounded-xl pl-10 pr-10 py-2.5 text-xs sm:text-sm text-slate-100 placeholder-slate-500 focus:outline-none focus:border-blue-500 transition-colors"
              />
              {searchQuery && (
                <button
                  onClick={() => handleSearch("")}
                  className="absolute right-3.5 top-1/2 -translate-y-1/2 text-slate-400 hover:text-white"
                >
                  <X className="h-4 w-4" />
                </button>
              )}
            </div>
          </div>

          {/* Search Results Display */}
          {searchQuery.trim() !== "" ? (
            <div className="space-y-3">
              <div className="flex items-center justify-between px-1 text-xs text-slate-400">
                <div className="flex items-center gap-1.5">
                  {isSearching && <Loader2 className="h-3.5 w-3.5 animate-spin text-blue-400" />}
                  <span>
                    Search results for &quot;<strong className="text-slate-200">{searchQuery}</strong>&quot;:
                  </span>
                </div>
                <span className="font-mono">
                  {searchResults.length} {searchResults.length === 1 ? "match" : "matches"}
                </span>
              </div>

              {searchResults.length === 0 && !isSearching ? (
                <div className="rounded-xl border border-slate-800 bg-slate-900/30 p-8 text-center text-xs text-slate-400">
                  No matching key points, action items, or decisions found for &quot;{searchQuery}&quot;.
                </div>
              ) : (
                <div className="grid grid-cols-1 gap-2.5">
                  {searchResults.map((item) => {
                    const badgeStyles: Record<string, { label: string; color: string; icon: React.ReactNode }> = {
                      "Key Point": {
                        label: "Key Point",
                        color: "text-blue-400 bg-blue-500/10 border-blue-500/20",
                        icon: <Sparkles className="h-3 w-3" />,
                      },
                      "Action": {
                        label: "Action Item",
                        color: "text-amber-400 bg-amber-500/10 border-amber-500/20",
                        icon: <CheckSquare className="h-3 w-3" />,
                      },
                      "Decision": {
                        label: "Decision",
                        color: "text-emerald-400 bg-emerald-500/10 border-emerald-500/20",
                        icon: <Gavel className="h-3 w-3" />,
                      },
                      "Date": {
                        label: "Important Date",
                        color: "text-purple-400 bg-purple-500/10 border-purple-500/20",
                        icon: <Calendar className="h-3 w-3" />,
                      },
                      "Summary": {
                        label: "Summary",
                        color: "text-cyan-400 bg-cyan-500/10 border-cyan-500/20",
                        icon: <FileText className="h-3 w-3" />,
                      },
                    };

                    const badge = badgeStyles[item.item_type] || badgeStyles["Key Point"];

                    return (
                      <div
                        key={item.id}
                        className="rounded-xl border border-slate-800 bg-slate-900/50 p-3.5 space-y-2 hover:border-slate-700 transition-colors"
                      >
                        <div className="flex flex-wrap items-center justify-between gap-2">
                          <div className="flex items-center gap-2">
                            <span
                              className={`inline-flex items-center gap-1 text-[10px] font-semibold uppercase tracking-wider px-2 py-0.5 rounded-full border ${badge.color}`}
                            >
                              {badge.icon}
                              {badge.label}
                            </span>
                            <span className="text-[11px] text-slate-400 truncate max-w-xs">
                              From: <span className="text-slate-300 font-medium">{item.analysis_title}</span>
                            </span>
                          </div>
                          <button
                            onClick={() => handleOpenAnalysis(item.analysis_id)}
                            disabled={isLoadingDetail}
                            className="inline-flex items-center gap-1 text-xs text-blue-400 hover:text-blue-300 transition-colors font-medium"
                          >
                            <span>Open Analysis</span>
                            <ArrowRight className="h-3 w-3" />
                          </button>
                        </div>
                        <p className="text-sm text-slate-200 leading-relaxed">{item.content}</p>
                        {item.source_reference && (
                          <div className="flex items-center gap-2 text-xs text-slate-400 pt-0.5">
                            <span className="rounded bg-slate-800/80 px-2 py-0.5 border border-slate-700/50 text-[11px]">
                              Source: {item.source_reference.sourceName} ({item.source_reference.messageRef})
                            </span>
                          </div>
                        )}
                      </div>
                    );
                  })}
                </div>
              )}
            </div>
          ) : (
            /* Chronological Analyses List */
            <div className="space-y-3">
              <div className="flex items-center justify-between px-1 text-xs text-slate-400">
                <span>Analyses History (Chronological)</span>
                <span className="font-mono">{analyses.length} saved</span>
              </div>

              {isLoadingAnalyses ? (
                <div className="rounded-xl border border-slate-800 bg-slate-900/40 p-8 text-center space-y-2">
                  <Loader2 className="h-5 w-5 animate-spin text-blue-400 mx-auto" />
                  <p className="text-xs text-slate-400">Loading stored analyses...</p>
                </div>
              ) : analyses.length === 0 ? (
                <div className="rounded-xl border border-slate-800 bg-slate-900/30 p-8 text-center space-y-2">
                  <FileText className="h-6 w-6 text-slate-500 mx-auto" />
                  <p className="text-sm font-medium text-slate-300">No analyses saved yet</p>
                  <p className="text-xs text-slate-400 max-w-sm mx-auto">
                    Go to the <strong>Analyze</strong> tab to paste or upload communication, then click <strong>&quot;Save to Project&quot;</strong> to preserve the extracted intelligence here.
                  </p>
                </div>
              ) : (
                <div className="grid grid-cols-1 gap-3">
                  {analyses.map((item) => (
                    <div
                      key={item.id}
                      className="rounded-xl border border-slate-800 bg-slate-900/50 p-4 sm:p-5 flex flex-col sm:flex-row sm:items-center justify-between gap-4 hover:border-slate-700 hover:bg-slate-900/80 transition-all shadow-sm group"
                    >
                      <div className="space-y-2 min-w-0">
                        <div className="flex items-center gap-2 text-xs text-slate-400">
                          <Calendar className="h-3 w-3 text-slate-500" />
                          <span>{item.created_at.slice(0, 16).replace("T", " ")}</span>
                        </div>
                        <h4 className="text-base font-semibold text-white tracking-tight truncate group-hover:text-blue-300 transition-colors">
                          {item.title}
                        </h4>

                        {/* Counts Badges */}
                        <div className="flex flex-wrap items-center gap-2 pt-1">
                          <span className="inline-flex items-center gap-1 text-[11px] text-blue-300 bg-blue-500/10 border border-blue-500/20 px-2 py-0.5 rounded-lg">
                            <Sparkles className="h-2.5 w-2.5 text-blue-400" />
                            <span>{item.key_points_count} points</span>
                          </span>
                          <span className="inline-flex items-center gap-1 text-[11px] text-amber-300 bg-amber-500/10 border border-amber-500/20 px-2 py-0.5 rounded-lg">
                            <CheckSquare className="h-2.5 w-2.5 text-amber-400" />
                            <span>{item.actions_count} actions</span>
                          </span>
                          <span className="inline-flex items-center gap-1 text-[11px] text-emerald-300 bg-emerald-500/10 border border-emerald-500/20 px-2 py-0.5 rounded-lg">
                            <Gavel className="h-2.5 w-2.5 text-emerald-400" />
                            <span>{item.decisions_count} decisions</span>
                          </span>
                          <span className="inline-flex items-center gap-1 text-[11px] text-purple-300 bg-purple-500/10 border border-purple-500/20 px-2 py-0.5 rounded-lg">
                            <Calendar className="h-2.5 w-2.5 text-purple-400" />
                            <span>{item.important_dates_count} dates</span>
                          </span>
                        </div>
                      </div>

                      <button
                        onClick={() => handleOpenAnalysis(item.id)}
                        disabled={isLoadingDetail}
                        className="inline-flex items-center justify-center gap-1.5 px-4 py-2 rounded-xl bg-slate-800 hover:bg-blue-600 hover:text-white text-slate-200 text-xs sm:text-sm font-medium transition-all self-start sm:self-center border border-slate-700/80 shadow-sm shrink-0"
                      >
                        {isLoadingDetail ? (
                          <Loader2 className="h-3.5 w-3.5 animate-spin" />
                        ) : (
                          <>
                            <span>View Intelligence</span>
                            <ArrowRight className="h-3.5 w-3.5" />
                          </>
                        )}
                      </button>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}
        </div>
      )}

      {/* Modal: Create Project */}
      {isCreateModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm p-4 animate-in fade-in duration-150">
          <div className="w-full max-w-md rounded-2xl border border-slate-800 bg-slate-900 p-6 shadow-2xl space-y-4">
            <div className="flex items-center justify-between border-b border-slate-800 pb-3">
              <div className="flex items-center gap-2">
                <FolderPlus className="h-5 w-5 text-blue-400" />
                <h3 className="text-base font-bold text-white">Create New Project</h3>
              </div>
              <button
                onClick={() => setIsCreateModalOpen(false)}
                className="text-slate-400 hover:text-white transition-colors"
              >
                <X className="h-4 w-4" />
              </button>
            </div>

            <form onSubmit={handleCreateProject} className="space-y-4">
              {createError && (
                <div className="p-2.5 rounded-lg bg-rose-500/10 border border-rose-500/20 text-xs text-rose-300 flex items-center gap-2">
                  <AlertCircle className="h-3.5 w-3.5 shrink-0" />
                  <span>{createError}</span>
                </div>
              )}

              <div className="space-y-1.5">
                <label className="text-xs font-semibold text-slate-300">
                  Project Name <span className="text-rose-400">*</span>
                </label>
                <input
                  type="text"
                  value={newProjectName}
                  onChange={(e) => setNewProjectName(e.target.value)}
                  placeholder="e.g. Riverside Office Renovation"
                  required
                  className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3.5 py-2 text-sm text-white placeholder-slate-500 focus:outline-none focus:border-blue-500 transition-colors"
                />
              </div>

              <div className="space-y-1.5">
                <label className="text-xs font-semibold text-slate-300">
                  Description <span className="text-slate-500 font-normal">(optional)</span>
                </label>
                <textarea
                  value={newProjectDesc}
                  onChange={(e) => setNewProjectDesc(e.target.value)}
                  placeholder="Brief description of project scope or client..."
                  rows={2}
                  className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3.5 py-2 text-xs sm:text-sm text-white placeholder-slate-500 focus:outline-none focus:border-blue-500 transition-colors resize-none"
                />
              </div>

              <div className="flex items-center justify-end gap-2 pt-2">
                <button
                  type="button"
                  onClick={() => setIsCreateModalOpen(false)}
                  className="px-3.5 py-2 rounded-xl text-xs font-medium text-slate-400 hover:text-white hover:bg-slate-800 transition-colors"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={isCreatingProject}
                  className="inline-flex items-center gap-1.5 px-4 py-2 rounded-xl bg-blue-600 hover:bg-blue-500 text-white text-xs font-medium transition-all shadow-md shadow-blue-600/20 disabled:opacity-50"
                >
                  {isCreatingProject && <Loader2 className="h-3.5 w-3.5 animate-spin" />}
                  <span>Create Project</span>
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
