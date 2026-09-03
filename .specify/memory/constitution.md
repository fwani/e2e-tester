<!--
Sync Impact Report
==================
Version change: (none / template) → 1.0.0
Bump rationale: Initial ratification. The prior file was the unfilled scaffold with
                unfilled bracket tokens, so this is a first definition rather than an amendment.

Modified principles: none (initial definition)

Added sections:
  - Core Principles I..V
      I.   Unified Step Model (NON-NEGOTIABLE)
      II.  Deterministic Replay (NON-NEGOTIABLE)
      III. Stateful Interactive Runner
      IV.  Locator Resilience
      V.   Asset Portability
  - Technology & Security Constraints
  - Development Workflow & Quality Gates
  - Governance

Removed sections: none

Deferred / TODO items: none
  RATIFICATION_DATE set to 2026-09-03 (date of first fill; no earlier adoption record exists).

Source of authority for principles: docs/prd.md
  - Principle I   ← PRD §9 Test Step Model, §17 차별화 #1
  - Principle II  ← PRD §12 AI 사용 원칙, §6 (자연어 명령을 테스트로 저장하지 않음), §17 #4
  - Principle III ← PRD §7 Interactive Test Editing, §8 Human Takeover, §2 P5
  - Principle IV  ← PRD §10 Locator 전략
  - Principle V   ← PRD §13 Playwright Export
  Principles I-III are the three MVP technical validation targets named in PRD §20.
-->

# Interactive AI Test Builder Constitution

## Core Principles

### I. Unified Step Model (NON-NEGOTIABLE)

Human browser actions and AI Agent browser actions MUST be recorded into one and the same
Test Step DSL. That DSL is the single source of truth for the product.

- The UI Step Editor, the AI authoring path, the Recorder, and the Playwright Generator MUST all
  read and write this one model. No component may introduce a private or parallel representation
  of a test.
- A Step MUST NOT carry information about who authored it as a semantic difference. Provenance
  (human / AI / imported) MAY be recorded as metadata, but MUST NOT change how the Step executes.
- Playwright code is a *generated artifact*, never the stored form of a test. The product MUST NOT
  persist tests as Playwright source and re-parse it.
- Adding a new Step type requires updating the DSL schema first; consumers follow.

**Rationale**: PRD §17 states the primary differentiator as "Human과 AI가 동일한 테스트를 작성할
수 있다". That claim collapses the moment two authoring paths produce two shapes of test — a Step
edited in the UI would then behave differently from the same Step produced by the Agent. One model
is what makes Pause → Edit → Resume across mixed-authorship tests coherent at all.

### II. Deterministic Replay (NON-NEGOTIABLE)

The replay path of a saved test MUST NOT call an LLM.

- LLM use is confined to Test Authoring. A successful AI Agent run MUST be compiled into
  deterministic Steps and stored in that compiled form.
- The natural-language instruction itself MUST NOT be stored as the executable test. It MAY be
  retained as documentation of intent alongside the compiled Steps.
- Any code path reachable from "run a saved test" that constructs an LLM request is a violation and
  MUST fail review, regardless of how it is guarded at runtime.
- An LLM-backed Step type MUST NOT be introduced in this MVP. PRD §12 defers it to future review;
  introducing it requires a constitution amendment, not a feature decision.

**Rationale**: PRD §2 P3 identifies four costs of judging the screen with AI on every run —
non-determinism, LLM cost, execution latency, and result drift on model change — and PRD §18 sets a
Replay Success Rate target of ≥95%. That target is unreachable if replay outcome depends on a model
version. Keeping the boundary architectural (rather than a config flag) is what makes the guarantee
auditable.

### III. Stateful Interactive Runner

The Runner MUST preserve live browser session state across Pause → Edit → Resume.

- On Pause, the browser session MUST remain open and its state (auth, navigation, form contents,
  in-page JS state) MUST survive Step edits.
- Editing Steps MUST NOT force a run from the beginning. Resume from the current browser state and
  re-run from a chosen Step MUST both be supported.
- Steps executed while paused — recorded by direct user operation, or added via natural language —
  MUST be captured into the same Step Model (see Principle I) and inserted at the paused position.
- When an AI Step fails, the session MUST be held open so the user can take over in place. Failure
  MUST NOT tear down the browser.

**Rationale**: PRD §2 P5 identifies the long fix loop as a core problem — for integration tests
with lengthy preconditions (login → data setup → navigation), restarting from zero on each edit is
the dominant cost. PRD §8 Human Takeover is only meaningful if the session outlives the failure.
This is the hardest of the three MVP validation targets and therefore the one most likely to be
quietly compromised; it is stated here to prevent that.

### IV. Locator Resilience

The Recorder MUST NOT store a single CSS selector as an element's identity.

- For every recorded element the Recorder MUST collect all available locator candidates
  (test id, ARIA role, accessible name, associated label, visible text, stable attributes, CSS path).
- Resolution MUST follow this priority order:
  `testId` → `role` + accessible name → `label` → `text` → stable attribute → CSS.
- CSS is the last resort and MUST NOT be the only stored candidate.
- Locator resolution logic MUST live in one place shared by the Runner and the Playwright Generator,
  so a generated test resolves elements the same way an in-product run does.
- Auto-applied self-healing is out of MVP scope (PRD §15). Candidate fallback within a recorded
  Step is not self-healing and is required.

**Rationale**: PRD §10 states the goal as tests that survive screen structure changes. An nth-child
CSS path breaks on any sibling insertion, which would surface to users as flaky tests and directly
undermine the ≥95% Replay Success Rate target.

### V. Asset Portability

Generated tests MUST remain usable without this product.

- Export MUST produce a standard runnable Playwright project (spec files, `playwright.config`,
  dependency manifest) that executes with a stock Playwright toolchain and no product runtime.
- Exported tests MUST NOT depend on a product API, product-hosted service, or proprietary runtime
  shim.
- The Test Step DSL MUST be stored in a documented, human-readable, plain-text format placed under
  version control by the user. No opaque binary or undocumented schema for user test assets.

**Rationale**: PRD §13 makes this an explicit product promise: "사용자는 제품을 사용하지 않더라도
생성한 테스트 자산을 계속 사용할 수 있다". Beyond adoption, it is a design constraint — a DSL that
must compile to portable standard Playwright cannot quietly accumulate product-only semantics, which
protects Principle II.

## Technology & Security Constraints

**Stack** (fixed for this MVP; changing it requires an amendment):

- Backend: Python with FastAPI. Browser automation via Playwright for Python.
- Frontend: React.
- Test Step DSL: plain-text structured format (YAML/JSON per PRD §9), schema-validated on both ends.

**Cross-language schema duty**: because backend and frontend are different languages, the Step DSL
schema MUST have one authoritative definition, with the other side generated or validated from it.
Two hand-maintained copies of the schema are a Principle I violation.

**Security requirements** (organization mandate, non-negotiable):

- No hardcoded secrets. Credentials, API keys, and tokens MUST come from environment or a secret
  store. This includes test fixtures and example files.
- Test data captured by the Recorder MAY contain credentials the user typed into the target
  application. Recorded input values for password-type and marked-sensitive fields MUST be stored
  as variable references, never as literals, and MUST be masked in UI, logs, screenshots metadata,
  and exports.
- All external input MUST be validated at the boundary: API request bodies, Step DSL loaded from
  disk, natural-language input forwarded to an LLM, and target-page content read by the Recorder.
- Generated Playwright code MUST be treated as data during generation and MUST NOT be produced by
  unescaped string concatenation of page-derived text.
- The product drives a real browser against user-specified targets. It MUST NOT be given
  capabilities beyond that; no arbitrary shell execution from a Step.
- Errors MUST be handled explicitly. A failing Step MUST surface a diagnosable result
  (error, screenshot, log per PRD §11), never a silent pass or an unhandled crash of the Runner.

## Development Workflow & Quality Gates

**Specification flow**: Features follow the Spec-Driven Development cycle
(`specify` → `clarify` → `plan` → `tasks` → `implement`). Requirements are traceable to `docs/prd.md`.

**Gates that MUST pass before a feature is considered done**:

1. **Principle compliance** — every change is checked against Principles I–V. A change that touches
   the replay path MUST include explicit evidence that no LLM call is reachable from it.
2. **Round-trip integrity** — for any change to the Step DSL, Recorder, or Generator:
   record → store → replay in-product → export → run exported test, all produce consistent results.
3. **Tests** — automated tests accompany the change. The product is a testing tool; shipping it
   without its own tests is not acceptable. Recorder, Runner state machine, and Generator each
   require tests at the unit level, plus at least one end-to-end scenario per user-facing flow.
4. **No disabled tests** — a test MUST NOT be deleted, skipped, or weakened to make a build pass.
   A genuinely obsolete test is removed with its reason recorded.
5. **Success-metric awareness** — changes affecting the flows measured in PRD §18
   (test creation, NL conversion, replay, takeover recovery) note their expected effect on those
   metrics.

**Simplicity**: Prefer the simplest design that satisfies the principles. Complexity that is not
required by a principle or a stated requirement MUST be justified in the plan or removed.

**Out of scope** (PRD §15) MUST NOT be built speculatively: mobile/native app testing, API test
builder, performance/load testing, visual regression, cross-browser cloud farm, complex test
management, auto-applied AI self-healing, automatic test-data generation.

## Governance

This constitution supersedes other development practices and conventions in this repository. Where
a tool default, a habit, or a convenience conflicts with a principle here, the principle wins.

**Amendment procedure**:

1. A proposed amendment is written down with the principle affected, the concrete motivation, and
   the migration impact on existing code and stored test assets.
2. It is reviewed and approved by the project maintainers before any dependent code lands.
3. On approval, `.specify/memory/constitution.md` is updated in a dedicated commit carrying the
   version bump and a Sync Impact Report.
4. Principles marked NON-NEGOTIABLE (I, II) require explicit justification of why the original
   rationale no longer holds. A deadline or convenience is not sufficient justification.

**Versioning policy** (semantic):

- **MAJOR** — a principle is removed or redefined in a backward-incompatible way; existing compliant
  code may become non-compliant.
- **MINOR** — a principle or section is added, or existing guidance is materially expanded.
- **PATCH** — clarification, wording, or typo fixes with no change in meaning.

**Compliance review**:

- Every pull request verifies compliance with Principles I–V and the Quality Gates above.
- Plans (`plan.md`) include a Constitution Check; unresolved violations block `tasks`/`implement`.
- Deviations discovered after merge are recorded and either corrected or elevated to an amendment
  proposal. They are not left as undocumented precedent.

**Version**: 1.0.0 | **Ratified**: 2026-09-03 | **Last Amended**: 2026-09-03
