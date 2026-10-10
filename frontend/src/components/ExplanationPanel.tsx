import React, { useState } from "react";
import { Sparkles, CheckSquare, Square, AlertCircle, CheckCircle2 } from "lucide-react";
import { Explanation, ChecklistItem } from "../types";

interface ExplanationPanelProps {
  explanation: Explanation;
  checklist: ChecklistItem[];
  dataGaps: string[];
}

export const ExplanationPanel: React.FC<ExplanationPanelProps> = ({
  explanation,
  checklist: initialChecklist,
  dataGaps,
}) => {
  const [checkedItems, setCheckedItems] = useState<Record<string, boolean>>({});

  const toggleCheck = (id: string) => {
    setCheckedItems((prev) => ({ ...prev, [id]: !prev[id] }));
  };

  const isAzure = explanation.source === "azure";

  return (
    <div className="space-y-5">
      {/* AI Explanation Narrative */}
      <div className="rounded-2xl border border-line-subtle bg-surface-secondary/90 p-5 shadow-sm">
        <div className="flex items-center justify-between border-b border-line-subtle pb-3">
          <div className="flex items-center gap-2">
            <Sparkles className="h-4 w-4 text-brand-400" />
            <h3 className="text-xs font-bold uppercase tracking-wider text-content-secondary">
              Investigation Narrative & Risk Assessment
            </h3>
          </div>
          <span
            className={`rounded-full border px-2.5 py-0.5 text-xs font-medium ${
              isAzure
                ? "border-emerald-500/30 bg-emerald-500/10 text-emerald-300"
                : "border-line-muted bg-slate-800 text-content-muted"
            }`}
          >
            {explanation.label}
          </span>
        </div>

        <div className="mt-4 prose prose-invert max-w-none text-xs text-content-muted leading-relaxed whitespace-pre-line">
          {explanation.text}
        </div>
      </div>

      {/* Credit Analyst Action Checklist */}
      <div className="rounded-2xl border border-line-subtle bg-surface-secondary/90 p-5 shadow-sm">
        <div className="flex items-center justify-between border-b border-line-subtle pb-3">
          <div className="flex items-center gap-2">
            <CheckSquare className="h-4 w-4 text-brand-400" />
            <h3 className="text-xs font-bold uppercase tracking-wider text-content-secondary">
              Analyst Action Checklist & Verification
            </h3>
          </div>
          <span className="text-xs text-content-muted">
            {Object.values(checkedItems).filter(Boolean).length}/{initialChecklist.length} Completed
          </span>
        </div>

        <div className="mt-4 space-y-2.5">
          {initialChecklist.map((item, idx) => {
            const isDone = !!checkedItems[item.id || `check-${idx}`];
            const priorityBadge =
              item.priority === "high"
                ? "border-rose-500/30 bg-rose-500/10 text-rose-300"
                : item.priority === "medium"
                ? "border-amber-500/30 bg-amber-500/10 text-amber-300"
                : "border-line-muted bg-slate-800 text-content-muted";

            return (
              <div
                key={item.id || idx}
                onClick={() => toggleCheck(item.id || `check-${idx}`)}
                onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); toggleCheck(item.id || `check-${idx}`); } }}
                role="checkbox"
                tabIndex={0}
                aria-checked={isDone}
                aria-label={item.text}
                className={`flex items-start gap-3 rounded-xl border p-3 text-xs cursor-pointer transition-all ${
                  isDone
                    ? "border-emerald-500/30 bg-emerald-950/10 text-content-muted opacity-70"
                    : "border-line-subtle/80 bg-surface-elevated/60 hover:border-line-muted"
                }`}
              >
                <button className="mt-0.5 text-brand-400 focus:outline-none">
                  {isDone ? (
                    <CheckCircle2 className="h-4 w-4 text-emerald-400" />
                  ) : (
                    <Square className="h-4 w-4 text-slate-500" />
                  )}
                </button>

                <div className="flex-1">
                  <p className={`leading-relaxed ${isDone ? "line-through text-content-muted" : "text-content-secondary"}`}>
                    {item.text}
                  </p>
                </div>

                <span className={`shrink-0 rounded-full border px-2 py-0.5 text-xs uppercase font-bold tracking-wider ${priorityBadge}`}>
                  {item.priority}
                </span>
              </div>
            );
          })}
        </div>
      </div>

      {/* Missing Data Gaps Warning (if any) */}
      {dataGaps && dataGaps.length > 0 && (
        <div className="rounded-2xl border border-amber-500/30 bg-amber-950/20 p-4 text-xs text-amber-200">
          <div className="flex items-center gap-2 font-semibold text-amber-300 mb-2">
            <AlertCircle className="h-4 w-4" />
            <span>Identified Data Gaps for Underwriter Review</span>
          </div>
          <ul className="list-disc pl-5 space-y-1 text-xs opacity-90">
            {dataGaps.map((gap, idx) => (
              <li key={idx}>{gap}</li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
};
