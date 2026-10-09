import React from "react";
import { X, Printer, ShieldCheck, UserCheck, AlertTriangle } from "lucide-react";
import { InvestigationData } from "../types";

interface ReportViewModalProps {
  isOpen: boolean;
  onClose: () => void;
  data: InvestigationData;
}

export const ReportViewModal: React.FC<ReportViewModalProps> = ({
  isOpen,
  onClose,
  data,
}) => {
  if (!isOpen) return null;

  const handlePrint = () => {
    window.print();
  };

  const isApproved = data.verdict.code === "ELIGIBLE_FOR_APPROVAL";
  const isReview = data.verdict.code === "FURTHER_REVIEW_REQUIRED";

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-sm p-4 overflow-y-auto">
      <div className="relative my-8 w-full max-w-4xl rounded-2xl border border-slate-700 bg-white text-slate-900 shadow-2xl overflow-hidden print:m-0 print:border-none print:shadow-none">
        {/* Actions Bar (hidden when printing) */}
        <div className="flex items-center justify-between border-b border-slate-200 bg-slate-100 p-4 print:hidden">
          <div className="flex items-center gap-2">
            <ShieldCheck className="h-5 w-5 text-brand-600" />
            <h3 className="font-bold text-sm text-slate-800">
              Credit Investigation Memorandum
            </h3>
          </div>

          <div className="flex items-center gap-2">
            <button
              onClick={handlePrint}
              className="flex items-center gap-1.5 rounded-lg bg-brand-600 px-3 py-1.5 text-xs font-semibold text-white shadow hover:bg-brand-700"
            >
              <Printer className="h-3.5 w-3.5" />
              <span>Print / Export PDF</span>
            </button>
            <button
              onClick={onClose}
              className="rounded-lg p-1.5 text-slate-500 hover:bg-slate-200 hover:text-slate-800"
            >
              <X className="h-5 w-5" />
            </button>
          </div>
        </div>

        {/* Formal Memorandum Body */}
        <div className="p-8 space-y-6 print:p-0">
          {/* Header */}
          <div className="flex justify-between items-start border-b-2 border-slate-900 pb-4">
            <div>
              <h1 className="text-2xl font-extrabold tracking-tight text-slate-950">
                CREDIT RISK INVESTIGATION MEMORANDUM
              </h1>
              <p className="text-xs font-medium text-slate-500 uppercase tracking-wider mt-0.5">
                Decision Support System • TAG Banking Group
              </p>
            </div>
            <div className="text-right text-xs">
              <div><strong>Case ID:</strong> {data.applicant.id}</div>
              <div><strong>Date:</strong> {new Date().toLocaleDateString()}</div>
              <div><strong>System Mode:</strong> {data.mode === "azure" ? "Azure OpenAI Live" : "Offline Engine"}</div>
            </div>
          </div>

          {/* Applicant & Facility */}
          <div className="grid grid-cols-2 gap-4 bg-slate-50 p-4 rounded-xl border border-slate-200 text-xs">
            <div>
              <span className="text-slate-500 block">Applicant Name:</span>
              <strong className="text-sm text-slate-900">{data.applicant.name}</strong>
            </div>
            <div>
              <span className="text-slate-500 block">Requested Facility:</span>
              <strong className="text-sm text-slate-900">{data.applicant.requested_amount} ({data.applicant.loan_tenure_months} months)</strong>
            </div>
            <div>
              <span className="text-slate-500 block">Credit Bureau Score:</span>
              <span className="font-mono font-bold text-slate-800">{data.applicant.credit_score}</span>
            </div>
            <div>
              <span className="text-slate-500 block">Facility Purpose:</span>
              <span className="text-slate-800">{data.applicant.purpose}</span>
            </div>
            <div>
              <span className="text-slate-500 block">Stated Monthly Income:</span>
              <span className="text-slate-800 font-medium">{data.applicant.monthly_income}</span>
            </div>
            <div>
              <span className="text-slate-500 block">Living Expenses & Debt:</span>
              <span className="text-slate-800 font-medium">{data.applicant.monthly_expenses} / {data.applicant.existing_debt}</span>
            </div>
          </div>

          {/* AI Recommendation Box */}
          <div
            className={`p-4 rounded-xl border ${
              isApproved
                ? "border-emerald-300 bg-emerald-50 text-emerald-950"
                : isReview
                ? "border-amber-300 bg-amber-50 text-amber-950"
                : "border-rose-300 bg-rose-50 text-rose-950"
            }`}
          >
            <div className="flex items-center justify-between">
              <span className="text-xs font-bold uppercase tracking-wider">
                System Recommendation
              </span>
              <strong className="text-sm font-extrabold uppercase">
                {data.verdict.label}
              </strong>
            </div>
            <p className="mt-2 text-xs leading-relaxed">
              {data.verdict.reason}
            </p>
            {data.verdict.driver && (
              <p className="mt-2 text-xs font-semibold">
                Primary Driver: {data.verdict.driver.code} — {data.verdict.driver.name} ({data.verdict.driver.reason})
              </p>
            )}
          </div>

          {/* Policy Compliance Matrix Summary */}
          <div>
            <h4 className="text-xs font-bold uppercase tracking-wider text-slate-800 border-b border-slate-200 pb-1 mb-2">
              Policy Compliance Audit (14 Rules Evaluated)
            </h4>
            <div className="grid grid-cols-3 gap-2 text-xs mb-3">
              <div className="p-2 bg-slate-50 rounded border border-slate-200">
                <span className="text-slate-500 block">Passed:</span>
                <strong className="text-emerald-700">{data.rules_summary.pass} rules</strong>
              </div>
              <div className="p-2 bg-slate-50 rounded border border-slate-200">
                <span className="text-slate-500 block">Flagged for Review:</span>
                <strong className="text-amber-700">{data.rules_summary.review} rules</strong>
              </div>
              <div className="p-2 bg-slate-50 rounded border border-slate-200">
                <span className="text-slate-500 block">Knockout / Failures:</span>
                <strong className="text-rose-700">{data.rules_summary.fail} rules</strong>
              </div>
            </div>

            {/* Non-passing rules listing */}
            <div className="space-y-1.5 text-xs">
              {data.rules
                .filter((r) => r.outcome !== "pass")
                .map((r) => (
                  <div key={r.code} className="p-2 bg-slate-50 rounded border border-slate-200">
                    <div className="flex justify-between font-semibold">
                      <span>{r.code}: {r.name}</span>
                      <span className={r.outcome === "fail" ? "text-rose-700" : "text-amber-700"}>
                        {r.outcome.toUpperCase()} (Actual: {r.actual} | Limit: {r.threshold})
                      </span>
                    </div>
                    <p className="text-slate-600 text-[11px] mt-0.5">{r.reason}</p>
                    <p className="text-slate-400 text-[10px] mt-0.5 italic">{r.citation}</p>
                  </div>
                ))}
            </div>
          </div>

          {/* ML Credit Risk Model */}
          {data.ml.available && (
            <div>
              <h4 className="text-xs font-bold uppercase tracking-wider text-slate-800 border-b border-slate-200 pb-1 mb-2">
                Machine Learning Risk Assessment (Supporting Signal)
              </h4>
              <div className="text-xs text-slate-700 flex justify-between bg-slate-50 p-3 rounded-lg border border-slate-200">
                <div>
                  <span>Predicted Probability of Default: </span>
                  <strong className="font-mono">{(data.ml.score * 100).toFixed(1)}%</strong>
                </div>
                <div>
                  <span>Risk Classification: </span>
                  <strong className="uppercase">{data.ml.level.replace("_", " ")}</strong>
                </div>
              </div>
            </div>
          )}

          {/* AI Narrative */}
          <div>
            <h4 className="text-xs font-bold uppercase tracking-wider text-slate-800 border-b border-slate-200 pb-1 mb-2">
              Investigation Narrative ({data.explanation.label})
            </h4>
            <p className="text-xs text-slate-700 leading-relaxed whitespace-pre-line">
              {data.explanation.text}
            </p>
          </div>

          {/* Analyst Sign-off Block */}
          <div className="border-t-2 border-slate-900 pt-4 grid grid-cols-2 gap-8 text-xs">
            <div>
              <div className="flex items-center gap-1.5 font-bold text-slate-900 mb-4">
                <UserCheck className="h-4 w-4 text-brand-600" />
                <span>Human Decision Ownership</span>
              </div>
              <p className="text-slate-500 text-[11px] leading-relaxed">
                This report is generated for decision support. The credit underwriter holds ultimate responsibility for lending approvals and policy exceptions.
              </p>
            </div>
            <div className="space-y-4">
              <div className="border-b border-slate-400 pb-1">
                <span className="text-slate-500 text-[10px] block">Credit Analyst Signature:</span>
                <div className="h-6"></div>
              </div>
              <div className="border-b border-slate-400 pb-1">
                <span className="text-slate-500 text-[10px] block">Risk Supervisor Approval:</span>
                <div className="h-6"></div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
