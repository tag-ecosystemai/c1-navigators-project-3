import React, { useState } from "react";
import {
  CheckCircle2,
  AlertTriangle,
  XCircle,
  HelpCircle,
  ChevronDown,
  ChevronUp,
  BookOpen,
  Search,
  Filter,
  BadgeAlert,
} from "lucide-react";
import { RuleDetail, RulesSummary, RuleOutcome } from "../types";

interface PolicyMatrixProps {
  rules: RuleDetail[];
  summary: RulesSummary;
}

export const PolicyMatrix: React.FC<PolicyMatrixProps> = ({ rules, summary }) => {
  const [activeFilter, setActiveFilter] = useState<"all" | RuleOutcome>("all");
  const [searchQuery, setSearchQuery] = useState("");
  const [selectedCategory, setSelectedCategory] = useState<string>("all");
  const [expandedRules, setExpandedRules] = useState<Record<string, boolean>>({});

  const toggleExpand = (code: string) => {
    setExpandedRules((prev) => ({ ...prev, [code]: !prev[code] }));
  };

  const expandAll = () => {
    const next: Record<string, boolean> = {};
    rules.forEach((r) => {
      next[r.code] = true;
    });
    setExpandedRules(next);
  };

  const collapseAll = () => {
    setExpandedRules({});
  };

  const getCategory = (code: string) => {
    if (code.startsWith("POL-ELG")) return "Eligibility";
    if (code.startsWith("POL-DTI") || code.startsWith("POL-LTI") || code.startsWith("POL-NDI"))
      return "Capacity & Ratios";
    if (code.startsWith("POL-INC") || code.startsWith("POL-TXN"))
      return "Verification & Transactions";
    if (code.startsWith("POL-SCR") || code.startsWith("POL-BNK"))
      return "Credit Bureau";
    return "Other";
  };

  const filteredRules = rules.filter((rule) => {
    // Outcome filter
    if (activeFilter !== "all" && rule.outcome !== activeFilter) return false;

    // Category filter
    if (selectedCategory !== "all" && getCategory(rule.code) !== selectedCategory)
      return false;

    // Search query
    if (searchQuery.trim()) {
      const q = searchQuery.toLowerCase();
      return (
        rule.code.toLowerCase().includes(q) ||
        rule.name.toLowerCase().includes(q) ||
        rule.reason.toLowerCase().includes(q) ||
        rule.citation.toLowerCase().includes(q)
      );
    }

    return true;
  });

  const getOutcomeBadge = (outcome: RuleOutcome, isDriver: boolean) => {
    switch (outcome) {
      case "pass":
        return (
          <span className="inline-flex items-center gap-1 rounded-full border border-emerald-500/30 bg-emerald-500/10 px-2.5 py-0.5 text-xs font-semibold text-emerald-400">
            <CheckCircle2 className="h-3 w-3" /> PASS
          </span>
        );
      case "review":
        return (
          <span className={`inline-flex items-center gap-1 rounded-full border px-2.5 py-0.5 text-xs font-semibold ${isDriver ? "border-amber-400 bg-amber-400/20 text-amber-300 ring-1 ring-amber-400/50" : "border-amber-500/30 bg-amber-500/10 text-amber-300"}`}>
            <AlertTriangle className="h-3 w-3" /> REVIEW
          </span>
        );
      case "fail":
        return (
          <span className={`inline-flex items-center gap-1 rounded-full border px-2.5 py-0.5 text-xs font-semibold ${isDriver ? "border-rose-400 bg-rose-500/20 text-rose-300 ring-1 ring-rose-400/50" : "border-rose-500/30 bg-rose-500/10 text-rose-300"}`}>
            <XCircle className="h-3 w-3" /> FAIL
          </span>
        );
      default:
        return (
          <span className="inline-flex items-center gap-1 rounded-full border border-line-muted bg-slate-800 px-2.5 py-0.5 text-xs font-semibold text-content-muted">
            <HelpCircle className="h-3 w-3" /> MISSING
          </span>
        );
    }
  };

  return (
    <div id="policy-matrix-section" className="rounded-2xl border border-line-subtle bg-surface-secondary/90 p-5 shadow-sm">
      {/* Header with Title & Counters */}
      <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between border-b border-line-subtle pb-4">
        <div>
          <div className="flex items-center gap-2">
            <BookOpen className="h-4 w-4 text-brand-400" />
            <h2 className="text-base font-bold text-content-primary">
              14-Rule Policy Evaluation Matrix
            </h2>
          </div>
          <p className="text-xs text-content-muted mt-0.5">
            Deterministic rule evaluation based on underwriting referral and exception policies
          </p>
        </div>

        {/* Outcome Filter Pills */}
        <div className="flex flex-wrap items-center gap-1.5 text-xs">
          <button
            onClick={() => setActiveFilter("all")}
            className={`rounded-lg px-3 py-1.5 font-medium transition-all ${
              activeFilter === "all"
                ? "bg-slate-700 text-white"
                : "bg-slate-800/80 text-content-muted hover:bg-slate-700/60"
            }`}
          >
            All ({rules.length})
          </button>
          <button
            onClick={() => setActiveFilter("pass")}
            className={`flex items-center gap-1.5 rounded-lg px-3 py-1.5 font-medium transition-all ${
              activeFilter === "pass"
                ? "bg-emerald-600 text-white"
                : "bg-emerald-950/40 text-emerald-300 hover:bg-emerald-900/60"
            }`}
          >
            <CheckCircle2 className="h-3 w-3 text-emerald-400" />
            Pass ({summary.pass})
          </button>
          <button
            onClick={() => setActiveFilter("review")}
            className={`flex items-center gap-1.5 rounded-lg px-3 py-1.5 font-medium transition-all ${
              activeFilter === "review"
                ? "bg-amber-600 text-white"
                : "bg-amber-950/40 text-amber-300 hover:bg-amber-900/60"
            }`}
          >
            <AlertTriangle className="h-3 w-3 text-amber-400" />
            Review ({summary.review})
          </button>
          <button
            onClick={() => setActiveFilter("fail")}
            className={`flex items-center gap-1.5 rounded-lg px-3 py-1.5 font-medium transition-all ${
              activeFilter === "fail"
                ? "bg-rose-600 text-white"
                : "bg-rose-950/40 text-rose-300 hover:bg-rose-900/60"
            }`}
          >
            <XCircle className="h-3 w-3 text-rose-400" />
            Fail ({summary.fail})
          </button>
        </div>
      </div>

      {/* Filter and Search Bar */}
      <div className="mt-4 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div className="relative flex-1 max-w-md">
          <Search className="absolute left-3 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-content-muted" />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search rule code, name, or citation..."
            className="w-full rounded-lg border border-line-muted bg-slate-900/80 py-1.5 pl-8 pr-3 text-xs text-content-secondary placeholder-slate-500 focus:border-brand-500 focus:outline-none"
          />
        </div>

        <div className="flex items-center gap-2">
          <div className="flex items-center gap-1.5 rounded-lg border border-line-muted bg-slate-900/80 px-2 py-1 text-xs text-content-muted">
            <Filter className="h-3 w-3 text-content-muted" />
            <select
              value={selectedCategory}
              onChange={(e) => setSelectedCategory(e.target.value)}
              className="bg-transparent text-xs text-content-secondary focus:outline-none cursor-pointer"
            >
              <option value="all" className="bg-slate-900">All Categories</option>
              <option value="Eligibility" className="bg-slate-900">Eligibility</option>
              <option value="Capacity & Ratios" className="bg-slate-900">Capacity & Ratios</option>
              <option value="Verification & Transactions" className="bg-slate-900">Verification & Transactions</option>
              <option value="Credit Bureau" className="bg-slate-900">Credit Bureau</option>
            </select>
          </div>

          <button
            onClick={Object.keys(expandedRules).length > 0 ? collapseAll : expandAll}
            className="rounded-lg border border-line-muted bg-slate-900/80 px-2.5 py-1 text-xs font-medium text-content-muted hover:bg-slate-800 transition-colors"
          >
            {Object.keys(expandedRules).length > 0 ? "Collapse All" : "Expand All"}
          </button>
        </div>
      </div>

      {/* Rules Table / Cards */}
      <div className="mt-4 space-y-2.5">
        {filteredRules.length === 0 ? (
          <div className="rounded-xl border border-line-subtle bg-slate-900/40 p-8 text-center text-xs text-content-muted">
            No policy checks match your current filter or search criteria.
          </div>
        ) : (
          filteredRules.map((rule) => {
            const isExpanded = !!expandedRules[rule.code];
            const isDriver = rule.is_driver;

            return (
              <div
                key={rule.code}
                className={`rounded-xl border transition-all ${
                  isDriver
                    ? rule.outcome === "fail"
                      ? "border-rose-500/50 bg-[#1a0f18]/90 ring-1 ring-rose-500/30"
                      : "border-amber-500/50 bg-[#1a160d]/90 ring-1 ring-amber-500/30"
                    : "border-line-subtle/80 bg-surface-elevated/50 hover:border-line-muted/80 hover:bg-surface-elevated/80"
                }`}
              >
                {/* Main Row */}
                <div
                  onClick={() => toggleExpand(rule.code)}
                  onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); toggleExpand(rule.code); } }}
                  role="button"
                  tabIndex={0}
                  aria-expanded={isExpanded}
                  aria-label={`${rule.code} ${rule.name}: ${rule.outcome}`}
                  className="flex flex-col gap-3 p-3.5 sm:flex-row sm:items-center sm:justify-between cursor-pointer select-none"
                >
                  <div className="flex items-start sm:items-center gap-3">
                    <div className="mt-0.5 sm:mt-0">{getOutcomeBadge(rule.outcome, isDriver)}</div>
                    <div>
                      <div className="flex items-center gap-2">
                        <span className="font-mono text-xs font-bold text-content-muted">
                          {rule.code}
                        </span>
                        <h4 className="text-xs font-semibold text-white">
                          {rule.name}
                        </h4>
                        {isDriver && (
                          <span className="inline-flex items-center gap-1 rounded bg-rose-500/20 px-1.5 py-0.5 text-[10px] font-bold text-rose-300 border border-rose-500/30">
                            <BadgeAlert className="h-3 w-3" /> Primary Driver
                          </span>
                        )}
                      </div>
                      <p className="mt-0.5 text-xs text-content-muted">{rule.reason}</p>
                    </div>
                  </div>

                  {/* Quantitative Actual vs Threshold */}
                  <div className="flex items-center justify-between sm:justify-end gap-4 text-xs">
                    <div className="text-right">
                      <div className="text-[10px] text-content-muted">Actual Value</div>
                      <div className="font-mono font-bold text-content-primary">{rule.actual}</div>
                    </div>
                    <div className="text-right">
                      <div className="text-[10px] text-content-muted">Policy Limit</div>
                      <div className="font-mono text-content-muted">{rule.threshold}</div>
                    </div>

                    <div className="text-content-muted pl-2">
                      {isExpanded ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
                    </div>
                  </div>
                </div>

                {/* Expanded Policy Citation & Excerpt */}
                {isExpanded && (
                  <div className="border-t border-line-subtle/80 bg-slate-950/60 p-4 rounded-b-xl space-y-3 text-xs">
                    <div>
                      <span className="text-[10px] font-bold uppercase tracking-wider text-content-muted block mb-1">
                        Policy Document Citation
                      </span>
                      <div className="font-mono text-[11px] text-brand-300 bg-brand-950/30 border border-brand-500/20 rounded p-2">
                        {rule.citation}
                      </div>
                    </div>

                    <div>
                      <span className="text-[10px] font-bold uppercase tracking-wider text-content-muted block mb-1">
                        Policy Excerpt
                      </span>
                      <blockquote className="border-l-2 border-slate-600 pl-3 py-1 text-content-muted italic text-xs leading-relaxed">
                        &ldquo;{rule.policy_excerpt}&rdquo;
                      </blockquote>
                    </div>
                  </div>
                )}
              </div>
            );
          })
        )}
      </div>
    </div>
  );
};
