import React from "react";
import { Cpu, ArrowUpRight, ArrowDownRight, Info } from "lucide-react";
import { MLResult } from "../types";

interface MLRiskCardProps {
  ml: MLResult;
}

export const MLRiskCard: React.FC<MLRiskCardProps> = ({ ml }) => {
  if (!ml.available) {
    return (
      <div className="rounded-2xl border border-slate-800 bg-[#0c1828]/90 p-5">
        <div className="flex items-center gap-2 text-slate-400">
          <Cpu className="h-4 w-4" />
          <h3 className="text-xs font-bold uppercase tracking-wider">ML Credit-Risk Model</h3>
        </div>
        <p className="mt-2 text-xs text-slate-400">Live ML scoring is currently unavailable.</p>
      </div>
    );
  }

  const scorePct = Math.round(ml.score * 100);
  const isHigh = ml.level === "HIGH_RISK" || ml.score >= 0.5;
  const isMedium = ml.level === "MEDIUM_RISK" || (ml.score >= 0.2 && ml.score < 0.5);
  const isLow = ml.level === "LOW_RISK" || ml.score < 0.2;

  const scoreColor = isHigh
    ? "text-rose-400"
    : isMedium
    ? "text-amber-400"
    : "text-emerald-400";

  const tierBadge = isHigh
    ? "border-rose-500/30 bg-rose-500/10 text-rose-300"
    : isMedium
    ? "border-amber-500/30 bg-amber-500/10 text-amber-300"
    : "border-emerald-500/30 bg-emerald-500/10 text-emerald-300";

  return (
    <div className="rounded-2xl border border-slate-800 bg-[#0c1828]/90 p-5 shadow-sm">
      <div className="flex items-center justify-between border-b border-slate-800 pb-3">
        <div className="flex items-center gap-2">
          <Cpu className="h-4 w-4 text-brand-400" />
          <h3 className="text-xs font-bold uppercase tracking-wider text-slate-200">
            ML Probability of Default (PD)
          </h3>
        </div>
        <span className={`rounded-full border px-2.5 py-0.5 text-[11px] font-bold ${tierBadge}`}>
          {ml.level.replace("_", " ")}
        </span>
      </div>

      {/* Main Score Display */}
      <div className="mt-4 flex items-center justify-between gap-4">
        <div>
          <div className="flex items-baseline gap-2">
            <span className={`font-mono text-3xl font-extrabold ${scoreColor}`}>
              {ml.score.toFixed(3)}
            </span>
            <span className="text-xs font-semibold text-slate-400">
              ({scorePct}% default prob.)
            </span>
          </div>
          <p className="mt-1 text-[11px] text-slate-400">
            XGBoost model trained on 20 financial & transaction features
          </p>
        </div>

        {/* Mini progress bar gauge */}
        <div className="w-28 text-right">
          <div className="h-2 w-full rounded-full bg-slate-800 overflow-hidden">
            <div
              className={`h-full rounded-full ${
                isHigh ? "bg-rose-500" : isMedium ? "bg-amber-500" : "bg-emerald-500"
              }`}
              style={{ width: `${Math.max(scorePct, 4)}%` }}
            />
          </div>
          <span className="text-[10px] font-mono text-slate-400 mt-1 block">
            {ml.precomputed ? "Batch Prediction" : "Live Scored"}
          </span>
        </div>
      </div>

      {/* Feature Attribution / Top Drivers */}
      <div className="mt-5 space-y-2.5">
        <span className="text-[10px] font-bold uppercase tracking-wider text-slate-400 block">
          Key Feature Risk Drivers
        </span>

        {ml.drivers && ml.drivers.length > 0 ? (
          ml.drivers.map((driver, idx) => {
            const raisesRisk = driver.effect === "raises risk";
            const sharePct = Math.round(driver.share * 100);

            return (
              <div
                key={driver.feature || idx}
                className="flex items-center justify-between rounded-lg border border-slate-800/80 bg-slate-900/50 p-2 text-xs"
              >
                <div className="flex items-center gap-2 truncate pr-2">
                  {raisesRisk ? (
                    <ArrowUpRight className="h-3.5 w-3.5 text-rose-400 shrink-0" />
                  ) : (
                    <ArrowDownRight className="h-3.5 w-3.5 text-emerald-400 shrink-0" />
                  )}
                  <span className="truncate text-slate-200 font-medium">{driver.label}</span>
                </div>

                <div className="flex items-center gap-2 shrink-0">
                  <span
                    className={`text-[10px] font-semibold uppercase tracking-wider ${
                      raisesRisk ? "text-rose-400" : "text-emerald-400"
                    }`}
                  >
                    {driver.effect}
                  </span>
                  <span className="font-mono text-[11px] text-slate-400 w-8 text-right">
                    {sharePct}%
                  </span>
                </div>
              </div>
            );
          })
        ) : (
          <p className="text-xs text-slate-400">No feature drivers available.</p>
        )}
      </div>

      {/* Disclaimer */}
      <div className="mt-4 flex items-start gap-1.5 rounded-lg bg-slate-900/60 p-2.5 text-[11px] text-slate-400">
        <Info className="h-3.5 w-3.5 text-brand-400 shrink-0 mt-0.5" />
        <span>{ml.label}</span>
      </div>
    </div>
  );
};
