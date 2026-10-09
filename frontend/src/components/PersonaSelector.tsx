import React from "react";
import { User, CheckCircle2, AlertCircle, AlertTriangle } from "lucide-react";
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
      <div className="flex items-center justify-between mb-2">
        <div className="flex items-center gap-2">
          <User className="h-4 w-4 text-brand-400" />
          <span className="text-xs font-bold uppercase tracking-wider text-slate-400">
            Select Test Persona (Golden Cases)
          </span>
        </div>
        <span className="text-[11px] text-slate-400">
          Keyboard: Press keys <kbd className="rounded bg-slate-800 px-1 py-0.5 font-mono text-slate-300">1</kbd> to <kbd className="rounded bg-slate-800 px-1 py-0.5 font-mono text-slate-300">5</kbd>
        </span>
      </div>

      <div className="grid grid-cols-1 gap-2.5 sm:grid-cols-2 lg:grid-cols-5">
        {personas.map((persona, index) => {
          const isSelected = persona.id === selectedId;
          const shortcutKey = index + 1;

          // Badges for expected test profiles
          let badgeColor = "border-slate-700 bg-slate-800/80 text-slate-300";
          let badgeIcon = <CheckCircle2 className="h-3 w-3 text-emerald-400" />;
          let outcomeTag = "Prime";

          if (persona.id === "CUST-GOLD-002") {
            badgeColor = "border-rose-900/50 bg-rose-950/40 text-rose-300";
            badgeIcon = <AlertCircle className="h-3 w-3 text-rose-400" />;
            outcomeTag = "Income Gap";
          } else if (persona.id === "CUST-GOLD-003") {
            badgeColor = "border-rose-900/50 bg-rose-950/40 text-rose-300";
            badgeIcon = <AlertCircle className="h-3 w-3 text-rose-400" />;
            outcomeTag = "Gambling/NSF";
          } else if (persona.id === "CUST-GOLD-004") {
            badgeColor = "border-amber-900/50 bg-amber-950/40 text-amber-300";
            badgeIcon = <AlertTriangle className="h-3 w-3 text-amber-400" />;
            outcomeTag = "Hidden Debt";
          } else if (persona.id === "CUST-GOLD-005") {
            badgeColor = "border-rose-900/50 bg-rose-950/40 text-rose-300";
            badgeIcon = <AlertCircle className="h-3 w-3 text-rose-400" />;
            outcomeTag = "Bankruptcy";
          }

          return (
            <button
              key={persona.id}
              onClick={() => onSelect(persona.id)}
              disabled={loading}
              className={`group relative flex flex-col justify-between rounded-xl border p-3.5 text-left transition-all duration-200 ${
                isSelected
                  ? "border-brand-500 bg-brand-950/40 shadow-lg shadow-brand-950/40 ring-1 ring-brand-500"
                  : "border-slate-800 bg-[#0c1828]/80 hover:border-slate-700 hover:bg-[#112238]/90"
              }`}
            >
              {/* Header */}
              <div className="flex items-start justify-between w-full gap-2">
                <div>
                  <div className="flex items-center gap-1.5">
                    <span className="flex h-5 w-5 items-center justify-center rounded-md bg-slate-800 font-mono text-[11px] font-bold text-slate-300 group-hover:bg-brand-600 group-hover:text-white transition-colors">
                      {shortcutKey}
                    </span>
                    <h3 className="font-semibold text-sm text-slate-100 group-hover:text-brand-300 transition-colors">
                      {persona.name}
                    </h3>
                  </div>
                  <span className="text-[11px] font-mono text-slate-400">
                    {persona.id}
                  </span>
                </div>

                <span className={`inline-flex items-center gap-1 rounded-full border px-2 py-0.5 text-[10px] font-medium ${badgeColor}`}>
                  {badgeIcon}
                  {outcomeTag}
                </span>
              </div>

              {/* Tagline */}
              <p className="mt-2 text-xs text-slate-400 line-clamp-2 leading-relaxed">
                {persona.tagline}
              </p>

              {/* Financial Headline */}
              <div className="mt-3 flex items-center justify-between border-t border-slate-800/80 pt-2 text-xs">
                <div>
                  <span className="text-[10px] text-slate-400 uppercase tracking-wider block">Requested</span>
                  <span className="font-semibold text-slate-200">{persona.headline.loan_amount}</span>
                </div>
                <div className="text-right">
                  <span className="text-[10px] text-slate-400 uppercase tracking-wider block">Score</span>
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
