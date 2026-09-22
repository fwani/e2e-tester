# Product

<!-- impeccable:product-schema 1 -->

## Platform
web

## Product Purpose
ITB is a local browser test authoring and execution tool. Users record browser actions or give AI instructions, edit Steps, replay tests, and inspect failures.

## Users
The current brief prioritizes people finding a test and understanding its latest execution result. Specific job titles are not established.

## Capabilities and Constraints
- Preserve project, group, draft, recording, AI authoring, execution, pause/edit/resume, and result inspection flows.
- Keep existing API contracts and local project data unchanged.
- Keep Korean product language, keyboard operation, disabled-action explanations, and distinct stopped/partial/success/failure outcomes.
- This is a desktop workbench: group navigation adapts in narrow windows; wide test tables scroll inside the content area and forms use a reading width.

## Product Principles
- Identify the test and its current execution state immediately.
- Make the next useful action discoverable.
- Distinguish current execution from the last saved result.
- Present errors with context and a recovery action.

## Evidence on Hand
README.md; frontend/src/pages; frontend/src/components/workbench; scripts/screen_sweep.py.
