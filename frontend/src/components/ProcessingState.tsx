"use client";

import { useEffect, useState } from "react";
import { Check, Loader2, Sparkles } from "lucide-react";

interface ProcessingStateProps {
  onComplete: () => void;
}

const STAGES = [
  { id: 1, label: "Reading communication", description: "Parsing conversation structure and participants..." },
  { id: 2, label: "Finding important information", description: "Identifying key points, decisions, and action items..." },
  { id: 3, label: "Organizing results", description: "Synthesizing multi-view intelligence model..." },
];

export default function ProcessingState({ onComplete }: ProcessingStateProps) {
  const [currentStage, setCurrentStage] = useState(1);

  useEffect(() => {
    // Stage 1 -> 2
    const timer1 = setTimeout(() => {
      setCurrentStage(2);
    }, 900);

    // Stage 2 -> 3
    const timer2 = setTimeout(() => {
      setCurrentStage(3);
    }, 1900);

    // Stage 3 -> Complete
    const timer3 = setTimeout(() => {
      onComplete();
    }, 2800);

    return () => {
      clearTimeout(timer1);
      clearTimeout(timer2);
      clearTimeout(timer3);
    };
  }, [onComplete]);

  return (
    <div className="w-full max-w-lg mx-auto py-16 px-4 animate-in fade-in duration-200">
      <div className="rounded-2xl border border-slate-800 bg-slate-900/60 p-8 shadow-2xl shadow-black/50 space-y-8 text-center">
        {/* Spinner & Brand */}
        <div className="space-y-3">
          <div className="inline-flex h-14 w-14 items-center justify-center rounded-2xl bg-blue-500/10 text-blue-400 border border-blue-500/20 shadow-lg shadow-blue-500/10">
            <Sparkles className="h-7 w-7 animate-pulse" />
          </div>
          <h2 className="text-xl font-bold text-white tracking-tight">
            Analyzing Communication
          </h2>
          <p className="text-xs text-slate-400">
            Extracting critical intelligence from conversation
          </p>
        </div>

        {/* Stages Timeline */}
        <div className="space-y-4 text-left">
          {STAGES.map((stage) => {
            const isFinished = currentStage > stage.id;
            const isCurrent = currentStage === stage.id;

            return (
              <div
                key={stage.id}
                className={`flex items-start gap-3.5 p-3 rounded-xl border transition-all duration-300 ${
                  isCurrent
                    ? "border-blue-500/40 bg-blue-950/20"
                    : isFinished
                    ? "border-emerald-500/20 bg-emerald-950/10 opacity-80"
                    : "border-slate-800/40 bg-transparent opacity-40"
                }`}
              >
                {/* Status Icon */}
                <div className="mt-0.5 shrink-0">
                  {isFinished ? (
                    <div className="h-5 w-5 rounded-full bg-emerald-500/20 text-emerald-400 flex items-center justify-center border border-emerald-500/30">
                      <Check className="h-3 w-3 stroke-[3]" />
                    </div>
                  ) : isCurrent ? (
                    <div className="h-5 w-5 rounded-full bg-blue-500/20 text-blue-400 flex items-center justify-center border border-blue-500/30">
                      <Loader2 className="h-3 w-3 animate-spin" />
                    </div>
                  ) : (
                    <div className="h-5 w-5 rounded-full bg-slate-800 text-slate-500 flex items-center justify-center text-[10px] font-mono">
                      {stage.id}
                    </div>
                  )}
                </div>

                {/* Stage Text */}
                <div className="space-y-0.5 flex-1">
                  <p
                    className={`text-sm font-medium ${
                      isCurrent
                        ? "text-white"
                        : isFinished
                        ? "text-emerald-300"
                        : "text-slate-500"
                    }`}
                  >
                    {stage.label}
                  </p>
                  <p className="text-xs text-slate-400 leading-normal">
                    {stage.description}
                  </p>
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}
