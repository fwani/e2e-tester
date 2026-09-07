# 원칙 준수 증거 (006 T091)

헌법 Quality Gate 1 은 "모든 변경이 원칙 I~V 에 대해 확인된다" 를 요구하고, 재생 경로를
건드리는 변경에는 **언어모델이 그 경로에서 도달 불가하다는 명시적 증거**를 요구한다.

이 문서는 그 증거를 한 곳에 모은 것이다. 문장이 아니라 **깨지면 알 수 있는 테스트**를
근거로 든다 — 문장은 코드가 바뀌어도 그대로 남는다.

## I. Unified Step Model (NON-NEGOTIABLE)

| 주장 | 근거 |
|---|---|
| Step DSL 을 바꾸지 않았다 | `git diff` 에 `domain/step.py`·`domain/locator.py` 변경 없음. `schema/step*.json` 드리프트 0 (T087) |
| 편집 규칙의 구현이 하나다 | `tests/unit/test_definition_edit_core.py::test_definition_route_reuses_the_shared_edit_core` — 정의 라우터가 `itb.execution.step_edits` 를 임포트하고 `update_step`·`delete_step`·`reorder_steps`·`derive_variables` 를 부른다 |
| 편집 화면이 하나다 | 진입점 3개가 같은 화면에 도달한다: `frontend/tests/EditEntryPoints.test.tsx` (App 을 통째로 렌더해 실제로 걷는다) |
| 변수 파생이 하나다 | `_variables_for()` 가 `derive_variables()` 로 위임한다. 두 벌이 아니라 **이식**이다 (T005·T006) |

**범위 밖으로 둔 것**: Step 을 "비활성/건너뛰기" 로 표시하는 개념. DSL 스키마 변경이므로
별도 결정이 필요하다 (명세 「하지 않는 것」).

## II. Deterministic Replay (NON-NEGOTIABLE)

| 주장 | 근거 |
|---|---|
| 신규 엔드포인트 2개에서 작성 계층이 도달 불가하다 | `test_definition_edit_core.py::test_definition_route_never_reaches_the_authoring_layer` — `itb.authoring` 임포트가 없고 `anthropic`·`validate_instruction`·`Agent(` 문자열이 없다 |
| 편집 판정이 전부 규칙 기반이다 | 순서 경고(`_reorder_warning`)·미정의 참조 경고(`undefined_variable_references`)·민감 참조 거절(`_reject_plaintext_over_secret`) 모두 순수 함수 |
| 자연어 Step 추가를 옮기지 않았다 | `POST /api/sessions/{id}/ai-step` 그대로. 정의 편집 경로에 그 연산이 없다 |

## III. Stateful Interactive Runner

| 주장 | 근거 |
|---|---|
| 상태 기계에 새 상태가 없다 | `tests/unit/test_pause_before_index.py::test_step_pacing_still_works_beside_the_new_gate` — `SessionState` 에 편집 전용 상태가 없다 |
| `pause_before_index` 가 기존 `PAUSED` 로 들어간다 | 같은 파일 `test_pause_gate_uses_the_existing_pause_command` |
| 004 의 `한 스텝씩` 을 흔들지 않았다 | 같은 파일의 그 테스트 + `tests/unit/test_runner_pacing.py` 전체 통과 |
| 편집이 처음부터 실행을 강요하지 않는다 | 이 기능이 그것을 **강화**했다 — 브라우저 없이 고치고, 필요하면 지정한 Step 직전에서 멈춘 세션을 연다 |

## IV. Locator Resilience

| 주장 | 근거 |
|---|---|
| 해석 순서를 바꾸지 않았다 | `test_definition_edit_core.py::test_locator_priority_is_untouched_by_this_feature` — `PRIORITY` 튜플을 값으로 단정한다 |
| 후보를 편집으로 손댈 수 없다 | `test_definition_edit_api.py::test_locator_fields_are_not_accepted` (5가지 필드 전수) + `test_update_step_has_no_target_parameter` |
| 후보 검증 상태를 조작하지 않는다 | 편집 요청 모델에 `status` 를 받는 필드가 없다. 후보 수집은 `itb.recording.repick` 만 한다 |

**이것이 FR-187 을 범위에서 뺀 이유다** (설계 조사 R6). 브라우저 없이 검증할 수 없는 후보를
`verified` 로 적으면 FR-019a 와 SC-008 측정이 오염되고, 아니면 조용한 무효 편집이 된다.

## V. Asset Portability

| 주장 | 근거 |
|---|---|
| 저장 형식이 그대로다 | `test_definition_edit_api.py::test_saving_keeps_the_plain_text_definition_shape` — 편집한 값 한 줄만 바뀐다(`updated_at` 제외). 저장이 파일을 재배치하면 사용자의 버전 관리가 쓸모 없어진다 |
| DSL ↔ Playwright 대응이 바뀌지 않았다 | Step 모델 무변경(위 I)이므로 생성기 대응도 무변경 |
| 사용자의 직접 수정을 정상 사용으로 인정한다 | `DEFINITION_STALE` 이 그 인정이다 — 편집기로 YAML 을 고친 것을 감지하고 조용히 덮어쓰지 않는다 (FR-209) |

**Export 는 이 기능에서도 구현되지 않는다.** 001 plan 이 등록한 기존 릴리스 게이트 항목이며
006 이 새로 만든 이연이 아니다. 이 기능이 지는 두 의무(DSL 불변·평문 저장 형식 유지)는
위 표에서 지켜졌다.

## 조직 보안 요건

| 요건 | 근거 |
|---|---|
| 경계 검증 | 요청 모델 전부 `extra="forbid"`. 알 수 없는 필드·범위 밖 인덱스·알 수 없는 `step_id` 거절 — `test_definition_edit_api.py` 의 거절 계약 8건 |
| 민감 값 마스킹 | 평문을 받는 필드가 **존재하지 않는다** (`test_no_field_accepts_plaintext_secrets`). 민감 참조를 평문으로 바꾸는 편집은 400 (`test_replacing_secret_reference_with_plaintext_is_rejected`). 응답에 평문 없음 (`test_response_never_carries_plaintext_secret`) |
| 민감 표시 강등 금지 | `test_sensitive_flag_survives_editing` — 강등되면 재실행이 빈 값을 채운다 |
| 오류를 명시적으로 | 저장 실패는 500 `STORAGE_WRITE_FAILED` 와 다음 행동. 조용한 성공 경로가 없다 |
| 원자적 쓰기 | `repo.write_test()` → `itb.storage.atomic`. 부분 저장된 정의 파일이 생기지 않는다 |
| 하드코딩된 비밀 없음 | 신규 코드에 자격 증명·키가 없다. 테스트 재료의 민감 값은 참조(`{{SECRET_PASSWORD}}`)뿐이다 |

## 성공 지표 인식 (Quality Gate 5)

이 기능은 PRD §18 의 "테스트 생성" 이 아니라 **수정 왕복**에 영향을 준다. 그 측정은
SC-303(왕복 끊김 0건)·SC-305(실행 잡기 0건)이며, 둘 다 자동 테스트로 고정했다
(`EditEntryPoints.test.tsx`, `test_pause_before_index.py`).
