import React from 'react';
import { ViewTab } from '../types';
import { LayoutDashboard, BookOpen, Search, Cpu, FileText } from 'lucide-react';

interface TabNavigationProps {
  activeTab: ViewTab;
  onTabChange: (tab: ViewTab) => void;
  disabled?: boolean;
}

export const TabNavigation: React.FC<TabNavigationProps> = ({
  activeTab,
  onTabChange,
  disabled = false,
}) => {
  const tabs: { id: ViewTab; label: string; icon: React.ElementType }[] = [
    { id: 'overview', label: 'Overview', icon: LayoutDashboard },
    { id: 'rules', label: 'Rules', icon: BookOpen },
    { id: 'forensics', label: 'Forensics', icon: Search },
    { id: 'ml', label: 'ML', icon: Cpu },
    { id: 'memo', label: 'Memo', icon: FileText },
  ];

  return (
    <div
      role="tablist"
      className="flex items-center space-x-1 rounded-xl border border-slate-200 dark:border-line-subtle bg-slate-100 dark:bg-slate-900/60 p-1"
    >
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
            className={`flex flex-1 items-center justify-center gap-2 rounded-lg py-2 text-sm font-medium transition-all ${
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
  );
};
