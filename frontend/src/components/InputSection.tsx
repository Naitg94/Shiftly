"use client";

import { useState } from "react";
import {
  Upload,
  FileText,
  Sparkles,
  ClipboardList,
  RotateCcw,
  FileType2,
  FileCode,
  FileUp,
  AlertCircle,
} from "lucide-react";
import { SAMPLE_CONVERSATION_RAW } from "@/data/mockData";

interface InputSectionProps {
  inputText: string;
  setInputText: (text: string) => void;
  onAnalyze: () => void;
}

export default function InputSection({
  inputText,
  setInputText,
  onAnalyze,
}: InputSectionProps) {
  const [activeTab, setActiveTab] = useState<"paste" | "upload">("paste");
  const [dragOver, setDragOver] = useState(false);
  const [uploadedFileName, setUploadedFileName] = useState<string | null>(null);

  const handleLoadSample = () => {
    setInputText(SAMPLE_CONVERSATION_RAW);
    setUploadedFileName(null);
    setActiveTab("paste");
  };

  const handleClear = () => {
    setInputText("");
    setUploadedFileName(null);
  };

  const handleFileDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setDragOver(false);
    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      const file = e.dataTransfer.files[0];
      setUploadedFileName(file.name);
      // Auto pre-populate sample text so user can test immediately
      if (!inputText) {
        setInputText(SAMPLE_CONVERSATION_RAW);
      }
    }
  };

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      const file = e.target.files[0];
      setUploadedFileName(file.name);
      if (!inputText) {
        setInputText(SAMPLE_CONVERSATION_RAW);
      }
    }
  };

  const charCount = inputText.length;
  const wordCount = inputText.trim() ? inputText.trim().split(/\s+/).length : 0;
  const isReadyToAnalyze = inputText.trim().length > 0 || uploadedFileName !== null;

  return (
    <div className="w-full max-w-4xl mx-auto space-y-8 animate-in fade-in duration-200">
      {/* Hero Headline */}
      <div className="text-center space-y-3 pt-4 sm:pt-8">
        <div className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-medium bg-blue-500/10 text-blue-400 border border-blue-500/20 mb-1">
          <Sparkles className="h-3.5 w-3.5" />
          <span>Communication Intelligence</span>
        </div>
        <h1 className="text-3xl sm:text-5xl font-bold tracking-tight text-white">
          Find what matters.
        </h1>
        <p className="text-base sm:text-lg text-slate-300 max-w-xl mx-auto font-normal">
          Turn long project communication into clear information.
        </p>
      </div>

      {/* Main Input Card */}
      <div className="rounded-2xl border border-slate-800 bg-slate-900/60 shadow-xl shadow-black/40 p-5 sm:p-7 space-y-5">
        {/* Tab & Controls Bar */}
        <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 border-b border-slate-800 pb-4">
          <div className="flex items-center gap-1 bg-slate-950 p-1 rounded-xl border border-slate-800 text-xs">
            <button
              onClick={() => setActiveTab("paste")}
              className={`flex items-center gap-2 px-3.5 py-1.5 rounded-lg font-medium transition-colors ${
                activeTab === "paste"
                  ? "bg-slate-800 text-white shadow-sm"
                  : "text-slate-400 hover:text-slate-200"
              }`}
            >
              <ClipboardList className="h-3.5 w-3.5" />
              <span>Paste Conversation</span>
            </button>
            <button
              onClick={() => setActiveTab("upload")}
              className={`flex items-center gap-2 px-3.5 py-1.5 rounded-lg font-medium transition-colors ${
                activeTab === "upload"
                  ? "bg-slate-800 text-white shadow-sm"
                  : "text-slate-400 hover:text-slate-200"
              }`}
            >
              <Upload className="h-3.5 w-3.5" />
              <span>Upload File</span>
              <span className="text-[10px] text-slate-400 font-normal">UI</span>
            </button>
          </div>

          {/* Quick Actions */}
          <div className="flex items-center gap-2 self-end sm:self-auto text-xs">
            <button
              onClick={handleLoadSample}
              className="inline-flex items-center gap-1.5 rounded-lg border border-blue-500/30 bg-blue-500/10 px-3 py-1.5 font-medium text-blue-300 hover:bg-blue-500/20 transition-colors"
              title="Load a realistic construction coordination thread"
            >
              <FileText className="h-3.5 w-3.5" />
              <span>Load sample conversation</span>
            </button>
            {charCount > 0 && (
              <button
                onClick={handleClear}
                className="inline-flex items-center gap-1 rounded-lg border border-slate-800 bg-slate-950/60 px-2.5 py-1.5 font-medium text-slate-400 hover:text-slate-200 hover:bg-slate-800 transition-colors"
                title="Clear current text"
              >
                <RotateCcw className="h-3.5 w-3.5" />
                <span>Clear</span>
              </button>
            )}
          </div>
        </div>

        {/* Tab 1: Paste Text */}
        {activeTab === "paste" && (
          <div className="space-y-2">
            <textarea
              value={inputText}
              onChange={(e) => setInputText(e.target.value)}
              placeholder="Paste a long project conversation here (Slack/Teams thread, WhatsApp chat, email chain, or meeting transcript)..."
              rows={10}
              className="w-full rounded-xl border border-slate-800 bg-slate-950 p-4 text-sm text-slate-100 placeholder:text-slate-500 focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500 resize-y font-mono leading-relaxed"
            />
          </div>
        )}

        {/* Tab 2: Upload File */}
        {activeTab === "upload" && (
          <div className="space-y-4">
            <div
              onDragOver={(e) => {
                e.preventDefault();
                setDragOver(true);
              }}
              onDragLeave={() => setDragOver(false)}
              onDrop={handleFileDrop}
              className={`relative flex flex-col items-center justify-center rounded-xl border-2 border-dashed p-8 sm:p-12 text-center transition-all ${
                dragOver
                  ? "border-blue-500 bg-blue-950/20"
                  : "border-slate-800 bg-slate-950/50 hover:border-slate-700"
              }`}
            >
              <input
                type="file"
                id="file-upload-input"
                accept=".txt,.pdf,.docx,.csv"
                onChange={handleFileSelect}
                className="sr-only"
              />
              <label
                htmlFor="file-upload-input"
                className="cursor-pointer flex flex-col items-center space-y-3"
              >
                <div className="h-12 w-12 rounded-xl bg-blue-500/10 flex items-center justify-center text-blue-400 border border-blue-500/20">
                  <FileUp className="h-6 w-6" />
                </div>
                <div className="space-y-1">
                  <p className="text-sm font-medium text-slate-200">
                    <span className="text-blue-400 hover:underline">Click to upload</span> or drag and drop
                  </p>
                  <p className="text-xs text-slate-400">
                    TXT, PDF, DOCX, or exported chat transcripts
                  </p>
                </div>
              </label>

              {uploadedFileName && (
                <div className="mt-4 inline-flex items-center gap-2 rounded-lg bg-slate-900 border border-slate-700 px-3 py-1.5 text-xs text-emerald-400">
                  <FileText className="h-3.5 w-3.5" />
                  <span>Ready: {uploadedFileName}</span>
                </div>
              )}
            </div>

            <div className="flex flex-wrap items-center justify-center gap-2 text-[11px] text-slate-400">
              <span className="flex items-center gap-1 rounded bg-slate-950 px-2 py-1 border border-slate-800">
                <FileType2 className="h-3 w-3 text-slate-400" /> .TXT
              </span>
              <span className="flex items-center gap-1 rounded bg-slate-950 px-2 py-1 border border-slate-800">
                <FileText className="h-3 w-3 text-slate-400" /> .PDF
              </span>
              <span className="flex items-center gap-1 rounded bg-slate-950 px-2 py-1 border border-slate-800">
                <FileCode className="h-3 w-3 text-slate-400" /> .DOCX
              </span>
              <span className="flex items-center gap-1 rounded bg-slate-950 px-2 py-1 border border-slate-800">
                Chat Exports
              </span>
            </div>
          </div>
        )}

        {/* Footer: Character Count & Analyze Button */}
        <div className="flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-4 pt-2">
          <div className="text-xs text-slate-400 flex items-center gap-3">
            <span>
              <strong className="text-slate-300 font-mono">{charCount.toLocaleString()}</strong> characters
            </span>
            <span>•</span>
            <span>
              <strong className="text-slate-300 font-mono">{wordCount.toLocaleString()}</strong> words
            </span>
          </div>

          <button
            onClick={onAnalyze}
            disabled={!isReadyToAnalyze}
            className={`flex items-center justify-center gap-2 rounded-xl px-6 py-3 text-sm font-semibold transition-all shadow-lg ${
              isReadyToAnalyze
                ? "bg-blue-600 text-white hover:bg-blue-500 shadow-blue-600/25 active:scale-[0.99] cursor-pointer"
                : "bg-slate-800 text-slate-500 cursor-not-allowed border border-slate-800"
            }`}
          >
            <Sparkles className="h-4 w-4" />
            <span>Analyze Communication</span>
          </button>
        </div>
      </div>
    </div>
  );
}
