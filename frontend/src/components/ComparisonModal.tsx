import React, { useEffect, useState } from "react";
import { X, Scale, CheckCircle2, AlertTriangle, XCircle, ArrowRight, Loader2 } from "lucide-react";
import { Persona, InvestigationData } from "../types";
import { investigateApplicant } from "../api/client";

interface ComparisonModalProps {
  isOpen: boolean;
  onClose: () => void;
  personas: Persona[];
  onSelectPersona: (id: string) => void;
}

export const ComparisonModal: React.FC<ComparisonModalProps> = ({
  isOpen,
  onClose,
  personas,
  onSelectPersona,
}) => {
  const [dataMap, setDataMap] = useState<Record<string, InvestigationData>>({});
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!isOpen) return;

    let isMounted = true;
    setLoading(true);

    // Fetch all 5 personas in parallel
    Promise.allSettled(
      personas.map((p) => investigateApplicant(p.id, false, false))
    ).then((results) => {
      if (!isMounted) return;
      const map: Record<string, InvestigationData> = {};
      results.forEach((res, idx) => {
        if (res.status === "fulfilled") {
          map[personas[idx].id] = res.value;
        }
      });
      setDataMap(map);
      setLoading(false);
    });

    return () => {
      isMounted = false;
    };
  }, [isOpen, personas]);

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-sm p-4" role="dialog" aria-modal="true" aria-labelledby="comparison-modal-title">
      <div className="relative flex max-h-[90vh] w-full max-w-6xl flex-col rounded-2xl border border-line-muted bg-surface-secondary shadow-2xl overflow-hidden">
        {/* Header */}
        <div className="flex items-center justify-between border-b border-line-subtle p-5">
          <div className="flex items-center gap-3">
            <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-brand-500/20 text-brand-400">
              <Scale className="h-5 w-5" />
            </div>
            <div>
              <h2 className="text-lg font-bold text-white">Side-by-Side Persona Comparison</h2>
              <p className="text-xs text-content-muted">
                Compare lending outcomes, risk scores, and policy drivers across all 5 test cases
              </p>
            </div>
          </div>

          <button
            onClick={onClose}
            className="rounded-lg p-2 text-content-muted hover:bg-slate-800 hover:text-white transition-colors"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-auto p-5">
          {loading ? (
            <div className="flex flex-col items-center justify-center py-20 text-content-muted gap-3">
              <Loader2 className="h-8 w-8 animate-spin text-brand-400" />
              <p className="text-sm">Running side-by-side policy & ML evaluations...</p>
            </div>
          ) : (
            <div className="grid grid-cols-1 gap-4 md:grid-cols-5">
              {personas.map((persona) => {
                const data = dataMap[persona.id];
                if (!data) return null;

                const isApproved = data.verdict.code === "ELIGIBLE_FOR_APPROVAL";
                const isReview = data.verdict.code === "FURTHER_REVIEW_REQUIRED";
                const isDecline = data.verdict.code === "DECLINE_RECOMMENDED";

                return (
                  <div
                    key={persona.id}
                    className="flex flex-col justify-between rounded-xl border border-line-subtle bg-surface-elevated/70 p-4 text-xs space-y-4"
                  >
                    {/* Top Identity */}
                    <div>
                      <span className="font-mono text-[10px] text-content-muted block">{persona.id}</span>
                      <h3 className="font-bold text-sm text-white">{persona.name}</h3>

                      {/* Verdict Badge */}
                      <div className="mt-2.5">
                        <span
                          className={`inline-flex items-center gap-1 rounded-full px-2.5 py-1 text-[11px] font-bold ${
                            isApproved
                              ? "bg-emerald-500/20 text-emerald-300 border border-emerald-500/30"
                              : isReview
                              ? "bg-amber-500/20 text-amber-300 border border-amber-500/30"
                              : "bg-rose-500/20 text-rose-300 border border-rose-500/30"
                          }`}
                        >
                          {isApproved && <CheckCircle2 className="h-3 w-3" />}
                          {isReview && <AlertTriangle className="h-3 w-3" />}
                          {isDecline && <XCircle className="h-3 w-3" />}
                          {data.verdict.label}
                        </span>
                      </div>
                    </div>

                    {/* Primary Driver */}
                    <div className="border-t border-line-subtle/80 pt-3">
                      <span className="text-[10px] font-bold uppercase tracking-wider text-content-muted block">
                        Primary Driver
                      </span>
                      <p className="mt-1 font-semibold text-content-secondary">
                        {data.verdict.driver ? `${data.verdict.driver.code}: ${data.verdict.driver.name}` : "All checks passed"}
                      </p>
                    </div>

                    {/* Key Metrics Table */}
                    <div className="space-y-2 border-t border-line-subtle/80 pt-3 text-[11px]">
                      <div className="flex justify-between">
                        <span className="text-content-muted">ML Default Prob:</span>
                        <strong className="font-mono text-content-secondary">
                          {data.ml.available ? `${(data.ml.score * 100).toFixed(1)}%` : "N/A"}
                        </strong>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-content-muted">Requested:</span>
                        <span className="font-semibold text-content-secondary">{data.applicant.requested_amount}</span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-content-muted">Credit Score:</span>
                        <span className="font-mono font-semibold text-content-secondary">{data.applicant.credit_score}</span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-content-muted">Policy Failures:</span>
                        <span className="font-semibold text-rose-400">{data.rules_summary.fail}</span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-content-muted">Policy Reviews:</span>
                        <span className="font-semibold text-amber-400">{data.rules_summary.review}</span>
                      </div>
                    </div>

                    {/* Select Button */}
                    <button
                      onClick={() => {
                        onSelectPersona(persona.id);
                        onClose();
                      }}
                      className="flex w-full items-center justify-center gap-1.5 rounded-lg border border-line-muted bg-slate-800 py-2 text-xs font-semibold text-white hover:bg-brand-600 transition-colors"
                    >
                      <span>Investigate</span>
                      <ArrowRight className="h-3.5 w-3.5" />
                    </button>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
