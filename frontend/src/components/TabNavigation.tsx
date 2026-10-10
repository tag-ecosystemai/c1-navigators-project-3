import React from 'react';
import { ViewTab } from '../types';
import { LayoutDashboard, BookOpen, Search, Cpu, FileText, ArrowLeft } from 'lucide-react';

interface TabNavigationProps {
  activeTab: ViewTab;
  onTabChange: (tab: ViewTab) => void;
  disabled?: boolean;
  onReturnToOverview: () => void;
}

export const TabNavigation: React.FC<TabNavigationProps> = ({
  activeTab,
  onTabChange,
  disabled = false,
  onReturnToOverview,
}) => {
  const tabs: { id: ViewTab; label: string; icon: React.ElementType }[] = [
    { id: 'overview', label: 'Overview', icon: LayoutDashboard },
    { id: 'rules', label: 'Rules', icon: BookOpen },
    { id: 'forensics', label: 'Forensics', icon: Search },
    { id: 'ml', label: 'ML', icon: Cpu },
    { id: 'memo', label: 'Memo', icon: FileText },
  ];

  return (
    <div className="sticky top-16 z-30 -mx-4 border-y border-line-subtle bg-surface-primary/95 px-4 py-2 backdrop-blur sm:top-16 sm:mx-0 sm:rounded-xl sm:border sm:px-1">
      <div role="tablist" className="flex items-center gap-1 overflow-x-auto">
      <button onClick={onReturnToOverview} className="flex shrink-0 items-center gap-1 rounded-lg border border-brand-500/30 bg-brand-50 px-2.5 py-2 text-xs font-semibold text-brand-700 hover:bg-brand-100 dark:bg-brand-950/30 dark:text-brand-300" aria-label="Return to case overview">
          <ArrowLeft className="h-3.5 w-3.5" /> <span>Case overview</span>
      </button>
      {tabs.map((tab) => {
        const Icon = tab.icon;
        const isActive = activeTab === tab.id;
        return (
          <button
            key={tab.id}
            role="tab"
            aria-selected={isActive}
            disabled={disabled}
            onClick={() => onTabChange(tab.id)}
            aria-controls={`${tab.id}-panel`}
            className={`flex min-w-[96px] flex-1 items-center justify-center gap-2 rounded-lg py-2 text-sm font-medium transition-all ${
              isActive
                ? 'bg-white dark:bg-slate-800 text-brand-600 dark:text-brand-400 shadow-sm'
                : 'text-slate-500 dark:text-content-muted hover:text-slate-700 dark:hover:text-content-secondary hover:bg-slate-200 dark:hover:bg-slate-800/50'
            } ${disabled ? 'opacity-50 cursor-not-allowed' : ''}`}
          >
            <Icon className="h-4 w-4" />
            {tab.label}
          </button>
        );
      })}
      </div>
    </div>
  );
};
