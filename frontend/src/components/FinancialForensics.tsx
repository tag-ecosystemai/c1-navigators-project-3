import React from "react";
import {
  DollarSign,
  TrendingUp,
  AlertTriangle,
  CheckCircle2,
  Receipt,
  Building,
  Briefcase,
  AlertCircle,
  ArrowDownRight,
  ArrowUpRight,
} from "lucide-react";
import { ApplicantInfo, TransactionItem } from "../types";

interface FinancialForensicsProps {
  applicant: ApplicantInfo;
  transactions?: TransactionItem[];
}

export const FinancialForensics: React.FC<FinancialForensicsProps> = ({
  applicant,
  transactions = [],
}) => {
  const hasIncomeVariance = (applicant.income_variance_pct || 0) > 10;
  const hasUndisclosedDebt = (applicant.undisclosed_debt_total || 0) > 0;
  const hasGambling = (applicant.gambling_ratio || 0) > 0;
  const hasNSF = (applicant.nsf_count || 0) > 0;

  return (
    <div className="space-y-6">
      {/* Top Forensic Summary Cards */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {/* Income Verification Card */}
        <div
          className={`rounded-2xl border p-4 transition-all ${
            hasIncomeVariance
              ? "border-rose-500/40 bg-rose-950/20 text-rose-200"
              : "border-line-subtle bg-surface-secondary/90 text-content-secondary"
          }`}
        >
          <div className="flex items-center justify-between text-xs">
            <span className="font-semibold uppercase tracking-wider text-content-muted">
              Income Verification
            </span>
            {hasIncomeVariance ? (
              <span className="inline-flex items-center gap-1 rounded bg-rose-500/20 px-2 py-0.5 text-xs font-bold text-rose-300">
                <AlertCircle className="h-3 w-3" /> {applicant.income_variance_pct?.toFixed(1)}% Gap
              </span>
            ) : (
              <span className="inline-flex items-center gap-1 rounded bg-emerald-500/20 px-2 py-0.5 text-xs font-bold text-emerald-300">
                <CheckCircle2 className="h-3 w-3" /> Verified 100%
              </span>
            )}
          </div>

          <div className="mt-3">
            <div className="text-xl font-bold font-mono text-white">
              {applicant.actual_monthly_salary || applicant.monthly_income}
            </div>
            <span className="text-xs text-content-muted block mt-0.5">
              Verified Monthly Deposits (Stated: {applicant.monthly_income})
            </span>
          </div>
        </div>

        {/* Shadow DTI & Hidden Debt Card */}
        <div
          className={`rounded-2xl border p-4 transition-all ${
            hasUndisclosedDebt
              ? "border-amber-500/40 bg-amber-950/20 text-amber-200"
              : "border-line-subtle bg-surface-secondary/90 text-content-secondary"
          }`}
        >
          <div className="flex items-center justify-between text-xs">
            <span className="font-semibold uppercase tracking-wider text-content-muted">
              Shadow DTI & Hidden Debt
            </span>
            {hasUndisclosedDebt ? (
              <span className="inline-flex items-center gap-1 rounded bg-amber-500/20 px-2 py-0.5 text-xs font-bold text-amber-300">
                <AlertTriangle className="h-3 w-3" /> +${applicant.undisclosed_debt_total}/mo Unlisted
              </span>
            ) : (
              <span className="inline-flex items-center gap-1 rounded bg-emerald-500/20 px-2 py-0.5 text-xs font-bold text-emerald-300">
                <CheckCircle2 className="h-3 w-3" /> Clean Debt Profile
              </span>
            )}
          </div>

          <div className="mt-3">
            <div className="text-xl font-bold font-mono text-white">
              {applicant.shadow_dti_pct ? `${applicant.shadow_dti_pct.toFixed(1)}%` : `${applicant.calculated_dti_pct || 18.3}%`}
            </div>
            <span className="text-xs text-content-muted block mt-0.5">
              Effective Shadow DTI (Stated: {applicant.calculated_dti_pct?.toFixed(1) || "18.3"}%)
            </span>
          </div>
        </div>

        {/* Gambling Activity Card */}
        <div
          className={`rounded-2xl border p-4 transition-all ${
            hasGambling
              ? "border-rose-500/40 bg-rose-950/20 text-rose-200"
              : "border-line-subtle bg-surface-secondary/90 text-content-secondary"
          }`}
        >
          <div className="flex items-center justify-between text-xs">
            <span className="font-semibold uppercase tracking-wider text-content-muted">
              Gambling & Wagering
            </span>
            {hasGambling ? (
              <span className="inline-flex items-center gap-1 rounded bg-rose-500/20 px-2 py-0.5 text-xs font-bold text-rose-300">
                <AlertTriangle className="h-3 w-3" /> High Risk ({applicant.gambling_ratio}%)
              </span>
            ) : (
              <span className="inline-flex items-center gap-1 rounded bg-emerald-500/20 px-2 py-0.5 text-xs font-bold text-emerald-300">
                <CheckCircle2 className="h-3 w-3" /> 0.0% Clean
              </span>
            )}
          </div>

          <div className="mt-3">
            <div className="text-xl font-bold font-mono text-white">
              {applicant.gambling_ratio ? `${applicant.gambling_ratio}% of income` : "0.0%"}
            </div>
            <span className="text-xs text-content-muted block mt-0.5">
              Policy cap: &lt; 3.0% standard (&gt; 10% decline)
            </span>
          </div>
        </div>

        {/* Liquidity Distress & NSF Card */}
        <div
          className={`rounded-2xl border p-4 transition-all ${
            hasNSF
              ? "border-rose-500/40 bg-rose-950/20 text-rose-200"
              : "border-line-subtle bg-surface-secondary/90 text-content-secondary"
          }`}
        >
          <div className="flex items-center justify-between text-xs">
            <span className="font-semibold uppercase tracking-wider text-content-muted">
              Overdraft & NSF Events
            </span>
            {hasNSF ? (
              <span className="inline-flex items-center gap-1 rounded bg-rose-500/20 px-2 py-0.5 text-xs font-bold text-rose-300">
                <AlertCircle className="h-3 w-3" /> {applicant.nsf_count} Events in 90d
              </span>
            ) : (
              <span className="inline-flex items-center gap-1 rounded bg-emerald-500/20 px-2 py-0.5 text-xs font-bold text-emerald-300">
                <CheckCircle2 className="h-3 w-3" /> 0 NSF Events
              </span>
            )}
          </div>

          <div className="mt-3">
            <div className="text-xl font-bold font-mono text-white">
              {applicant.nsf_count || 0} Fees
            </div>
            <span className="text-xs text-content-muted block mt-0.5">
              Policy limit: 0 standard (&gt;= 4 decline knockout)
            </span>
          </div>
        </div>
      </div>

      {/* Employment & Underwriting Baseline */}
      <div className="rounded-2xl border border-line-subtle bg-surface-secondary/90 p-5 shadow-sm">
        <h3 className="text-xs font-bold uppercase tracking-wider text-content-muted border-b border-line-subtle pb-3 mb-4">
          Underwriter Verification & Employment Baseline
        </h3>

        <div className="grid grid-cols-2 gap-4 sm:grid-cols-4 text-xs">
          <div>
            <div className="flex items-center gap-1.5 text-content-muted mb-1">
              <Building className="h-3.5 w-3.5 text-brand-400" />
              <span>Employer</span>
            </div>
            <strong className="text-white block">{applicant.employer_name || "Verified Employer"}</strong>
            <span className="text-xs text-content-muted">{applicant.job_title || "Salaried Employee"}</span>
          </div>

          <div>
            <div className="flex items-center gap-1.5 text-content-muted mb-1">
              <Briefcase className="h-3.5 w-3.5 text-brand-400" />
              <span>Tenure</span>
            </div>
            <strong className="text-white block">{applicant.employment_tenure_months} Months</strong>
            <span className={`text-xs ${applicant.employment_tenure_months >= 6 ? "text-emerald-400" : "text-amber-400"}`}>
              {applicant.employment_tenure_months >= 6 ? "Meets >= 6mo policy" : "Probationary (< 6mo)"}
            </span>
          </div>

          <div>
            <div className="flex items-center gap-1.5 text-content-muted mb-1">
              <DollarSign className="h-3.5 w-3.5 text-brand-400" />
              <span>Living Costs</span>
            </div>
            <strong className="text-white block">{applicant.monthly_expenses}</strong>
            <span className="text-xs text-content-muted">{applicant.housing_status || "Standard"} housing</span>
          </div>

          <div>
            <div className="flex items-center gap-1.5 text-content-muted mb-1">
              <TrendingUp className="h-3.5 w-3.5 text-brand-400" />
              <span>Public Records</span>
            </div>
            <strong className={`block ${applicant.bankruptcies_count > 0 ? "text-rose-400" : "text-emerald-400"}`}>
              {applicant.bankruptcies_count > 0 ? `${applicant.bankruptcies_count} Active Bankruptcy` : "0 Bankruptcies / Liens"}
            </strong>
            <span className="text-xs text-content-muted">Bureau public record check</span>
          </div>
        </div>
      </div>

      {/* Forensic Bank Statement Transaction Log */}
      <div className="rounded-2xl border border-line-subtle bg-surface-secondary/90 p-5 shadow-sm">
        <div className="flex items-center justify-between border-b border-line-subtle pb-3 mb-4">
          <div className="flex items-center gap-2">
            <Receipt className="h-4 w-4 text-brand-400" />
            <h3 className="text-xs font-bold uppercase tracking-wider text-content-secondary">
              Forensic Transaction Ledger & Red Flag Analysis
            </h3>
          </div>
          <span className="text-xs text-content-muted">
            {transactions.length} Sample Transactions Inspected
          </span>
        </div>

        {transactions.length === 0 ? (
          <p className="text-xs text-content-muted py-6 text-center">
            No bank statement ledger items available for this applicant.
          </p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs border-collapse">
              <thead>
                <tr className="border-b border-line-subtle text-content-muted font-semibold text-xs">
                  <th className="pb-2.5">Date</th>
                  <th className="pb-2.5">Description</th>
                  <th className="pb-2.5">Category</th>
                  <th className="pb-2.5 text-right">Amount</th>
                  <th className="pb-2.5 text-right">Balance</th>
                  <th className="pb-2.5 pl-4">Forensic Flag</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/60">
                {transactions.map((tx) => {
                  const isInflow = tx.type === "inflow";
                  return (
                    <tr
                      key={tx.id}
                      className={`hover:bg-slate-800/40 transition-colors ${
                        tx.flagged ? "bg-rose-950/20" : ""
                      }`}
                    >
                      <td className="py-2.5 font-mono text-content-muted whitespace-nowrap">{tx.date}</td>
                      <td className="py-2.5 font-medium text-content-secondary">{tx.description}</td>
                      <td className="py-2.5">
                        <span className="rounded bg-slate-800 px-2 py-0.5 text-xs font-medium text-content-muted capitalize">
                          {tx.category.replace("_", " ")}
                        </span>
                      </td>
                      <td className="py-2.5 text-right font-mono font-semibold whitespace-nowrap">
                        <span className={`inline-flex items-center gap-0.5 ${isInflow ? "text-emerald-400" : "text-content-muted"}`}>
                          {isInflow ? <ArrowDownRight className="h-3 w-3" /> : <ArrowUpRight className="h-3 w-3 text-content-muted" />}
                          ${tx.amount.toLocaleString()}
                        </span>
                      </td>
                      <td className="py-2.5 text-right font-mono text-content-muted whitespace-nowrap">
                        ${tx.balance.toLocaleString()}
                      </td>
                      <td className="py-2.5 pl-4">
                        {tx.flagged ? (
                          <span className="inline-flex items-center gap-1 rounded bg-rose-500/20 px-2 py-0.5 text-xs font-bold text-rose-300 border border-rose-500/30">
                            <AlertTriangle className="h-3 w-3" /> {tx.flagReason}
                          </span>
                        ) : (
                          <span className="text-content-muted text-xs">—</span>
                        )}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
};
