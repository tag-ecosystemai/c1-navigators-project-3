import React, { useEffect, useState, useCallback, useRef } from "react";
import { Navbar } from "./components/Navbar";
import { PersonaSelector } from "./components/PersonaSelector";
import { AgentPipelineStepper } from "./components/AgentPipelineStepper";
import { PolicyMatrix } from "./components/PolicyMatrix";
import { MLRiskCard } from "./components/MLRiskCard";
import { CrossCheckDrawer } from "./components/CrossCheckDrawer";
import { ComparisonModal } from "./components/ComparisonModal";
import { KeyboardShortcutsModal } from "./components/KeyboardShortcutsModal";
import { ReportViewModal } from "./components/ReportViewModal";
import { TabNavigation } from "./components/TabNavigation";
import { FinancialForensics } from "./components/FinancialForensics";
import { CaseOverview } from "./components/CaseOverview";
import { fetchHealth, fetchPersonas, investigateApplicant } from "./api/client";
import { HealthResponse, Persona, InvestigationData, ViewTab } from "./types";
import { AlertTriangle, Loader2 } from "lucide-react";

export const App: React.FC = () => {
  const [theme, setTheme] = useState<"dark" | "light">("dark");
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [healthLoading, setHealthLoading] = useState(true);
  const [personas, setPersonas] = useState<Persona[]>([]);
  const [selectedId, setSelectedId] = useState<string>("CUST-GOLD-001");
  const [investigationData, setInvestigationData] = useState<InvestigationData | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<ViewTab>("overview");
  const lastNonMemoTab = useRef<ViewTab>("overview");
  const [focusedRuleCode, setFocusedRuleCode] = useState<string | null>(null);
  const [showPipeline, setShowPipeline] = useState(false);

  // Modals state
  const [isCompareOpen, setIsCompareOpen] = useState(false);
  const [isShortcutsOpen, setIsShortcutsOpen] = useState(false);
  const [isReportOpen, setIsReportOpen] = useState(false);

  useEffect(() => {
    if (activeTab !== "memo") lastNonMemoTab.current = activeTab;
  }, [activeTab]);

  // Toggle Theme
  const toggleTheme = () => {
    const nextTheme = theme === "dark" ? "light" : "dark";
    setTheme(nextTheme);
    if (nextTheme === "dark") {
      document.documentElement.classList.add("dark");
      document.documentElement.classList.remove("light");
    } else {
      document.documentElement.classList.remove("dark");
      document.documentElement.classList.add("light");
    }
  };

  // Run Investigation for Persona
  const runInvestigation = useCallback(
    async (customerId: string, refresh = false) => {
      setLoading(true);
      setError(null);
      try {
        const data = await investigateApplicant(customerId, true, refresh);
        setInvestigationData(data);
      } catch (err: any) {
        setError(err.message || "Failed to complete credit risk investigation.");
      } finally {
        setLoading(false);
      }
    },
    []
  );

  // Initial Data Load
  useEffect(() => {
    let isMounted = true;

    async function init() {
      try {
        setHealthLoading(true);
        const [healthRes, personasRes] = await Promise.all([
          fetchHealth().catch(() => null),
          fetchPersonas().catch(() => []),
        ]);

        if (!isMounted) return;

        if (healthRes) setHealth(healthRes);
        if (personasRes && personasRes.length > 0) {
          setPersonas(personasRes);
          const firstId = personasRes[0].id;
          setSelectedId(firstId);
          runInvestigation(firstId);
        }
      } catch (err: any) {
        if (isMounted) setError(err.message || "Failed to initialize application.");
      } finally {
        if (isMounted) setHealthLoading(false);
      }
    }

    init();

    return () => {
      isMounted = false;
    };
  }, [runInvestigation]);

  // Handle Persona Selection
  const handleSelectPersona = (id: string) => {
    if (id === selectedId && investigationData) return;
    setSelectedId(id);
    runInvestigation(id, false);
  };

  // Handle Refresh Investigation
  const handleRefresh = () => {
    if (selectedId) {
      runInvestigation(selectedId, true);
    }
  };

  // Keyboard Shortcuts Listener
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      // Ignore if typing inside an input
      if (["INPUT", "TEXTAREA", "SELECT"].includes((e.target as HTMLElement)?.tagName)) {
        return;
      }

      // Keys 1 to 5
      if (["1", "2", "3", "4", "5"].includes(e.key)) {
        const index = parseInt(e.key, 10) - 1;
        if (personas[index]) {
          handleSelectPersona(personas[index].id);
        }
      } else if (e.key === "c" || e.key === "C") {
        setIsCompareOpen((prev) => !prev);
      } else if (e.key === "t" || e.key === "T") {
        toggleTheme();
      } else if (e.key === "r" || e.key === "R") {
        handleRefresh();
      } else if (e.key === "?") {
        setIsShortcutsOpen((prev) => !prev);
      } else if (e.key === "Escape") {
        setIsCompareOpen(false);
        setIsShortcutsOpen(false);
        setIsReportOpen(false);
        setActiveTab((prev) => (prev === "memo" ? lastNonMemoTab.current : prev));
      }
    };

    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [personas, selectedId, theme]);

  const openMemo = () => {
    if (activeTab !== "memo") lastNonMemoTab.current = activeTab;
    setActiveTab("memo");
    setIsReportOpen(true);
  };

  const openDriverRule = (code: string) => {
    setFocusedRuleCode(code);
    setActiveTab("rules");
  };

  return (
    <div className={`min-h-screen bg-surface-primary text-content-primary`}>
      {/* Top Navigation */}
      <Navbar
        health={health}
        healthLoading={healthLoading}
        theme={theme}
        onToggleTheme={toggleTheme}
        onOpenCompare={() => setIsCompareOpen(true)}
        onOpenShortcuts={() => setIsShortcutsOpen(true)}
        onRefresh={handleRefresh}
        onLogoClick={() => setActiveTab("overview")}
        isInvestigating={loading}
      />

      {/* Main Container */}
      <main className="mx-auto max-w-7xl px-4 py-5 sm:px-6 lg:px-8 space-y-5">
        {/* Persona Selector Bar */}
        {personas.length > 0 && (
          <PersonaSelector
            personas={personas}
            selectedId={selectedId}
            onSelect={handleSelectPersona}
            loading={loading}
          />
        )}

        {/* Error Alert */}
        {error && (
          <div className="flex items-center gap-3 rounded-xl border border-rose-500/40 bg-rose-950/40 p-4 text-xs text-rose-200">
            <AlertTriangle className="h-5 w-5 text-rose-400 shrink-0" />
            <div>
              <strong className="font-bold">Investigation Error:</strong> {error}
            </div>
          </div>
        )}

        {/* Loading Skeleton */}
        {loading && !investigationData && (
          <div className="space-y-6">
            <div className="flex flex-col items-center justify-center py-8 text-content-muted gap-3">
              <Loader2 className="h-10 w-10 animate-spin text-brand-500" />
              <p className="text-sm font-medium">Investigating credit application with AI agents...</p>
            </div>
            {/* Dummy VerdictHero block */}
            <div className="h-64 rounded-xl bg-surface-secondary animate-pulse w-full" />
            {/* 2-Column Grid */}
            <div className="grid grid-cols-1 gap-6 lg:grid-cols-12">
              <div className="lg:col-span-7 h-96 rounded-xl bg-surface-secondary animate-pulse" />
              <div className="lg:col-span-5 h-96 rounded-xl bg-surface-secondary animate-pulse" />
            </div>
          </div>
        )}

        {/* Investigation Results */}
        {investigationData && (
          <div className="space-y-6">
            <details open={showPipeline} onToggle={(event) => setShowPipeline((event.target as HTMLDetailsElement).open)} className="rounded-xl border border-line-subtle bg-surface-secondary/70 px-4 py-3">
              <summary className="cursor-pointer list-none text-xs font-semibold text-content-secondary">
                <span className="mr-2 text-brand-400">Investigation run</span>{investigationData.steps.length} agents completed in {investigationData.timings.total_ms} ms
              </summary>
              <div className="mt-4"><AgentPipelineStepper steps={investigationData.steps} totalMs={investigationData.timings.total_ms} engineMs={investigationData.timings.engine_ms} isInvestigating={loading} /></div>
            </details>

            <TabNavigation
              activeTab={activeTab}
              onTabChange={(tab) => {
                if (tab === "memo") {
                  openMemo();
                } else {
                  setActiveTab(tab);
                }
              }}
              onReturnToOverview={() => setActiveTab("overview")}
              disabled={loading}
            />

            {/* Conditional Content based on activeTab */}
            {activeTab === "overview" && (
              <>
                <CaseOverview data={investigationData} onOpenMemo={openMemo} onOpenRules={() => setActiveTab("rules")} onOpenForensics={() => setActiveTab("forensics")} onOpenMl={() => setActiveTab("ml")} onViewDriver={openDriverRule} />
              </>
            )}

            {activeTab === "rules" && (
              <div className="w-full">
                <PolicyMatrix
                  rules={investigationData.rules}
                  summary={investigationData.rules_summary}
                  focusedRuleCode={focusedRuleCode}
                  onFocusedRuleHandled={() => setFocusedRuleCode(null)}
                />
              </div>
            )}

            {activeTab === "forensics" && (
              <div className="w-full">
                <FinancialForensics
                  applicant={investigationData.applicant}
                  transactions={investigationData.transactions}
                />
              </div>
            )}

            {activeTab === "ml" && (
              <div className="space-y-6">
                <MLRiskCard ml={investigationData.ml} />
                <CrossCheckDrawer crossCheck={investigationData.cross_check} />
              </div>
            )}
          </div>
        )}
      </main>

      {/* Comparison Modal (C) */}
      <ComparisonModal
        isOpen={isCompareOpen}
        onClose={() => setIsCompareOpen(false)}
        personas={personas}
        onSelectPersona={handleSelectPersona}
      />

      {/* Keyboard Shortcuts Modal (?) */}
      <KeyboardShortcutsModal
        isOpen={isShortcutsOpen}
        onClose={() => setIsShortcutsOpen(false)}
      />

      {/* Formal Credit Memorandum Modal */}
      {investigationData && (
        <ReportViewModal
          isOpen={isReportOpen}
          onClose={() => {
              setIsReportOpen(false);
              setActiveTab((prev) => (prev === "memo" ? lastNonMemoTab.current : prev));
            }}
          onReturnHome={() => {
            setIsReportOpen(false);
            setActiveTab("overview");
          }}
          data={investigationData}
        />
      )}
    </div>
  );
};

export default App;
