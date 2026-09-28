# Implementation Plan: 입력값 검증 — 칸에 무엇이 들어 있는지 묻는다

**Branch**: `023-input-value-assertion` | **Date**: 2026-09-28 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/023-input-value-assertion/spec.md`

---

## Summary

검증 종류에 **`value` 하나를 더한다.** 스키마 변경은 그것이 전부다.

입력 칸을 대상으로 한 텍스트 검증은 구조적으로 100% 실패한다 — 입력값은 텍스트 노드가
아니라 요소의 값 속성이기 때문이다. 표현 수단이 없어서 생긴 문제이므로 어휘를 하나
더하는 것이 답이고, 021 이 상태 검증을 더한 것과 같은 모양이다.

조사에서 계획을 바꾼 것이 셋 있다.

| 조사 | 원래 생각 | 확인한 사실 |
|---|---|---|
| R1 | 생성기가 `TargetLocator.tag` 로 matcher 를 고른다 | **고를 필요가 없다.** 종류가 곧 답이다 |
| R2 | 기존 스크러버가 비밀번호를 가려 준다 | **실패할 때만 샌다.** 스크러버는 복호화된 값만 안다 |
| R3 | 판정을 `build_assertion` 에 두면 된다 | **AI 경로는 거기를 지나지 않는다.** 021 의 경고도 닿지 않고 있다 |

R2 가 이 계획에서 가장 무거운 부분이다. 나머지는 값 하나를 더하고 그 값이 지나는 자리를
빠짐없이 덮는 일이다.

---

## Technical Context

**Language/Version**: Python 3.12 (backend) · TypeScript 5 / React 19 (frontend)

**Primary Dependencies**: FastAPI · Playwright for Python · Pydantic v2 · Vite · Tailwind

**Storage**: 테스트 정의는 사람이 읽는 평문 파일. 민감 값만 `secrets.local.yaml` 에 봉인

**Testing**: pytest (`backend/tests/{unit,contract,integration,abnormal}`) · Vitest (frontend)

**Target Platform**: 로컬 실행 (macOS · Linux). 브라우저는 Playwright Chromium

**Project Type**: Web application (backend + frontend)

**Performance Goals**: 이번 변경에 새 목표 없음. 실행 시점에 대상 속성을 한 번 더 읽는
비용이 늘지만 검증 하나당 왕복 1회 수준이다

**Constraints**:
- 정의 파일 하위 호환 — 마이그레이션 없이 열리고 실행돼야 한다 (FR-040)
- 비밀번호 평문이 정의·로그·결과·공유 묶음 어디에도 남지 않아야 한다 (FR-015~FR-017, 헌법 보안 제약)
- 제품 안 실행과 내보낸 코드가 같은 판정을 해야 한다 (헌법 원칙 V)

**Scale/Scope**: 검증 종류 6 → 7. 백엔드 6개 모듈 · 프론트 3개 파일 · 고정 대상 1개 화면

---

## Constitution Check

*GATE: Phase 0 전에 통과해야 하고, Phase 1 설계 후 다시 본다.*

### Phase 0 이전

| 원칙 | 판정 | 근거 |
|---|---|---|
| **I. Unified Step Model** (비협상) | **통과** | 종류 값 하나만 늘린다. 병행 표현을 만들지 않는다. 세 작성 경로가 같은 `Assertion` 을 만든다 |
| **II. Deterministic Replay** (비협상) | **통과** | 재실행 경로에 LLM 호출이 없다. 값 관찰·비교는 결정적이다 |
| **III. Stateful Interactive Runner** | **해당 없음** | 세션 수명·일시정지 동작을 건드리지 않는다 |
| **IV. Locator Resilience** | **통과** | 후보 수집은 기존 `collect_by_selector` 를 그대로 쓴다. CSS 단독 후보를 만들지 않는다 |
| **V. Asset Portability** | **주의** | 새 종류를 생성기에 반영하지 않으면 내보내기가 깨진다. **이번 범위에 포함**했다 (US2) |
| **보안 제약** (조직 명령, 비협상) | **주의** | 입력값 검증은 비밀번호 평문의 **새 유출 경로**다. FR-015~FR-017 로 함께 막는다 |

### Phase 1 설계 후 재확인

| 원칙 | 재확인 |
|---|---|
| I | 판정 규칙을 **한 함수**에 두고 두 작성 경로가 호출한다 (research R3). 규칙이 경로마다 갈리지 않는다 |
| II | **마스킹은 설명 문자열만 바꾼다.** 통과·실패는 실제 값으로 판정하므로 「같은 화면이면 같은 결과」가 유지된다 |
| IV | `TargetLocator` 에 필드를 더하지 않는다. 성질 판정은 살아 있는 요소에서 하고 저장하지 않는다 (research R1) |
| V | [contracts/export-mapping.md](./contracts/export-mapping.md) 에 네 비교 방식의 대응을 모두 규정했다. `contains` 는 표준에 직접 대응이 없어 `expect.poll` 로 옮긴다 — 표준 API 만 쓴다 |
| 보안 | 판별 규칙을 새로 만들지 않고 녹화와 **같은 출처·같은 규칙**을 쓴다. 관찰값 마스킹은 스크러버에 기대지 않고 별도로 보장한다 |

**위반 없음. Complexity Tracking 을 채우지 않는다.**

### 품질 게이트 대응

| 게이트 | 이 기능에서 |
|---|---|
| 1. 원칙 준수 | 재실행 경로 변경분(관찰 함수·마스킹)에 LLM 도달 경로가 없음을 테스트로 남긴다 |
| 2. 왕복 정합 | 기록 → 저장 → 제품 내 실행 → 내보내기 → 내보낸 테스트 실행을 입력값 검증으로 한 번 완주한다 (quickstart §7) |
| 3. 테스트 | 도메인·실행기·생성기 각각 단위 테스트 + 사용자 흐름당 통합 1건 |
| 4. 비활성 테스트 금지 | 기존 테스트를 끄지 않는다. 입력 칸 대상 텍스트 검증이 여전히 실패하는 것은 **의도된 동작**이므로 그대로 둔다 |
| 5. 성공 지표 | 검증 작성·재실행 흐름에 영향. 실패하던 시나리오가 통과로 바뀌므로 Replay Success Rate 에 양의 방향 |

---

## Project Structure

### Documentation (this feature)

```text
specs/023-input-value-assertion/
├── plan.md                        # 이 파일
├── spec.md
├── research.md                    # Phase 0 — R1~R8
├── data-model.md                  # Phase 1
├── quickstart.md                  # Phase 1 — 사람이 손으로 확인하는 순서
├── contracts/
│   ├── assertion-surface.md       # 작성 표면 (경로별 지원·거절·문구)
│   └── export-mapping.md          # 정의 ↔ 표준 Playwright 대응
├── checklists/
│   └── requirements.md
└── tasks.md                       # /speckit-tasks 가 만든다
```

### Source Code (repository root)

변경이 닿는 자리만 적는다. **조용히 빠질 수 있는 곳에 ★** 를 붙였다 (data-model §5).

```text
backend/
├── src/itb/
│   ├── domain/
│   │   └── assertion.py           # ★ AssertionKind 에 value · 집합 · 형태 규칙 · docstring 정정
│   ├── execution/
│   │   ├── assertion_builder.py   # ★ 대상 성질 판정(신규 함수) · ELEMENT_KINDS · default_label
│   │   ├── element_probe.py       #   서술(tag·type)을 함께 돌려주는 진입점
│   │   └── step_executor.py       #   _assert_value 관찰 함수 + 비밀번호 관찰값 마스킹
│   ├── generator/
│   │   └── playwright_gen.py      #   value 종류의 네 비교 방식 대응
│   ├── authoring/
│   │   └── tools.py               # ★ assert_condition 도구 설명 + 성질 판정 호출
│   ├── api/routes/
│   │   └── steps.py               #   거절을 오류로, 안내를 경고 통로로
│   └── schema/                    #   재생성 (값 추가가 스키마에 반영된다)
└── tests/
    ├── unit/                      # 도메인 형태 규칙 · 표시 이름 · 생성기 · 성질 판정
    ├── contract/                  # 작성 표면 · 내보내기 대응
    └── integration/               # 실행 · 비밀번호 마스킹 · 하위 호환

frontend/
├── src/
│   ├── lib/wording.ts             # ★ 종류 이름·설명·요약·안내 문구 (문구의 소유자)
│   ├── components/AssertionForm.tsx  # ★ KINDS · NEEDS_TARGET · NEEDS_VALUE · comparesValue
│   └── types/generated/           #   재생성
└── (테스트는 기존 위치 규약을 따른다)

fixtures/sample-app/               # 여러 줄 입력 칸 추가 (제품 아님 — 테스트 대상)
```

**Structure Decision**: 기존 구조를 그대로 쓴다. 새 모듈·새 패키지를 만들지 않는다. 이번
변경은 **이미 있는 축에 값 하나를 더하는 것**이고, 새 자리를 만들면 「검증 종류는
`domain/assertion.py` 에 있다」는 기존의 단일 지점이 흐려진다.

---

## 구현 순서와 의존

```
① 도메인 (assertion.py)
      ↓ 스키마 재생성
② 실행 (step_executor.py)          ⟍
③ 생성 (playwright_gen.py)          ⟩ ①에만 의존 — 서로 독립, 병행 가능
④ 성질 판정 (assertion_builder.py) ⟋
      ↓
⑤ 두 작성 경로 연결 (steps.py · tools.py)     ← ④에 의존
⑥ 프론트 (wording.ts · AssertionForm.tsx)     ← ①의 타입 재생성에 의존
      ↓
⑦ 비밀번호 마스킹 (②+④ 위에)
⑧ 고정 대상 · 하위 호환 · 전량 검증
```

**①이 먼저인 이유**: 헌법의 교차 언어 스키마 의무 — DSL 스키마를 먼저 바꾸고 소비자가
따른다 (원칙 I). 프론트 타입이 ①에서 생성되므로 ⑥은 그전에 시작할 수 없다.

**⑦을 분리한 이유**: ②와 ④가 각각 동작한 뒤에 그 위에 얹는 층이다. 섞어서 만들면 마스킹
때문에 실패한 것인지 관찰이 틀린 것인지 가릴 수 없다. **그리고 이것이 유일한 새 보안
요구라 독립적으로 검증돼야 한다.**

---

## 위험과 대응

| 위험 | 어떻게 드러나는가 | 대응 |
|---|---|---|
| **`default_label` 분기 누락** | 조용히 `"검증"` 이라는 이름이 붙는다 | 단위 테스트에서 7종 전부의 표시 이름을 확인한다 |
| **AI 경로가 성질 판정을 건너뜀** | 화면에서는 거절되는데 AI 는 만든다 | 판정을 공용 함수로 두고 **두 경로 각각에 테스트**를 건다 |
| **비밀번호 관찰값 유출** | 실패한 실행 결과 파일에 평문이 남는다 | quickstart §6-3 의 `grep` 을 자동 검증으로도 만든다 |
| **`select` 값이 예상과 다름** | FR-033 안내 문구가 거짓이 된다 | 문구를 쓰기 전에 실측한다 (research R8) |
| **`contains` 내보내기 형태** | 제품과 내보낸 코드의 판정이 갈린다 | `expect.poll` 형태를 계약에 고정하고 왕복 정합으로 확인한다 |
| **부정 비교 + 값 관찰의 조합** | 021 의 관찰 루프가 값에서도 같게 도는지 미확인 | 통합 테스트 + quickstart §3 에서 실제로 돌린다 |

---

## 이번에 하지 않는 것

명시하지 않으면 구현 중에 범위가 번진다.

| 하지 않는 것 | 왜 |
|---|---|
| 두 작성 경로의 통합 | `build_assertion` 은 예외를 던지고 AI 경로는 `{"error"}` 를 돌려준다. 통합하면 모델이 보는 오류 형태가 바뀐다 — 이번 기능과 무관한 위험이고, 규칙 단일화는 공용 함수로 이미 달성된다 |
| 021 의 경고가 AI 경로에 없는 것 | **021 의 빈칸이지 023 의 결함이 아니다.** research R3 에 기록했고 `converge` 가 판단한다 |
| 체크 상태 검증 | 021 에서 범위 외. 이 검증으로 대신할 수 없다는 사실만 분명히 한다 |
| 손으로 넣는 Step 에 대상 지원 | 그 경로의 설계 전제를 바꾸는 별도 주제 |
| 기존 텍스트 검증의 자동 변환 | FR-041 — 뜻을 추측해 정의를 바꾸지 않는다 |
| `select[multiple]` 대응 | 제품과 내보낸 코드가 **같게** 동작하므로 원칙 V 는 지켜진다. 사용자의 뜻과 다를 수 있는 것은 별개 문제로 계약에 한계로 적었다 |

---

## Complexity Tracking

> Constitution Check 에 위반이 없으므로 비워 둔다.

해당 없음.
