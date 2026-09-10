"use client";

import { useEffect } from "react";
import { X, FileText, Calendar, User, Hash, ExternalLink } from "lucide-react";
import { SourceReference } from "@/types/analysis";

interface SourceModalProps {
  source: SourceReference | null;
  onClose: () => void;
}

export default function SourceModal({ source, onClose }: SourceModalProps) {
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [onClose]);

  if (!source) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 sm:p-6">
      {/* Backdrop */}
      <div
        className="fixed inset-0 bg-black/60 backdrop-blur-sm transition-opacity"
        onClick={onClose}
        aria-hidden="true"
      />

      {/* Modal Dialog */}
      <div
        className="relative w-full max-w-lg rounded-2xl border border-slate-700 bg-slate-900 shadow-2xl p-6 sm:p-7 z-10 animate-in fade-in zoom-in-95 duration-150"
        role="dialog"
        aria-modal="true"
        aria-labelledby="source-modal-title"
      >
        {/* Header */}
        <div className="flex items-start justify-between gap-4 border-b border-slate-800 pb-4">
          <div className="space-y-1">
            <div className="flex items-center gap-2">
              <span className="inline-flex items-center gap-1 rounded-md bg-blue-500/10 px-2 py-0.5 text-xs font-semibold text-blue-400 border border-blue-500/20">
                <FileText className="h-3 w-3" />
                {source.sourceType}
              </span>
              <span className="text-xs text-slate-400">•</span>
              <span className="text-xs text-slate-400">{source.messageRef}</span>
            </div>
            <h3 id="source-modal-title" className="text-base font-semibold text-white">
              {source.sourceName}
            </h3>
          </div>
          <button
            onClick={onClose}
            className="rounded-lg p-1.5 text-slate-400 hover:bg-slate-800 hover:text-white transition-colors"
            aria-label="Close source info"
          >
            <X className="h-4 w-4" />
          </button>
        </div>

        {/* Metadata Details */}
        <div className="mt-4 grid grid-cols-2 gap-3 text-xs">
          <div className="rounded-lg bg-slate-800/40 p-2.5 border border-slate-800">
            <div className="flex items-center gap-1.5 text-slate-400 mb-1">
              <User className="h-3.5 w-3.5 text-blue-400" />
              <span>Participant / Sender</span>
            </div>
            <p className="font-medium text-slate-200 truncate">{source.sender}</p>
          </div>
          <div className="rounded-lg bg-slate-800/40 p-2.5 border border-slate-800">
            <div className="flex items-center gap-1.5 text-slate-400 mb-1">
              <Calendar className="h-3.5 w-3.5 text-emerald-400" />
              <span>Date & Time</span>
            </div>
            <p className="font-medium text-slate-200 truncate">{source.date}</p>
          </div>
        </div>

        {/* Relevant Excerpt */}
        <div className="mt-4 space-y-2">
          <label className="text-xs font-medium uppercase tracking-wider text-slate-400">
            Original Conversation Excerpt
          </label>
          <div className="rounded-xl border border-blue-500/20 bg-blue-950/20 p-3.5 text-sm text-slate-200 italic leading-relaxed">
            &ldquo;{source.excerpt}&rdquo;
          </div>
        </div>

        {/* Footer Note */}
        <div className="mt-5 flex items-center justify-between pt-3 border-t border-slate-800/80 text-[11px] text-slate-400">
          <span>Shiftly Verified Citation</span>
          <button
            onClick={onClose}
            className="rounded-md bg-slate-800 hover:bg-slate-700 px-3 py-1.5 text-xs font-medium text-slate-200 transition-colors"
          >
            Done
          </button>
        </div>
      </div>
    </div>
  );
}
