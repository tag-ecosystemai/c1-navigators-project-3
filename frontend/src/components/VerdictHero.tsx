import React from "react";
import {
  CheckCircle2,
  AlertTriangle,
  XCircle,
  ShieldAlert,
  UserCheck,
  ArrowRight,
  FileText,
  BadgeAlert,
} from "lucide-react";
import { Verdict, ApplicantInfo } from "../types";

interface VerdictHeroProps {
  verdict: Verdict;
  applicant: ApplicantInfo;
  onOpenReport: () => void;
  onScrollToRules: () => void;
}

export const VerdictHero: React.FC<VerdictHeroProps> = ({
  verdict,
  applicant,
  onOpenReport,
  onScrollToRules,
}) => {
  const isApproved = verdict.code === "ELIGIBLE_FOR_APPROVAL";
  const isReview = verdict.code === "FURTHER_REVIEW_REQUIRED";
  const isDecline = verdict.code === "DECLINE_RECOMMENDED";

  return (
    <div
      className={`relative overflow-hidden rounded-2xl border p-6 shadow-xl transition-all ${
        isApproved
          ? "border-emerald-500/40 bg-gradient-to-br from-[#0c2419]/90 via-[#0c1828]/95 to-[#07111f] shadow-emerald-950/30"
          : isReview
          ? "border-amber-500/40 bg-gradient-to-br from-[#2a1d08]/90 via-[#0c1828]/95 to-[#07111f] shadow-amber-950/30"
          : "border-rose-500/40 bg-gradient-to-br from-[#280c13]/90 via-[#0c1828]/95 to-[#07111f] shadow-rose-950/30"
      }`}
    >
      <div className="flex flex-col gap-6 lg:flex-row lg:items-center lg:justify-between">
        {/* Left Side: Verdict Badge & Rationale */}
        <div className="space-y-4 max-w-2xl">
          <div className="flex flex-wrap items-center gap-2.5">
            <span
              className={`inline-flex items-center gap-2 rounded-full px-4 py-1.5 text-sm font-bold tracking-wide shadow-sm uppercase ${
                isApproved
                  ? "bg-emerald-500 text-white shadow-emerald-500/30"
                  : isReview
                  ? "bg-amber-500 text-slate-950 shadow-amber-500/30"
                  : "bg-rose-600 text-white shadow-rose-600/30"
              }`}
            >
              {isApproved && <CheckCircle2 className="h-4 w-4" />}
              {isReview && <AlertTriangle className="h-4 w-4" />}
              {isDecline && <XCircle className="h-4 w-4" />}
              {verdict.label}
            </span>

            <span className="inline-flex items-center gap-1.5 rounded-full border border-slate-700 bg-slate-800/80 px-3 py-1 text-xs text-slate-300">
              <UserCheck className="h-3.5 w-3.5 text-brand-400" />
              <span>{verdict.note}</span>
            </span>
          </div>

          <div>
            <h1 className="text-2xl font-bold tracking-tight text-white sm:text-3xl">
              {applicant.name}
            </h1>
            <p className="mt-1 text-sm text-slate-300 leading-relaxed">
              {verdict.reason}
            </p>
          </div>

          {/* Primary Driver Banner */}
          {verdict.driver && (
            <div
              className={`flex items-start gap-3 rounded-xl border p-3.5 ${
                isDecline
                  ? "border-rose-500/30 bg-rose-950/30 text-rose-200"
                  : "border-amber-500/30 bg-amber-950/30 text-amber-200"
              }`}
            >
              <div className="mt-0.5 flex h-6 w-6 shrink-0 items-center justify-center rounded-lg bg-rose-500/20 text-rose-400">
                <BadgeAlert className="h-4 w-4" />
              </div>
              <div className="flex-1">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-bold uppercase tracking-wider">
                    Primary Decision Driver: {verdict.driver.code} - {verdict.driver.name}
                  </span>
                  <button
                    onClick={onScrollToRules}
                    className="flex items-center gap-1 text-xs font-semibold underline underline-offset-2 hover:opacity-80 transition-opacity"
                  >
                    View in Matrix <ArrowRight className="h-3 w-3" />
                  </button>
                </div>
                <p className="mt-0.5 text-xs opacity-90 leading-relaxed">
                  {verdict.driver.reason}
                </p>
              </div>
            </div>
          )}

          {isApproved && (
            <div className="flex items-center gap-2 rounded-xl border border-emerald-500/30 bg-emerald-950/30 p-3 text-xs text-emerald-200">
              <CheckCircle2 className="h-4 w-4 text-emerald-400 shrink-0" />
              <span>All 14 lending policy checks, affordability buffers, and fraud investigations satisfied.</span>
            </div>
          )}
        </div>

        {/* Right Side: Quick Action & Financial Snapshot */}
        <div className="flex flex-col gap-4 lg:w-80 shrink-0">
          <div className="rounded-xl border border-slate-800 bg-[#07111f]/80 p-4">
            <span className="text-[11px] font-bold uppercase tracking-wider text-slate-400 block mb-3">
              Applicant Profile & Facility
            </span>
            <div className="grid grid-cols-2 gap-3 text-xs">
              <div>
                <span className="text-slate-400 block text-[10px]">Requested Facility</span>
                <strong className="text-white text-sm font-semibold">{applicant.requested_amount}</strong>
                <span className="text-slate-400 block text-[10px]">{applicant.loan_tenure_months} mo. tenure</span>
              </div>
              <div>
                <span className="text-slate-400 block text-[10px]">Credit Bureau Score</span>
                <strong className={`text-sm font-bold font-mono ${applicant.credit_score >= 680 ? "text-emerald-400" : applicant.credit_score >= 600 ? "text-amber-400" : "text-rose-400"}`}>
                  {applicant.credit_score}
                </strong>
                <span className="text-slate-400 block text-[10px]">{applicant.purpose}</span>
              </div>
              <div className="border-t border-slate-800 pt-2">
                <span className="text-slate-400 block text-[10px]">Stated Income</span>
                <span className="text-slate-200 font-semibold">{applicant.monthly_income}</span>
              </div>
              <div className="border-t border-slate-800 pt-2">
                <span className="text-slate-400 block text-[10px]">Living Expenses</span>
                <span className="text-slate-200 font-semibold">{applicant.monthly_expenses}</span>
              </div>
            </div>
          </div>

          <button
            onClick={onOpenReport}
            className="flex w-full items-center justify-center gap-2 rounded-xl bg-gradient-to-r from-brand-600 to-blue-600 px-4 py-3 text-xs font-bold text-white shadow-lg shadow-brand-600/20 transition-all hover:from-brand-500 hover:to-blue-500 hover:shadow-brand-500/30"
          >
            <FileText className="h-4 w-4" />
            <span>Generate Formal Credit Memorandum</span>
          </button>
        </div>
      </div>
    </div>
  );
};
