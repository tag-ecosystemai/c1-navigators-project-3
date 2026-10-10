import React from "react";
import { X, Command } from "lucide-react";

interface KeyboardShortcutsModalProps {
  isOpen: boolean;
  onClose: () => void;
}

export const KeyboardShortcutsModal: React.FC<KeyboardShortcutsModalProps> = ({
  isOpen,
  onClose,
}) => {
  if (!isOpen) return null;

  const shortcuts = [
    { key: "1 - 5", description: "Instantly switch between the 5 golden borrower personas" },
    { key: "C", description: "Open side-by-side comparison matrix across all personas" },
    { key: "R", description: "Re-run investigation and bypass cached results" },
    { key: "T", description: "Toggle between Dark and Light interface themes" },
    { key: "?", description: "Open / close this keyboard shortcuts overlay" },
    { key: "Esc", description: "Close any active modal or drawer" },
  ];

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-sm p-4">
      <div className="relative w-full max-w-md rounded-2xl border border-line-muted bg-surface-secondary p-6 shadow-2xl">
        <div className="flex items-center justify-between border-b border-line-subtle pb-4">
          <div className="flex items-center gap-2 text-brand-400">
            <Command className="h-5 w-5" />
            <h3 className="text-base font-bold text-white">Keyboard Shortcuts</h3>
          </div>
          <button
            onClick={onClose}
            className="rounded-lg p-1.5 text-content-muted hover:bg-slate-800 hover:text-white"
          >
            <X className="h-4 w-4" />
          </button>
        </div>

        <div className="mt-4 space-y-3">
          {shortcuts.map((s) => (
            <div
              key={s.key}
              className="flex items-center justify-between rounded-lg border border-line-subtle/80 bg-slate-900/50 p-2.5 text-xs"
            >
              <span className="text-content-muted">{s.description}</span>
              <kbd className="rounded border border-line-muted bg-slate-800 px-2 py-1 font-mono font-bold text-brand-300">
                {s.key}
              </kbd>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};
