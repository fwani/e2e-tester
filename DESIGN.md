---
name: ITB Quality Workbench
description: A Korean browser testing workspace with persistent project navigation and evidence-first execution views.
colors:
  accent: "#087E83"
  accent-hover: "#06666A"
  accent-t: "#E4F4F2"
  nav: "#F7F9FA"
  nav-ink: "#263B45"
  nav-muted: "#536974"
  nav-hover: "#E7EEF1"
  bg: "#F4F6F8"
  panel: "#FFFFFF"
  sunken: "#E8EEF1"
  sunken-2: "#F7F8FA"
  ink: "#162C38"
  ink-2: "#465B66"
  ink-3: "#627580"
  hair: "#DCE4E8"
  hair-2: "#BCCBD2"
  pass: "#1A7F45"
  pass-t: "#E8F5ED"
  fail: "#C8371D"
  fail-t: "#FCEDE9"
  fail-line: "#EFC7BC"
  warn: "#8F5A00"
  warn-t: "#FBF3E2"
  warn-line: "#E5D3AC"
  run: "#0B6BCB"
  run-t: "#E8F1FB"
  ai: "#6B3FD4"
  ai-t: "#F0EBFB"
typography:
  display:
    fontFamily: '"IBM Plex Sans KR", system-ui, sans-serif'
    fontSize: "24px"
    lineHeight: 1.5
    letterSpacing: "-0.035em"
  headline:
    fontFamily: '"IBM Plex Sans KR", system-ui, sans-serif'
    fontSize: "24px"
    letterSpacing: "-0.035em"
  title:
    fontFamily: '"IBM Plex Sans KR", system-ui, sans-serif'
    fontSize: "20px"
    fontWeight: 500
    lineHeight: 1.4
  body:
    fontFamily: '"IBM Plex Sans KR", system-ui, sans-serif'
    fontSize: "14px"
    fontWeight: 400
    lineHeight: 1.5
  label:
    fontFamily: '"IBM Plex Sans KR", system-ui, sans-serif'
    fontSize: "13px"
    fontWeight: 500
    lineHeight: 1.5
  metadata:
    fontFamily: '"IBM Plex Mono", ui-monospace, SFMono-Regular, monospace'
    fontSize: "12px"
    fontWeight: 400
    lineHeight: 1.5
rounded:
  base: "7px"
  chip: "5px"
  lg: "12px"
spacing:
  s-1: "4px"
  s-2: "8px"
  s-3: "12px"
  s-4: "16px"
  s-5: "24px"
  s-6: "32px"
components:
  button-primary:
    backgroundColor: "{colors.accent}"
    textColor: "{colors.panel}"
    rounded: "{rounded.base}"
    padding: "0 12px"
    height: "36px"
  button-primary-hover:
    backgroundColor: "{colors.accent-hover}"
  button-default:
    backgroundColor: "{colors.panel}"
    textColor: "{colors.ink}"
    rounded: "{rounded.base}"
    padding: "0 12px"
    height: "36px"
  button-danger:
    backgroundColor: "{colors.panel}"
    textColor: "{colors.fail}"
    rounded: "{rounded.base}"
    height: "36px"
  input:
    backgroundColor: "{colors.panel}"
    textColor: "{colors.ink}"
    rounded: "{rounded.base}"
    padding: "0 10px"
  navigation:
    backgroundColor: "{colors.nav}"
    textColor: "{colors.nav-ink}"
    width: "208px"
  panel:
    backgroundColor: "{colors.panel}"
    rounded: "{rounded.base}"
---

# Design System: ITB Quality Workbench

## Overview

**Creative North Star: “Quality Workbench”**

A light neutral project navigation rail gives the application a stable edge. The light workspace makes Korean test names, current actions, and execution evidence the main reading surface. Authoring uses a spatial sequence: Steps on the left, browser and work area in the center, selected Step details from the right.

This documents the implemented September 2026 redesign, following the user's rejection of a typography-only refresh. The historical 008 screen compositions are reference history, not the current layout specification. The system uses restrained borders, readable type, and semantic states rather than invented dashboard metrics.

**Key Characteristics:**

- Persistent project context with compact navigation during focused work.
- Separate visual regions for library groups, test identity, and latest outcome.
- Korean interface copy with monospace identifiers and technical evidence.
- Status text and icons accompany semantic colors.

## Colors

### Primary

Deep teal (`accent`) identifies primary actions; `accent-hover` deepens on hover, while `accent-t` marks group selection and native text selection. Teal is also the current global focus and caret color.

### Neutral

The dark marine navigation palette (`nav`, `nav-ink`, `nav-muted`, `nav-hover`) is independent of the light workspace palette. The canvas uses `bg`, working panels use `panel`, and `sunken` / `sunken-2` separate browser, diagnostics, and supporting areas. Three ink levels distinguish identity, ordinary supporting text, and metadata. Hairline tokens divide regions without heavy framing.

Semantic pairs retain their specific meanings: green `pass`, red `fail`, amber `warn`, blue `run`, and violet `ai`, each with a tint. Warning and error notices have dedicated border tokens. Blue links and informational notices remain part of the implementation; teal does not replace execution semantics.

**The State Rule.** Preserve stopped, partial, success, failure, and unrun as distinct labeled outcomes. Color alone must never carry their distinction.

## Typography

IBM Plex Sans KR carries Korean interface copy. IBM Plex Mono is reserved for IDs, locators, durations, code, and compact technical labels. Body numerals are tabular.

The frontmatter defines the observed hierarchy: lobby display, library headline, workbench title, body, and technical label. The compact navigation brand is 24px; ordinary navigation labels are 13px. Metadata commonly uses 11–12px. Primary controls use 14px semibold text; small controls use 12px. Do not convert Korean prose into letter-spaced technical labels.

## Layout

The desktop shell has a full-height sticky project rail (208px), shrinking to 192px below 1400px. Test/session detail routes always use the compact 68px rail; all routes use compact navigation at 900px and below. Compact links retain accessible names or titles.

The library separates group navigation (178px) from the test collection with a 28px gap. Below 1400px, groups become a wrapping horizontal toolbar. Result filters sit above search and maintenance actions. A test name and its ID occupy one identity column; its latest result has a separate column. Rows have a minimum height of 82px. Below 900px, the table retains an 850px minimum width and scrolls inside its content area.

The workbench puts the Step list on the left (400px). The center contains the target browser/evidence and the phase-specific work area. Step details open from the right over the central area (640px detail token). The phase heading wraps as needed, has a minimum height of 86px, and uses 18px by 24px padding. The Step header is 84px to keep selection tools on a separate line. Step rows remain 52px.

Workbench notices occupy an in-flow dock directly beneath the phase heading. It grows only when populated, has a 160px maximum height with scrolling, and never overlays Step controls. Its notices are at least 44px high. Other application toast surfaces retain their separate overlay behavior.

Result evidence keeps at least 400px of height, with an explicit full-size image link. Diagnostics have a 280px allocation and scroll independently; the result workspace itself can scroll vertically. This prevents long diagnostics from compressing the evidence into an unreadable strip.

The project lobby divides into a dark introduction (30%, minimum 260px) and the project chooser, below a shared 56px header. At 900px and below it becomes one column. Settings retain reading-width forms. Spacing uses the documented scale, with composition-specific 18px and 28px gaps where present.

## Elevation & Depth

Most hierarchy comes from background tone, spacing, and thin dividers. Controls use the subtle `e-1` shadow; dialogs and the Step detail overlay use `e-2`. In-flow workbench notices are explicitly shadowless. Active navigation uses an inset one-pixel outline rather than a floating card treatment. No decorative motion is needed; preserve reduced-motion behavior when introducing transitions.

Shadow definitions live in the sidecar because the frontmatter format does not support them. Implementation sources remain the authority for exact CSS.

## Shapes

Controls and ordinary panels share the base radius; status chips use the smaller chip radius, and larger settings/dialog surfaces use the large radius. Dividers are usually one pixel. Disabled controls retain their place with dashed borders and muted text. Destructive actions use an outlined red treatment, keeping solid teal reserved for the primary action.

## Components

### Buttons

Solid teal primary controls lead the next action. Default controls are white with a subtle shadow and border; dangerous controls use red text and border. Small controls are 30px high. Hover uses the corresponding tint or deeper primary color. Keyboard focus uses a two-pixel teal outline with a three-pixel offset; active boxed buttons remove their shadow. Disabled controls retain explanations and keyboard-accessible recovery actions nearby.

### Inputs

White inputs have a one-pixel neutral border, the base radius, and a minimum height of 36px. AI instruction fields use the violet border. Invalid fields use the error border; disabled inputs become transparent with dashed borders. Editable workbench titles keep the title's location and reveal editing treatment on hover/focus.

### Navigation

Project switching appears beneath the brand, tests and creation occupy the main group, and secret/key settings sit at the bottom. Selected links use the lighter marine surface and an inset outline. Preserve the labels “테스트 라이브러리”, “테스트 작성”, “비밀 값”, and “키 관리”.

### Chips and group selection

Outcome chips combine text, icon, and semantic tint. Unrun state uses a dashed neutral treatment. Library group selection uses teal tint and stronger text rather than the outcome palette. Groups wrap at the narrower desktop breakpoint.

### Panels, Steps, and evidence

White panels and subtle borders organize forms and supporting content. Step identity and selection controls stay separate; compact row actions must not crowd the name or duration. Duration text does not wrap. Technical values may truncate in a row, with detail inspection available. Evidence remains inspectable at full size, and diagnostics scroll rather than displacing it.

### Notices

Notices preserve semantic color, context, dismissal, and a useful recovery action when available. The workbench dock sits in document flow beneath the heading and above the Step/browser body. Do not recreate the former control-covering toast placement.

## Do's and Don'ts

- **Do** use the token primitives in `frontend/src/theme/tokens.css` and the workspace palette/composition in `frontend/src/theme/workspace.css`. `tokens.app.css` is generated by `node frontend/scripts/split-canon.mjs`.
- **Do** preserve Korean copy, keyboard operation, disabled-action explanations, and the existing project/session/API contracts.
- **Do** validate the actual library, editing, execution, and result screens at desktop widths, including scrolling and focus.
- **Do** keep current execution distinct from the last saved result.
- **Don't** treat the old 008 geometry, legacy CSS comments, or old pixel snapshots as the new redesign's acceptance criteria.
- **Don't** reduce the redesign to font changes, hide controls beneath notices, or compress result evidence to make diagnostics fit.
- **Don't** invent metrics or decorative dashboard panels that compete with tests and evidence.


### Quiet admin refinement — September 22

The user requested a lighter admin service with less bold text and fewer competing buttons. This revision takes precedence over earlier dark-navigation descriptions and component defaults.

- Open-workspace navigation uses #F7F9FA with #263B45 text, #536974 secondary text and #E7EEF1 selection. The project chooser also uses a light introduction panel and modest 24px headings.
- Library titles are 23px and workbench titles 20px, weight600. List identities and emphasis use500. Ordinary buttons and badges use400 and no shadow.
- Result filters use a restrained underline. Row execution and result links have no persistent box. Library rows have a72px minimum.
- Numbering, Excel export and import live under the button-triggered `목록 관리` popover. Secondary Step actions live under `Step 편집 도구`; action availability and explanations remain inside it.
- Pointer devices reveal Step row operations on hover, focus within the row, or selection. Touch devices keep them visible; keyboard focus reveals the actions before activation.
- Primary creation, execution and save actions remain directly accessible. APIs and destructive-action confirmations are unchanged.


### Typography roles — September 22

The light admin visual weight is preserved. `workspace.css` owns a rem-based role scale (16px browser default): page 24px/1.35, workbench and dialog title 20px/1.4, section title 16px/1.5, body/input/regular control 14px/1.5–1.6, field labels/helper prose/small controls 13px/1.45–1.55, IDs/badges/counters 12px. Compact inspector headers remain 14px; they do not compete with the selected Step title. Long Korean helper text no longer shares the compact metadata size. Browser zoom remains available. Dense authoring and tables justify 14px body instead of a marketing/prose 16px floor. No font family or weight expansion was introduced; unused Black Han Sans was removed from the font request.


### Start screen simplification — September 22

The user requested only essential functions before starting a test. `/tests/new` uses a centered 680px form and full navigation: URL, a compact record/AI switch, and one selected start action with a quiet back action. Direct recording is the default. AI instructions appear only for AI mode; switching preserves both inputs and draft entry preselects AI. Busy state locks setup inputs and prevents duplicate starts. Availability warnings, invalid URL errors and draft provenance remain visible when relevant.

Empty browser/Step panels, disabled save/name/Step editing controls, duplicated remedies, authoring badges and multi-paragraph method cards were removed from this pre-session screen. Recording and AI sessions still open the existing full workbench. This intentionally supersedes the old compose-only UI placement assertions requiring an empty workbench before a session exists; execution capability rules and backend routes are unchanged.


### Whole-workspace simplification — September 22

The same essential-first structure now applies across the application. The library uses a flat table, with group filtering and management in the toolbar; repeated group headings and duplicate counters are removed. Test metadata shares the identity column, and result plus time share a result column. An empty library has one creation entry point; authoring-method selection belongs to the start screen.

The workbench has one toolbar. Session stop/pause and save remain directly available. Secondary navigation, pacing and editing options are grouped in labeled button-triggered popovers. The Step footer separates adding Steps, editing tools and test settings. Active recording keeps its stop control exposed. AI assistance has explicit “대화 열기” and “대화 닫기” controls; activity or a new conversation opens it, preserving draft input when closed. Editing now places Step fields beside the list in the main pane; live sessions and result inspection retain their inspector behavior.

Results show only available evidence tabs. Failure summary and diagnosis remain exposed, while detailed locator attempts are available in a labeled tool panel. Project selection uses one bounded, centered work surface with a title and creation action above the project list. Existing-folder opening and Excel import are direct buttons; a single import action must not sit behind another popup. Optional testId configuration stays visible in the creation form. Row maintenance, key technical details and destructive key maintenance use labeled button-triggered panels. Confirmation, validation, sensitive-value protection, stale conflicts and recovery actions remain intact.

This replaces the old presentation contracts for permanently visible empty panels, unsupported evidence tabs and a shared inspector placement in editing. Backend API and capability rules are unchanged.

Auxiliary panels use Base UI Popover for viewport collision handling, outside-click dismissal, Escape, and focus restoration. They do not change the document layout. Their inputs stay mounted to preserve drafts. Executing a workbench action closes its panel so confirmations remain reachable. Recording stop stays directly exposed.
