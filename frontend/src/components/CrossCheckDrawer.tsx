import React from "react";
import { Scale, CheckCircle2, AlertTriangle, ShieldCheck } from "lucide-react";
import { CrossCheck } from "../types";

interface CrossCheckDrawerProps {
  crossCheck: CrossCheck;
}

export const CrossCheckDrawer: React.FC<CrossCheckDrawerProps> = ({ crossCheck }) => {
  if (!crossCheck.available) {
    return (
      <div className="rounded-2xl border border-line-subtle bg-surface-secondary/90 p-5">
        <div className="flex items-center justify-between border-b border-line-subtle pb-3">
          <div className="flex items-center gap-2">
            <Scale className="h-4 w-4 text-brand-400" />
            <h3 className="text-xs font-bold uppercase tracking-wider text-content-secondary">
              Policy RAG Cross-Check
            </h3>
          </div>
          <span className="rounded-full border border-line-muted bg-slate-800 px-2 py-0.5 text-[10px] text-content-muted">
            Offline Mode
          </span>
        </div>
        <p className="mt-3 text-xs text-content-muted">
          Azure OpenAI cross-check is skipped in offline mode. The investigation relies directly on the deterministic policy evaluator.
        </p>
      </div>
    );
  }

  const hasConflicts = crossCheck.conflicts && crossCheck.conflicts.length > 0;

  return (
    <div className="rounded-2xl border border-line-subtle bg-surface-secondary/90 p-5 shadow-sm">
      <div className="flex items-center justify-between border-b border-line-subtle pb-3">
        <div className="flex items-center gap-2">
          <Scale className="h-4 w-4 text-brand-400" />
          <h3 className="text-xs font-bold uppercase tracking-wider text-content-secondary">
            Policy Checker vs Rule Evaluator
          </h3>
        </div>
        <span className="inline-flex items-center gap-1 rounded-full border border-emerald-500/30 bg-emerald-500/10 px-2.5 py-0.5 text-[11px] font-semibold text-emerald-300">
          <ShieldCheck className="h-3 w-3" />
          {crossCheck.compared}/{crossCheck.total_rules} Rules Compared
        </span>
      </div>

      <div className="mt-4">
        {!hasConflicts ? (
          <div className="rounded-xl border border-emerald-500/30 bg-emerald-950/20 p-3.5 text-xs text-emerald-200 flex items-start gap-2.5">
            <CheckCircle2 className="h-4 w-4 text-emerald-400 shrink-0 mt-0.5" />
            <div>
              <strong className="font-semibold block">Full Policy Agreement</strong>
              <p className="mt-0.5 text-[11px] opacity-90">
                Azure OpenAI RAG checker and the deterministic rule evaluator agree on all {crossCheck.compared} verified clauses.
              </p>
            </div>
          </div>
        ) : (
          <div className="space-y-3">
            <div className="rounded-xl border border-amber-500/30 bg-amber-950/20 p-3 text-xs text-amber-200 flex items-start gap-2">
              <AlertTriangle className="h-4 w-4 text-amber-400 shrink-0 mt-0.5" />
              <div>
                <strong>Interpretation Differences Identified</strong>
                <p className="mt-0.5 text-[11px] opacity-90">
                  The LLM identified nuanced policy criteria requiring human analyst review.
                </p>
              </div>
            </div>

            <div className="space-y-2">
              {crossCheck.conflicts.map((conflict, idx) => (
                <div
                  key={conflict.rule || idx}
                  className="rounded-lg border border-line-subtle bg-slate-900/60 p-2.5 text-xs space-y-1.5"
                >
                  <div className="flex items-center justify-between">
                    <span className="font-mono font-bold text-brand-300">{conflict.rule}</span>
                    <div className="flex items-center gap-2 text-[10px]">
                      <span className="text-content-muted">Engine: <strong className="text-content-secondary">{conflict.evaluator}</strong></span>
                      <span className="text-content-muted">RAG: <strong className="text-amber-300">{conflict.rag}</strong></span>
                    </div>
                  </div>
                  <p className="text-[11px] text-content-muted italic">{conflict.notes}</p>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
