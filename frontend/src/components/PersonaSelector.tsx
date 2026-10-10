import React from "react";
import { User } from "lucide-react";
import { Persona } from "../types";

interface PersonaSelectorProps {
  personas: Persona[];
  selectedId: string;
  onSelect: (id: string) => void;
  loading: boolean;
}

export const PersonaSelector: React.FC<PersonaSelectorProps> = ({
  personas,
  selectedId,
  onSelect,
  loading,
}) => {
  return (
    <div className="w-full">
      <div className="flex items-center justify-between gap-3 mb-2">
        <div className="flex items-center gap-2">
          <User className="h-4 w-4 text-brand-400" />
          <span className="text-xs font-bold uppercase tracking-wider text-content-muted">
            Select Test Persona (Golden Cases)
          </span>
        </div>
        <span className="hidden text-xs text-content-muted sm:block">
          Keyboard: Press keys <kbd className="rounded bg-slate-800 px-1 py-0.5 font-mono text-content-muted">1</kbd> to <kbd className="rounded bg-slate-800 px-1 py-0.5 font-mono text-content-muted">5</kbd>
        </span>
      </div>

      <div className="flex gap-2 overflow-x-auto pb-1 xl:grid xl:grid-cols-5 xl:overflow-visible">
        {personas.map((persona, index) => {
          const isSelected = persona.id === selectedId;
          const shortcutKey = index + 1;

          // Badges for expected test profiles
          let badgeColor = "border-line-muted bg-slate-800/80 text-content-muted";
          let badgeIcon = <User className="h-3 w-3 text-slate-400" />;

          // Use the first few words of the tagline, or just the whole tagline if short
          let outcomeTag = persona.tagline.split(" ").slice(0, 2).join(" ");

          return (
            <button
              key={persona.id}
              onClick={() => onSelect(persona.id)}
              disabled={loading}
              aria-pressed={isSelected}
              className={`group relative flex min-w-[180px] flex-col justify-between rounded-xl border p-3 text-left transition-all duration-200 xl:min-w-0 ${
                isSelected
                  ? "border-brand-500 bg-brand-50 text-slate-900 shadow-lg shadow-brand-200/70 ring-1 ring-brand-500 dark:bg-brand-950/40 dark:text-white dark:shadow-brand-950/40"
                  : "border-line-subtle bg-surface-secondary/80 hover:border-line-muted hover:bg-surface-elevated/90"
              }`}
            >
              {/* Header */}
              <div className="flex items-start justify-between w-full gap-2">
                <div>
                  <div className="flex items-center gap-1.5">
                    <span className="flex h-5 w-5 items-center justify-center rounded-md bg-slate-800 font-mono text-xs font-bold text-content-muted group-hover:bg-brand-600 group-hover:text-white transition-colors">
                      {shortcutKey}
                    </span>
                    <h3 className="font-semibold text-sm text-content-primary group-hover:text-brand-300 transition-colors">
                      {persona.name}
                    </h3>
                  </div>
                  <span className="hidden text-xs font-mono text-content-muted xl:block">
                    {persona.id}
                  </span>
                </div>

                <span className={`inline-flex items-center gap-1 rounded-full border px-2 py-0.5 text-xs font-medium ${badgeColor}`}>
                  {badgeIcon}
                  {outcomeTag}
                </span>
              </div>

              {/* Tagline */}
              <p className="hidden mt-2 text-xs text-content-muted line-clamp-2 leading-relaxed xl:block">
                {persona.tagline}
              </p>

              {/* Financial Headline */}
              <div className="mt-2 flex items-center justify-between border-t border-line-subtle/80 pt-2 text-xs xl:mt-3">
                <div>
                  <span className="text-xs text-content-muted uppercase tracking-wider block">Requested</span>
                  <span className="font-semibold text-content-secondary">{persona.headline.loan_amount}</span>
                </div>
                <div className="text-right">
                  <span className="text-xs text-content-muted uppercase tracking-wider block">Score</span>
                  <span className={`font-mono font-semibold ${persona.headline.credit_score >= 680 ? "text-emerald-400" : persona.headline.credit_score >= 600 ? "text-amber-400" : "text-rose-400"}`}>
                    {persona.headline.credit_score}
                  </span>
                </div>
              </div>
            </button>
          );
        })}
      </div>
    </div>
  );
};
