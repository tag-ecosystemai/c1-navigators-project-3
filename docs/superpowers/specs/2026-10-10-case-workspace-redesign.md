# Case Workspace Redesign

## Goal

Make the credit-risk case workspace easier to scan and navigate by putting the current decision first, moving detailed evidence into dedicated views, and giving every drill-down a clear return path.

## Scope

- Keep the existing backend contract, persona data, policy calculations, and printable memorandum unchanged.
- Replace the duplicated overview dashboard with a compact case brief.
- Add persistent case navigation with an explicit overview return action.
- Preserve a user’s active tab when changing the selected persona.
- Make modal exits accessible and predictable.
- Make the top navigation fit a 390px viewport without horizontal clipping.

## Information Architecture

The overview contains only:

1. A concise current-case selector.
2. The verdict, primary driver, and a small set of decision metrics.
3. Direct actions to review rules, investigate transactions, inspect risk signals, or open the memo.

Rules, Forensics, and ML retain their existing detailed components as separate views. Pipeline telemetry is moved behind a compact expandable disclosure so it does not displace the decision. The tab/navigation bar is sticky beneath the application header and displays a labelled `Case overview` return action whenever the user is away from the overview.

## Navigation Rules

- Selecting another persona retains the current detailed view; it does not reset to Overview.
- The logo and explicit `Case overview` action both return to Overview.
- Opening and closing the memo restores the previous tab, not an unconditional Overview state.
- Comparison and keyboard-shortcut modals use named `Close` controls. The memo uses `Back to case`.
- The primary-driver link opens the Rules tab, scrolls to the specific driver, and supplies a visible route back through persistent navigation.

## Responsive Rules

- The header uses a compact brand treatment under the medium breakpoint.
- Secondary header actions are grouped behind a labelled `Tools` control on small screens.
- The persona selector becomes compact horizontal case buttons rather than five full briefing cards on small screens and in the primary analyst flow.
- Detail components may retain their internal horizontal overflow where necessary for ledger data, but the page itself must not overflow horizontally.

## Accessibility

- Named controls are required for every icon-only button, especially modal exits.
- Dialogs expose `role=dialog`, `aria-modal=true`, and labelled titles.
- Tabs include relationships to their tab panels.
- Modal focus is moved to the dialog on open and restored to the opener on close.

## Verification

- TypeScript/Vite production build passes.
- Browser check at 1440px confirms the verdict appears in the initial viewport and detailed content is reachable through dedicated views.
- Browser check at 390px confirms no header or page-level horizontal overflow and all navigation remains reachable.
- Keyboard checks cover tab selection, explicit overview return, modal close, and memo return-to-origin behavior.
