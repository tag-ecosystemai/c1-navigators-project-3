import React from "react";
import { AlertTriangle, ArrowRight, BookOpen, CheckCircle2, FileText, Search, TrendingUp, XCircle } from "lucide-react";
import { InvestigationData } from "../types";

interface CaseOverviewProps {
  data: InvestigationData;
  onOpenMemo: () => void;
  onOpenRules: () => void;
  onOpenForensics: () => void;
  onOpenMl: () => void;
  onViewDriver: (ruleCode: string) => void;
}

export const CaseOverview: React.FC<CaseOverviewProps> = ({
  data,
  onOpenMemo,
  onOpenRules,
  onOpenForensics,
  onOpenMl,
  onViewDriver,
}) => {
  const { applicant, verdict, rules_summary: rulesSummary, ml } = data;
  const approved = verdict.code === "ELIGIBLE_FOR_APPROVAL";
  const review = verdict.code === "FURTHER_REVIEW_REQUIRED";
  const VerdictIcon = approved ? CheckCircle2 : review ? AlertTriangle : XCircle;
  const tone = approved ? "border-emerald-500/35 bg-emerald-950/20" : review ? "border-amber-500/35 bg-amber-950/20" : "border-rose-500/35 bg-rose-950/20";
  const badge = approved ? "bg-emerald-500 text-white" : review ? "bg-amber-500 text-slate-950" : "bg-rose-600 text-white";

  return (
    <section aria-labelledby="case-overview-title" className="space-y-5">
      <div className={`rounded-2xl border p-5 sm:p-6 ${tone}`}>
        <div className="flex flex-col gap-5 lg:flex-row lg:items-start lg:justify-between">
          <div className="max-w-3xl">
            <div className="flex flex-wrap items-center gap-2">
              <span className={`inline-flex items-center gap-2 rounded-full px-3 py-1.5 text-xs font-bold uppercase tracking-wide ${badge}`}>
                <VerdictIcon className="h-4 w-4" /> {verdict.label}
              </span>
              <span className="rounded-full border border-line-muted bg-surface-elevated px-2.5 py-1 text-xs text-content-muted">Human decision required</span>
            </div>
            <h1 id="case-overview-title" className="mt-4 text-2xl font-bold tracking-tight text-content-primary sm:text-3xl">{applicant.name}</h1>
            <p className="mt-2 max-w-2xl text-sm leading-relaxed text-content-secondary">{verdict.reason}</p>
            {verdict.driver && (
              <div className="mt-4 flex flex-col gap-3 rounded-xl border border-line-muted bg-surface-primary/60 p-3 sm:flex-row sm:items-center sm:justify-between">
                <div>
                  <p className="text-xs font-bold uppercase tracking-wider text-content-muted">Primary decision driver</p>
                  <p className="mt-1 text-sm font-semibold text-content-primary">{verdict.driver.code} · {verdict.driver.name}</p>
                  <p className="mt-1 text-xs text-content-muted">{verdict.driver.reason}</p>
                </div>
                <button onClick={() => onViewDriver(verdict.driver!.code)} className="inline-flex shrink-0 items-center justify-center gap-1 rounded-lg border border-brand-500/40 px-3 py-2 text-xs font-semibold text-brand-300 hover:bg-brand-950/40">
                  Review rule <ArrowRight className="h-3.5 w-3.5" />
                </button>
              </div>
            )}
          </div>
          <button onClick={onOpenMemo} className="inline-flex shrink-0 items-center justify-center gap-2 rounded-xl bg-brand-600 px-4 py-3 text-xs font-bold text-white shadow-lg shadow-brand-900/20 hover:bg-brand-500">
            <FileText className="h-4 w-4" /> Open credit memo
          </button>
        </div>
      </div>

      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        <div className="rounded-xl border border-line-subtle bg-surface-secondary p-4"><p className="text-xs text-content-muted">Requested facility</p><p className="mt-1 text-lg font-bold text-content-primary">{applicant.requested_amount}</p><p className="text-xs text-content-muted">{applicant.loan_tenure_months} month term</p></div>
        <div className="rounded-xl border border-line-subtle bg-surface-secondary p-4"><p className="text-xs text-content-muted">Credit bureau score</p><p className="mt-1 text-lg font-bold text-content-primary">{applicant.credit_score}</p><p className="text-xs text-content-muted">{applicant.purpose}</p></div>
        <div className="rounded-xl border border-line-subtle bg-surface-secondary p-4"><p className="text-xs text-content-muted">Policy findings</p><p className="mt-1 text-lg font-bold text-content-primary">{rulesSummary.fail + rulesSummary.review}</p><p className="text-xs text-content-muted">{rulesSummary.fail} fail · {rulesSummary.review} review</p></div>
        <div className="rounded-xl border border-line-subtle bg-surface-secondary p-4"><p className="text-xs text-content-muted">Default probability</p><p className="mt-1 text-lg font-bold text-content-primary">{ml.available ? `${(ml.score * 100).toFixed(1)}%` : "Unavailable"}</p><p className="text-xs text-content-muted">{ml.available ? ml.level.replace("_", " ") : "Supporting signal"}</p></div>
      </div>

      <div className="rounded-2xl border border-line-subtle bg-surface-secondary p-4 sm:p-5">
        <h2 className="text-sm font-bold text-content-primary">Review the evidence</h2>
        <p className="mt-1 text-xs text-content-muted">Open only the evidence needed for this decision.</p>
        <div className="mt-4 grid gap-3 sm:grid-cols-3">
          <button onClick={onOpenRules} className="group rounded-xl border border-line-subtle p-4 text-left hover:border-brand-500/50 hover:bg-surface-elevated"><BookOpen className="h-5 w-5 text-brand-400" /><p className="mt-3 text-sm font-semibold text-content-primary">Policy rules</p><p className="mt-1 text-xs text-content-muted">{data.rules.length} evaluated policy checks</p></button>
          <button onClick={onOpenForensics} className="group rounded-xl border border-line-subtle p-4 text-left hover:border-brand-500/50 hover:bg-surface-elevated"><Search className="h-5 w-5 text-brand-400" /><p className="mt-3 text-sm font-semibold text-content-primary">Transaction forensics</p><p className="mt-1 text-xs text-content-muted">Income, debt, spending and ledger review</p></button>
          <button onClick={onOpenMl} className="group rounded-xl border border-line-subtle p-4 text-left hover:border-brand-500/50 hover:bg-surface-elevated"><TrendingUp className="h-5 w-5 text-brand-400" /><p className="mt-3 text-sm font-semibold text-content-primary">Risk signals</p><p className="mt-1 text-xs text-content-muted">Model drivers and policy cross-check</p></button>
        </div>
      </div>
    </section>
  );
};
