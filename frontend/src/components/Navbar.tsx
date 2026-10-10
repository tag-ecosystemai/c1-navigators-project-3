import React, { useState } from "react";
import {
  ShieldCheck,
  Activity,
  Moon,
  Sun,
  RotateCw,
  Scale,
  HelpCircle,
  AlertTriangle,
  Zap,
  Menu,
  X,
} from "lucide-react";
import { HealthResponse } from "../types";

interface NavbarProps {
  health: HealthResponse | null;
  healthLoading: boolean;
  theme: "dark" | "light";
  onToggleTheme: () => void;
  onOpenCompare: () => void;
  onOpenShortcuts: () => void;
  onRefresh: () => void;
  onLogoClick: () => void;
  isInvestigating: boolean;
}

export const Navbar: React.FC<NavbarProps> = ({
  health,
  healthLoading,
  theme,
  onToggleTheme,
  onOpenCompare,
  onOpenShortcuts,
  onRefresh,
  onLogoClick,
  isInvestigating,
}) => {
  const isAzure = health?.mode === "azure";
  const [toolsOpen, setToolsOpen] = useState(false);

  return (
    <header className="sticky top-0 z-40 w-full border-b border-line-subtle bg-surface-primary/95 backdrop-blur-md">
      <div className="mx-auto flex min-h-16 max-w-7xl items-center justify-between gap-2 px-3 sm:px-6 lg:px-8">
        {/* Brand */}
        <button onClick={onLogoClick} aria-label="Return to case overview" className="flex min-w-0 items-center gap-2 text-left hover:opacity-90 transition-opacity sm:gap-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-gradient-to-tr from-brand-600 to-blue-400 shadow-md shadow-brand-500/20">
            <ShieldCheck className="h-6 w-6 text-white" />
          </div>
          <div className="min-w-0">
            <div className="flex items-center gap-2">
              <span className="text-base font-bold tracking-tight text-content-primary sm:text-lg">
                CREDENCE
              </span>
              <span className="hidden rounded bg-brand-500/10 px-1.5 py-0.5 text-xs font-semibold text-brand-400 border border-brand-500/20 sm:inline">
                AI CREDIT AGENT
              </span>
            </div>
            <p className="hidden text-xs text-content-muted sm:block">Decision-Support Workstation</p>
          </div>
        </button>

        {/* Status Mode Banner */}
        <div className="hidden md:flex items-center gap-3">
          {healthLoading ? (
            <div className="flex items-center gap-2 rounded-full border border-line-muted bg-slate-800/60 px-3 py-1 text-xs text-content-muted">
              <Activity className="h-3.5 w-3.5 animate-spin text-brand-400" />
              <span>Checking AI services...</span>
            </div>
          ) : isAzure ? (
            <div
              className="group relative flex items-center gap-2 rounded-full border border-emerald-500/30 bg-emerald-500/10 px-3.5 py-1 text-xs font-medium text-emerald-400 shadow-sm shadow-emerald-900/20"
              title={`Chat: ${health?.deployments?.chat || "GPT-4o"}, Embeddings: ${health?.deployments?.embeddings || "text-embedding-ada"}`}
            >
              <span className="relative flex h-2 w-2">
                <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-emerald-400 opacity-75"></span>
                <span className="relative inline-flex h-2 w-2 rounded-full bg-emerald-500"></span>
              </span>
              <span className="flex items-center gap-1.5">
                <Zap className="h-3.5 w-3.5" />
                Azure OpenAI Live
              </span>
              {health?.deployments?.chat && (
                <span className="text-xs text-emerald-300/70 border-l border-emerald-500/20 pl-1.5">
                  {health.deployments.chat}
                </span>
              )}
            </div>
          ) : (
            <div
              className="offline-status flex items-center gap-2 rounded-full border border-amber-500/30 bg-amber-500/10 px-3.5 py-1 text-xs font-semibold text-amber-300"
              title={health?.degraded_reason || "Using local deterministic rule engine and policy store"}
            >
              <AlertTriangle className="h-3.5 w-3.5 text-amber-400" />
              <span>Offline Mode (Deterministic Safety Net)</span>
            </div>
          )}

          {health?.warm?.running && (
            <div className="flex items-center gap-2 rounded-full border border-brand-500/30 bg-brand-500/10 px-3 py-1 text-xs text-brand-300 animate-pulse">
              <span>Warming up cases: {health.warm.done}/{health.warm.total}</span>
            </div>
          )}
        </div>

        {/* Action Controls */}
        <div className="hidden items-center gap-2 sm:flex">
          <button
            onClick={onOpenCompare}
            className="flex items-center gap-1.5 rounded-lg border border-line-muted bg-white px-3 py-1.5 text-xs font-medium text-slate-700 transition-colors hover:bg-slate-100 dark:bg-slate-800/80 dark:text-content-secondary dark:hover:bg-slate-700 dark:hover:text-white"
            title="Side-by-side Persona Comparison (Shortcut: C)"
          >
            <Scale className="h-3.5 w-3.5 text-brand-400" />
            <span className="hidden sm:inline">Compare</span>
            <kbd className="ml-1 rounded bg-slate-700/80 px-1 py-0.5 text-xs text-content-muted">C</kbd>
          </button>

          <button
            onClick={onRefresh}
            disabled={isInvestigating}
            className="flex items-center gap-1.5 rounded-lg border border-line-muted bg-white px-3 py-1.5 text-xs font-medium text-slate-700 transition-colors hover:bg-slate-100 dark:bg-slate-800/80 dark:text-content-secondary dark:hover:bg-slate-700 dark:hover:text-white disabled:opacity-50"
            title="Re-run Investigation (Shortcut: R)"
          >
            <RotateCw className={`h-3.5 w-3.5 text-content-muted ${isInvestigating ? "animate-spin text-brand-400" : ""}`} />
            <span className="hidden sm:inline">Re-run</span>
            <kbd className="ml-1 rounded bg-slate-700/80 px-1 py-0.5 text-xs text-content-muted">R</kbd>
          </button>

          <button
            onClick={onToggleTheme}
            className="rounded-lg border border-line-muted bg-white p-2 text-slate-600 transition-colors hover:bg-slate-100 dark:bg-slate-800/80 dark:text-content-muted dark:hover:bg-slate-700 dark:hover:text-white"
            title={`Toggle ${theme === "dark" ? "Light" : "Dark"} Mode (Shortcut: T)`}
            aria-label="Toggle theme"
          >
            {theme === "dark" ? <Sun className="h-4 w-4" /> : <Moon className="h-4 w-4" />}
          </button>

          <button
            onClick={onOpenShortcuts}
            className="rounded-lg border border-line-muted bg-white p-2 text-slate-600 transition-colors hover:bg-slate-100 dark:bg-slate-800/80 dark:text-content-muted dark:hover:bg-slate-700 dark:hover:text-white"
            title="Keyboard Shortcuts (Shortcut: ?)"
            aria-label="Keyboard shortcuts"
          >
            <HelpCircle className="h-4 w-4" />
          </button>
        </div>
        <div className="relative sm:hidden">
          <button onClick={() => setToolsOpen((open) => !open)} aria-expanded={toolsOpen} aria-controls="mobile-tools" className="inline-flex items-center gap-1 rounded-lg border border-line-muted bg-slate-800/80 px-2.5 py-2 text-xs font-semibold text-content-secondary">
            {toolsOpen ? <X className="h-4 w-4" /> : <Menu className="h-4 w-4" />} Tools
          </button>
          {toolsOpen && (
            <div id="mobile-tools" className="absolute right-0 top-full z-50 mt-2 w-48 rounded-xl border border-line-muted bg-surface-secondary p-1.5 shadow-xl">
              <button onClick={() => { onOpenCompare(); setToolsOpen(false); }} className="w-full rounded-lg px-3 py-2 text-left text-xs text-content-secondary hover:bg-surface-elevated">Compare cases</button>
              <button onClick={() => { onRefresh(); setToolsOpen(false); }} disabled={isInvestigating} className="w-full rounded-lg px-3 py-2 text-left text-xs text-content-secondary hover:bg-surface-elevated disabled:opacity-50">Re-run investigation</button>
              <button onClick={() => { onToggleTheme(); setToolsOpen(false); }} className="w-full rounded-lg px-3 py-2 text-left text-xs text-content-secondary hover:bg-surface-elevated">Toggle theme</button>
              <button onClick={() => { onOpenShortcuts(); setToolsOpen(false); }} className="w-full rounded-lg px-3 py-2 text-left text-xs text-content-secondary hover:bg-surface-elevated">Keyboard shortcuts</button>
            </div>
          )}
        </div>
      </div>
    </header>
  );
};
