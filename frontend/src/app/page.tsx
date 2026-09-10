"use client";

import { useEffect, useState } from "react";
import { CheckCircle2, AlertCircle, RefreshCw, Server, Laptop, Layers, FileText } from "lucide-react";

interface BackendHealth {
  status: string;
  service: string;
  version: string;
}

export default function Home() {
  const [backendHealth, setBackendHealth] = useState<BackendHealth | null>(null);
  const [backendStatus, setBackendStatus] = useState<"checking" | "online" | "offline">("checking");
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const checkBackendHealth = async () => {
    setBackendStatus("checking");
    setErrorMessage(null);
    try {
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
      const res = await fetch(`${apiUrl}/api/health`);
      if (!res.ok) {
        throw new Error(`HTTP error ${res.status}`);
      }
      const data: BackendHealth = await res.json();
      setBackendHealth(data);
      setBackendStatus("online");
    } catch (err: unknown) {
      setBackendStatus("offline");
      setErrorMessage(err instanceof Error ? err.message : "Failed to connect to backend");
      setBackendHealth(null);
    }
  };

  useEffect(() => {
    checkBackendHealth();
  }, []);

  return (
    <main className="min-h-screen bg-slate-950 text-slate-100 flex flex-col items-center justify-between p-6 sm:p-12">
      <div className="w-full max-w-4xl space-y-10">
        {/* Header Branding */}
        <header className="flex flex-col items-start space-y-3 border-b border-slate-800 pb-6">
          <div className="flex items-center space-x-3">
            <div className="h-10 w-10 rounded-xl bg-blue-600 flex items-center justify-center text-white font-bold text-xl shadow-lg shadow-blue-500/20">
              S
            </div>
            <div>
              <h1 className="text-3xl font-bold tracking-tight text-white flex items-center gap-2">
                Shiftly
                <span className="text-xs font-semibold px-2 py-0.5 rounded-full bg-blue-500/10 text-blue-400 border border-blue-500/20">
                  Foundation
                </span>
              </h1>
              <p className="text-sm font-medium text-slate-400">Find what matters.</p>
            </div>
          </div>
          <p className="text-sm text-slate-300 max-w-xl">
            AI-powered communication intelligence layer. Processes long, unstructured project
            communication and extracts only the essential information so teams stay aligned without reading entire chat threads.
          </p>
        </header>

        {/* Foundation Status Alert */}
        <div className="rounded-xl border border-emerald-500/30 bg-emerald-950/20 p-4 sm:p-5 flex items-start gap-4">
          <CheckCircle2 className="h-6 w-6 text-emerald-400 shrink-0 mt-0.5" />
          <div className="space-y-1">
            <h2 className="text-base font-semibold text-emerald-300">
              Application Foundation Ready
            </h2>
            <p className="text-sm text-slate-300">
              Frontend and backend architectures are initialized and configured to run independently.
            </p>
          </div>
        </div>

        {/* Service Health Cards */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {/* Frontend Status */}
          <div className="rounded-xl border border-slate-800 bg-slate-900/50 p-6 space-y-4">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2.5">
                <Laptop className="h-5 w-5 text-blue-400" />
                <h3 className="font-semibold text-white">Frontend Service</h3>
              </div>
              <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-medium bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                <span className="h-1.5 w-1.5 rounded-full bg-emerald-400"></span>
                Running
              </span>
            </div>
            <div className="text-xs text-slate-400 space-y-1.5 border-t border-slate-800/80 pt-4">
              <div className="flex justify-between">
                <span>Framework</span>
                <span className="text-slate-200 font-mono">Next.js (App Router)</span>
              </div>
              <div className="flex justify-between">
                <span>Language</span>
                <span className="text-slate-200 font-mono">TypeScript</span>
              </div>
              <div className="flex justify-between">
                <span>Styling</span>
                <span className="text-slate-200 font-mono">Tailwind CSS</span>
              </div>
              <div className="flex justify-between">
                <span>Port</span>
                <span className="text-slate-200 font-mono">3000</span>
              </div>
            </div>
          </div>

          {/* Backend Status */}
          <div className="rounded-xl border border-slate-800 bg-slate-900/50 p-6 space-y-4">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2.5">
                <Server className="h-5 w-5 text-indigo-400" />
                <h3 className="font-semibold text-white">Backend Service</h3>
              </div>
              {backendStatus === "online" && (
                <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-medium bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                  <span className="h-1.5 w-1.5 rounded-full bg-emerald-400 animate-pulse"></span>
                  Online
                </span>
              )}
              {backendStatus === "offline" && (
                <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-medium bg-rose-500/10 text-rose-400 border border-rose-500/20">
                  <AlertCircle className="h-3 w-3" />
                  Offline
                </span>
              )}
              {backendStatus === "checking" && (
                <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-medium bg-amber-500/10 text-amber-400 border border-amber-500/20">
                  <RefreshCw className="h-3 w-3 animate-spin" />
                  Checking
                </span>
              )}
            </div>

            <div className="text-xs text-slate-400 space-y-1.5 border-t border-slate-800/80 pt-4">
              <div className="flex justify-between">
                <span>Framework</span>
                <span className="text-slate-200 font-mono">FastAPI</span>
              </div>
              <div className="flex justify-between">
                <span>Health Endpoint</span>
                <span className="text-slate-200 font-mono">/api/health</span>
              </div>
              <div className="flex justify-between">
                <span>Service Info</span>
                <span className="text-slate-200 font-mono">
                  {backendHealth ? `${backendHealth.service} (${backendHealth.version})` : "N/A"}
                </span>
              </div>
              <div className="flex justify-between items-center">
                <span>Actions</span>
                <button
                  onClick={checkBackendHealth}
                  className="inline-flex items-center gap-1 text-blue-400 hover:text-blue-300 font-medium transition-colors"
                >
                  <RefreshCw className="h-3 w-3" />
                  Recheck
                </button>
              </div>
            </div>

            {backendStatus === "offline" && (
              <p className="text-[11px] text-amber-400/90 bg-amber-950/20 border border-amber-800/30 rounded p-2">
                Backend is not currently reachable on port 8000. Start it with: <br />
                <code className="font-mono text-slate-200">uvicorn app.main:app --reload</code>
              </p>
            )}
          </div>
        </div>

        {/* Roadmap / Scope Guardrails */}
        <div className="rounded-xl border border-slate-800/70 bg-slate-900/30 p-6 space-y-3">
          <div className="flex items-center gap-2 text-slate-200 font-medium text-sm">
            <Layers className="h-4 w-4 text-blue-400" />
            <span>Architecture & Scope Guardrails</span>
          </div>
          <p className="text-xs text-slate-400 leading-relaxed">
            Shiftly foundation is locked to core intelligence extraction: Pasted & uploaded conversations, chunked processing, and structured multi-view presentation (Key points, Summary, Table, Structured). External integrations, agents, and complex analytics are strictly out of scope.
          </p>
        </div>
      </div>

      {/* Footer */}
      <footer className="w-full max-w-4xl border-t border-slate-800/80 pt-6 mt-12 flex flex-col sm:flex-row justify-between items-center text-xs text-slate-400 gap-2">
        <div className="flex items-center gap-2">
          <FileText className="h-3.5 w-3.5 text-slate-400" />
          <span>Shiftly — Initial Project Foundation</span>
        </div>
        <span>Built with Next.js & FastAPI</span>
      </footer>
    </main>
  );
}
