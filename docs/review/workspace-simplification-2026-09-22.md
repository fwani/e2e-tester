# Whole-workspace simplification

Requested direction: preserve core test authoring/execution functions while simplifying every screen, following the approved lightweight admin style.

- Library: single flat list and toolbar; group management by selection/disclosure; merged identity metadata and run metadata; single creation entry on empty state.
- Workbench: one toolbar; secondary controls in labeled menus; Step addition/settings collapsed until needed; active recording stop remains exposed.
- Editing: selected Step uses the main pane instead of a third panel over empty content. Empty AI helper is collapsed and automatically opens on activity/conversation.
- Results: only supported evidence tabs, direct failure/diagnosis summary and expandable attempt details.
- Project/settings: removed promotional and nested-card structure, disclosure for auxiliary imports/settings/maintenance. Required validation, warnings and confirmations retained.

Meaningful checks preserve callback routes, CRUD and confirmations, group sorting/filtering, draft and AI flows, input retention, duplicate-start guards, keyboard/focus and sensitive-value behavior. Updated layout tests explicitly encode the requested new presentation.

Browser coverage includes both start modes, expanded group controls, Step addition, AI assistance and editing options, plus existing library, edit, result, settings and live recording scenes. AI authoring/takeover and external-file import runtime scenes still require model/file input; they are covered by component behavior tests rather than claimed as browser runs.

The visual scanner now accounts for native closed details: Chromium can retain descendant geometry without painting it. It ignores unpainted descendants, and treats intentional menu panels as layers without exempting their own controls from clipping/coverage checks. Registered popup overflow is limited to observed menu scenes and their trigger containers.

Validation completed: production build passed (existing bundle-size warning); 121 functional test files / 1452 tests passed and 8 screen-report tests passed separately. Browser sweep reached all 100 screen/viewport combinations with zero unregistered findings. Its 73 allowed findings cover deliberate popups, fixture/network states and one bounded chat scroll case. At 1280x800 the chat panel was measured at clientHeight 225, scrollHeight 249; scrolling 24px fully exposed the send button and its hit test passed. No unreachable control was exempted. Impeccable detector and git diff --check passed.
