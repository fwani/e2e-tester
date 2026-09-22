# Test start simplification — 2026-09-22

User direction: simplify the start screen to essential functions while retaining the light admin styling.

The pre-session screen now contains a start URL, a compact direct-recording/AI switch, and one primary start action. Direct recording is preselected. AI selection reveals the instruction field; switching preserves the values. Draft entry keeps its AI selection, instruction and provenance. Busy input locks, URL validation, unavailable-AI warnings and existing session callbacks are retained.

Removed from this screen: empty browser preview, empty Step list, selection controls, Step-edit palette, disabled name/save controls, duplicated start remedies, phase badges, and explanatory method cards. These belong to the session workbench after starting. The backend routes and capability engine are unchanged.

Tests previously requiring the empty workbench were updated to the requested pre-session design. Behavioral coverage preserves record/AI callbacks, URL validation, busy guards, draft handling, error display and sensitive-value protections, and adds method-switch input preservation. Screen sweep now includes both record and AI start states at four desktop widths.

Validation: production build passed (existing bundle-size warning), 121 functional test files / 1449 tests passed, and the screen-report tests passed separately after report regeneration. All 84 screen/viewport combinations were reached with no unregistered findings (36 pre-existing allowed cases). One existing bulk-delete confirmation at 1920px timed out on the first pass; a targeted rerun passed without product changes. The Impeccable detector returned no findings and git diff --check passed.
