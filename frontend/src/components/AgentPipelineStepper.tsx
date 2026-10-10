import React from "react";
import {
  Database,
  FileCheck,
  Cpu,
  Sparkles,
  CheckCircle2,
  Clock,
  Check,
  Loader2,
} from "lucide-react";
import { AgentStep } from "../types";

interface AgentPipelineStepperProps {
  steps: AgentStep[];
  totalMs: number;
  engineMs: number;
  isInvestigating: boolean;
}

export const AgentPipelineStepper: React.FC<AgentPipelineStepperProps> = ({
  steps,
  totalMs,
  isInvestigating,
}) => {
  const getStepIcon = (key: string) => {
    switch (key) {
      case "data":
        return <Database className="h-4 w-4" />;
      case "compliance":
        return <FileCheck className="h-4 w-4" />;
      case "credit":
        return <Cpu className="h-4 w-4" />;
      case "explanation":
        return <Sparkles className="h-4 w-4" />;
      default:
        return <Cpu className="h-4 w-4" />;
    }
  };

  const getStepDescription = (key: string) => {
    switch (key) {
      case "data":
        return "Validation, Income Verification & Txn Metrics";
      case "compliance":
        return "14-Rule Deterministic Policy Matrix";
      case "credit":
        return "20-Feature Extraction & ML PD Scoring";
      case "explanation":
        return "Fact-Checked LLM Narrative Synthesis";
      default:
        return "Core Execution Step";
    }
  };

  return (
    <div className="rounded-xl border border-line-subtle bg-surface-secondary/90 p-4 shadow-sm">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-line-subtle pb-3">
        <div className="flex items-center gap-2">
          <div className="h-2 w-2 rounded-full bg-brand-400 animate-pulse" />
          <h2 className="text-xs font-bold uppercase tracking-wider text-content-muted">
            Multi-Agent Orchestration Pipeline
          </h2>
        </div>

        <div className="flex items-center gap-3 text-xs text-content-muted">
          <div className="flex items-center gap-1.5">
            <Clock className="h-3.5 w-3.5 text-content-muted" />
            <span>
              Total Latency: <strong className="font-mono text-brand-300">{totalMs} ms</strong>
            </span>
          </div>
          {isInvestigating ? (
            <span className="inline-flex items-center gap-1 rounded bg-amber-500/10 px-2 py-0.5 text-xs font-medium text-amber-400 border border-amber-500/20">
              <Loader2 className="h-3 w-3 animate-spin" /> Processing...
            </span>
          ) : (
            <span className="inline-flex items-center gap-1 rounded bg-emerald-500/10 px-2 py-0.5 text-xs font-medium text-emerald-400 border border-emerald-500/20">
              <Check className="h-3 w-3" /> 4 Agents Executed
            </span>
          )}
        </div>
      </div>

      <div className="mt-4 grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-4">
        {steps.map((step, idx) => {
          return (
            <div
              key={step.key || idx}
              className="relative flex flex-col justify-between rounded-lg border border-line-subtle bg-surface-elevated/60 p-3 transition-all hover:border-line-muted"
            >
              <div>
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2 text-brand-400">
                    <div className="flex h-7 w-7 items-center justify-center rounded-md bg-brand-950/60 border border-brand-500/20 text-brand-400">
                      {getStepIcon(step.key)}
                    </div>
                    <div>
                      <span className="text-xs font-mono uppercase tracking-wider text-content-muted">
                        Agent 0{idx + 1}
                      </span>
                      <h4 className="text-xs font-semibold text-content-secondary">
                        {step.name}
                      </h4>
                    </div>
                  </div>

                  <span className="flex items-center gap-1 text-xs font-mono text-emerald-400">
                    {isInvestigating ? (
                      <span className="h-3 w-3 animate-spin rounded-full border border-brand-400 border-t-transparent" />
                    ) : (
                      <>
                        <CheckCircle2 className="h-3.5 w-3.5 text-emerald-400" />
                        <span>{step.duration_ms}ms</span>
                      </>
                    )}
                  </span>
                </div>

                <p className="mt-2 text-xs text-content-muted leading-relaxed">
                  {getStepDescription(step.key)}
                </p>
              </div>

              {step.summary && (
                <div className="mt-2.5 rounded bg-slate-900/60 p-1.5 font-mono text-xs text-content-muted truncate">
                  {step.summary}
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
};
