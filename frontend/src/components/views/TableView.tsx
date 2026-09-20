"use client";

import { useMemo, useState } from "react";
import { ShiftlyAnalysisResult, SourceReference } from "@/types/analysis";
import { Info, ArrowUpDown, Filter } from "lucide-react";

interface TableViewProps {
  result: ShiftlyAnalysisResult;
  onOpenSource: (source: SourceReference) => void;
}

interface TableRow {
  id: string;
  type: "Key Point" | "Action" | "Decision" | "Date";
  typeLabel: string;
  information: string;
  person: string;
  date: string;
  source: SourceReference;
}

export default function TableView({ result, onOpenSource }: TableViewProps) {
  const [filterType, setFilterType] = useState<string>("all");

  const rows: TableRow[] = useMemo(() => {
    const list: TableRow[] = [];

    result.keyPoints.forEach((kp) => {
      list.push({
        id: kp.id,
        type: "Key Point",
        typeLabel: "Key Point",
        information: kp.point,
        person: kp.source.sender ? kp.source.sender.split("(")[0].trim() : "—",
        date: "—",
        source: kp.source,
      });
    });

    result.actions.forEach((act) => {
      list.push({
        id: act.id,
        type: "Action",
        typeLabel: "Action Item",
        information: act.action,
        person: act.responsiblePerson ? act.responsiblePerson.split("(")[0].trim() : "Unassigned",
        date: act.deadline || "—",
        source: act.source,
      });
    });

    result.decisions.forEach((dec) => {
      list.push({
        id: dec.id,
        type: "Decision",
        typeLabel: "Decision",
        information: dec.decision,
        person: dec.approvedBy ? dec.approvedBy.split("(")[0].trim() : "—",
        date: dec.date || "—",
        source: dec.source,
      });
    });

    result.importantDates.forEach((dt) => {
      list.push({
        id: dt.id,
        type: "Date",
        typeLabel: "Milestone Date",
        information: dt.significance ? `${dt.title} — ${dt.significance}` : dt.title,
        person: dt.source.sender ? dt.source.sender.split("(")[0].trim() : "—",
        date: dt.date || "—",
        source: dt.source,
      });
    });

    return list;
  }, [result]);

  const filteredRows = useMemo(() => {
    if (filterType === "all") return rows;
    return rows.filter((r) => r.type === filterType);
  }, [rows, filterType]);

  const getTypeBadgeStyle = (type: TableRow["type"]) => {
    switch (type) {
      case "Action":
        return "bg-amber-500/10 text-amber-400 border-amber-500/20";
      case "Decision":
        return "bg-emerald-500/10 text-emerald-400 border-emerald-500/20";
      case "Date":
        return "bg-purple-500/10 text-purple-400 border-purple-500/20";
      default:
        return "bg-blue-500/10 text-blue-400 border-blue-500/20";
    }
  };

  return (
    <div className="space-y-4 animate-in fade-in duration-200">
      {/* Filter toolbar */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-2 border-b border-slate-800">
        <h3 className="text-sm font-semibold uppercase tracking-wider text-slate-400">
          Consolidated Table View ({filteredRows.length} items)
        </h3>

        {/* Filter Chips */}
        <div className="flex items-center gap-1.5 overflow-x-auto text-xs">
          <Filter className="h-3.5 w-3.5 text-slate-500 mr-1 hidden sm:inline" />
          {[
            { id: "all", label: "All" },
            { id: "Key Point", label: "Key Points" },
            { id: "Action", label: "Actions" },
            { id: "Decision", label: "Decisions" },
            { id: "Date", label: "Dates" },
          ].map((tab) => (
            <button
              key={tab.id}
              onClick={() => setFilterType(tab.id)}
              className={`rounded-lg px-2.5 py-1 font-medium transition-colors ${
                filterType === tab.id
                  ? "bg-slate-800 text-white border border-slate-700"
                  : "text-slate-400 hover:text-slate-200 hover:bg-slate-900"
              }`}
            >
              {tab.label}
            </button>
          ))}
        </div>
      </div>

      {/* Table Container */}
      <div className="overflow-x-auto rounded-xl border border-slate-800 bg-slate-900/30">
        <table className="w-full text-left text-xs sm:text-sm">
          <thead className="border-b border-slate-800 bg-slate-900/80 text-xs font-semibold text-slate-400 uppercase tracking-wider">
            <tr>
              <th className="px-4 py-3">Type</th>
              <th className="px-4 py-3">Information</th>
              <th className="px-4 py-3">Person</th>
              <th className="px-4 py-3">Date / Deadline</th>
              <th className="px-4 py-3 text-right">Source</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-800/60">
            {filteredRows.length === 0 ? (
              <tr>
                <td colSpan={5} className="px-4 py-8 text-center text-xs text-slate-400">
                  No matching intelligence items found.
                </td>
              </tr>
            ) : (
              filteredRows.map((row) => (
              <tr
                key={row.id}
                className="hover:bg-slate-900/50 transition-colors group"
              >
                <td className="px-4 py-3.5 whitespace-nowrap align-top">
                  <span
                    className={`inline-flex items-center rounded-md px-2 py-0.5 text-[11px] font-semibold border ${getTypeBadgeStyle(
                      row.type
                    )}`}
                  >
                    {row.typeLabel}
                  </span>
                </td>
                <td className="px-4 py-3.5 text-slate-200 align-top leading-relaxed max-w-md">
                  {row.information}
                </td>
                <td className="px-4 py-3.5 text-slate-300 align-top whitespace-nowrap font-medium">
                  {row.person}
                </td>
                <td className="px-4 py-3.5 text-slate-400 align-top whitespace-nowrap font-mono text-xs">
                  {row.date}
                </td>
                <td className="px-4 py-3.5 text-right align-top whitespace-nowrap">
                  <button
                    onClick={() => onOpenSource(row.source)}
                    className="inline-flex items-center gap-1 rounded-md border border-slate-800 bg-slate-950 px-2 py-1 text-xs text-slate-400 hover:text-blue-300 hover:border-blue-500/40 transition-colors"
                    title="View source citation"
                    aria-label={`View source citation for ${row.typeLabel}: ${row.information.slice(0, 30)}`}
                  >
                    <Info className="h-3.5 w-3.5 text-blue-400" />
                    <span className="hidden md:inline text-[11px]">View</span>
                  </button>
                </td>
              </tr>
            )))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
