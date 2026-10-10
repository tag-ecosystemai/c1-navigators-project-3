# Case Workspace Redesign Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Deliver a calmer, decision-first credit case workspace with reliable return navigation on desktop and mobile.

**Architecture:** Keep the existing API data and detailed evidence components intact. `App` owns tab history, the selected case, and focused-rule state; new focused presentation components consume the existing `InvestigationData`. Navigation and modal components receive explicit close/return callbacks, so they do not infer where a user came from.

**Tech Stack:** React 18, TypeScript, Vite 6, Tailwind CSS 3, Vitest, Testing Library.

**Spec:** `docs/superpowers/specs/2026-10-10-case-workspace-redesign.md`

## Global Constraints

- Preserve all backend/API contracts, policy calculations, persona data, and print content.
- Do not overwrite or stage unrelated existing worktree changes.
- The application must have no page-level horizontal overflow at a 390px viewport.
- Use explicit accessible names for icon-only actions and modal exit controls.
- Verify the production build plus browser behavior at 1440px and 390px.

## Review Focus

- Persona selection while viewing Rules, Forensics, or ML retains that view and refreshes its evidence.
- Closing a memo returns to the exact tab from which it was opened.
- A primary-driver link opens Rules and focuses the matching rule instead of merely scrolling to a duplicate matrix.
- A 390px header exposes all navigation/actions without clipping or horizontal page scroll.
- Keyboard and assistive-technology users can identify and operate every dialog close action.

---

### Task 1: Add test support and case-navigation state

**Files:**
- Modify: `frontend/package.json`
- Modify: `frontend/vite.config.ts`
- Create: `frontend/src/test/setup.ts`
- Create: `frontend/src/App.test.tsx`
- Modify: `frontend/src/App.tsx`
- Modify: `frontend/src/types/index.ts`

**Interfaces:**
- Produces `ViewTab` navigation with `previousTab` and `focusedRuleCode` state in `App`.
- Produces a test command runnable as `npm test` from `frontend/`.

- [ ] **Step 1: Write failing App navigation tests**

Test that choosing a persona preserves the selected Rules tab, and that closing Memo restores the tab that opened it.

- [ ] **Step 2: Run the focused tests to verify RED**

Run: `npm test -- App.test.tsx`

Expected: FAIL because test configuration and/or required navigation behavior is absent.

- [ ] **Step 3: Add Vitest/Testing Library configuration and implement App navigation state**

Use `previousTab: ViewTab` to restore the memo caller; remove the unconditional Overview reset from `handleSelectPersona`; use `focusedRuleCode: string | null` for the driver-to-rule handoff.

- [ ] **Step 4: Run focused tests to verify GREEN**

Run: `npm test -- App.test.tsx`

Expected: PASS.

- [ ] **Step 5: Commit Task 1**

```bash
git add frontend/package.json frontend/vite.config.ts frontend/src/test/setup.ts frontend/src/App.test.tsx frontend/src/App.tsx frontend/src/types/index.ts
git commit -m "feat: preserve case navigation context"
```

### Task 2: Build decision-first overview and persistent case navigation

**Files:**
- Create: `frontend/src/components/CaseOverview.tsx`
- Modify: `frontend/src/components/PersonaSelector.tsx`
- Modify: `frontend/src/components/AgentPipelineStepper.tsx`
- Modify: `frontend/src/components/TabNavigation.tsx`
- Modify: `frontend/src/components/PolicyMatrix.tsx`
- Modify: `frontend/src/App.tsx`
- Create: `frontend/src/components/CaseOverview.test.tsx`

**Interfaces:**
- `CaseOverview` consumes `InvestigationData`, exposes `onOpenMemo`, `onOpenRules`, `onOpenForensics`, and `onOpenMl` callbacks.
- `TabNavigation` accepts an `onReturnToOverview` callback and renders it only away from Overview.
- `PolicyMatrix` accepts optional `focusedRuleCode?: string | null` and `onFocusedRuleHandled?: () => void`.

- [ ] **Step 1: Write failing overview/navigation tests**

Assert that Overview renders verdict plus evidence actions without the 14-rule list, and that a non-overview tab exposes `Back to case overview`.

- [ ] **Step 2: Run focused tests to verify RED**

Run: `npm test -- CaseOverview.test.tsx`

Expected: FAIL because `CaseOverview` and explicit return navigation do not exist.

- [ ] **Step 3: Implement the compact overview and disclosure-based pipeline**

Extract verdict, primary driver, snapshot metrics, and evidence buttons into `CaseOverview`; move full policy/ML/cross-check/narrative detail to their existing dedicated tabs. Render pipeline telemetry in a compact disclosure. Replace full persona cards with concise selected-case controls while preserving keyboard selection.

- [ ] **Step 4: Implement sticky tab navigation and focused-rule handoff**

Use a sticky navigation bar with a labelled return action; set Rules and `focusedRuleCode` from the driver action. Expand, scroll, and visibly mark that rule in `PolicyMatrix`, then clear the focus signal.

- [ ] **Step 5: Run focused tests to verify GREEN**

Run: `npm test -- CaseOverview.test.tsx`

Expected: PASS.

- [ ] **Step 6: Commit Task 2**

```bash
git add frontend/src/components/CaseOverview.tsx frontend/src/components/PersonaSelector.tsx frontend/src/components/AgentPipelineStepper.tsx frontend/src/components/TabNavigation.tsx frontend/src/components/PolicyMatrix.tsx frontend/src/App.tsx frontend/src/components/CaseOverview.test.tsx
git commit -m "feat: prioritize case decisions in workspace"
```

### Task 3: Make responsive header and dialogs explicit and accessible

**Files:**
- Modify: `frontend/src/components/Navbar.tsx`
- Modify: `frontend/src/components/ComparisonModal.tsx`
- Modify: `frontend/src/components/KeyboardShortcutsModal.tsx`
- Modify: `frontend/src/components/ReportViewModal.tsx`
- Modify: `frontend/src/styles.css`
- Create: `frontend/src/components/dialogs.test.tsx`

**Interfaces:**
- Each modal close control has an accessible name and invokes its supplied close callback.
- `ReportViewModal` accepts a `returnLabel?: string` defaulting to `Back to case`.
- `Navbar` groups secondary actions under a labelled mobile `Tools` control.

- [ ] **Step 1: Write failing accessibility and responsive-control tests**

Assert named dialog exits and a named `Tools` header control at the small-screen breakpoint behavior boundary.

- [ ] **Step 2: Run focused tests to verify RED**

Run: `npm test -- dialogs.test.tsx`

Expected: FAIL because dialog close buttons are unnamed and no mobile tools control exists.

- [ ] **Step 3: Implement named dialog exits and modal focus behavior**

Give every dialog a labelled title and close button; focus the dialog/first action on open and restore the trigger on close. Retain print behavior for the memo.

- [ ] **Step 4: Implement compact responsive header**

Use a compact brand treatment and a labelled Tools menu below the medium breakpoint, keeping compare, refresh, theme, and help reachable without page-level overflow.

- [ ] **Step 5: Run focused tests to verify GREEN**

Run: `npm test -- dialogs.test.tsx`

Expected: PASS.

- [ ] **Step 6: Build and manually verify viewport behavior**

Run: `npm run build`

Expected: PASS. Then inspect the local app at 1440px and 390px: verdict visible in the initial desktop view; no page-level horizontal overflow on mobile; the explicit overview return and dialog close actions work.

- [ ] **Step 7: Commit Task 3**

```bash
git add frontend/src/components/Navbar.tsx frontend/src/components/ComparisonModal.tsx frontend/src/components/KeyboardShortcutsModal.tsx frontend/src/components/ReportViewModal.tsx frontend/src/styles.css frontend/src/components/dialogs.test.tsx
git commit -m "feat: improve responsive workspace navigation"
```
