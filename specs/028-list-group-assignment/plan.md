# Implementation Plan: 목록에서 그룹 지정하기 — 하이픈 접두어와 끌어 놓기

**Branch**: `028-list-group-assignment` | **Date**: 2026-09-30 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/028-list-group-assignment/spec.md`

---

## Summary

사용자가 `IT-PM`·`IT-DM` 으로 테스트를 나누려다 두 곳에서 막혔다 — 접두어가 하이픈을 받지
않고, 그래서 그룹이 없으니 목록의 「그룹으로 옮기기」도 나타나지 않았다.

**접근**

1. 접두어 규칙을 「하이픈으로 이은 마디들, 각 마디는 영문 대문자로 시작」으로 넓힌다.
   옛 규칙의 상위집합이므로 저장된 자산을 건드리지 않는다.
2. 식별자에서 접두어를 뽑는 17개 자리를 **도메인의 읽기 함수 하나로 모은다.** 앞에서
   자르던 것을 뒤에서 자르는 것으로 바꾸되, 그 규칙이 다시 열일곱 벌이 되지 않게 한다.
3. 화면의 손으로 적은 정규식을 **스키마에서 생성한 상수**로 바꾼다 (헌법 Cross-language
   schema duty).
4. 목록 행을 끌 수 있게 하고, **끌기 중에만** 나타나는 표적 띠를 둔다. 013 SC-627 을
   지키면서 목록 안에서 지정이 끝난다.
5. 그룹이 0개일 때 선택 띠에서 사라지던 길을 막는다 — 끌기를 쓰지 않는 사용자에게도
   목록에서 그룹을 만들어 넣는 경로가 생긴다.

## Technical Context

**Language/Version**: Python 3.12 (백엔드) · TypeScript 5 / React 19 (프론트)

**Primary Dependencies**: FastAPI · Pydantic v2 · Playwright (백엔드) / React Router ·
`@base-ui/react` · Tailwind (프론트). **이번에 더하는 런타임 의존성 없음** (R5).

**Storage**: 사용자 데이터 디렉터리의 파일 — `project.yaml` 과 `tests/<식별자>-<이름>.yaml`

**Testing**: pytest (`scripts/test-backend.sh` 로 두 계층) · vitest + Testing Library (jsdom)

**Target Platform**: 데스크톱 브라우저. 터치 끌어 놓기는 범위 밖 (spec Assumptions).

**Project Type**: 웹 (백엔드 + 프론트)

**Constraints**:

- 접두어 길이 상한 12자 — 식별자가 파일 이름에 들어간다
- Pydantic v2 의 `pattern` 은 Rust regex — 선읽기·후읽기를 쓸 수 없다 (R1)
- 저장된 자산에 마이그레이션을 요구하지 않는다 (FR-011)

**Scale/Scope**: 백엔드 17개 호출 지점 + 정규식 2개 + 검증 함수 1개, 프론트 목록 화면
1개 · 그룹 띠 1개 · 생성 스크립트 1개

## Constitution Check

*GATE: Phase 0 이전에 통과해야 하고, Phase 1 이후 다시 본다.*

| 원칙 | 판정 | 근거 |
|---|---|---|
| I. Unified Step Model (NON-NEGOTIABLE) | 해당 없음 | Step DSL 을 건드리지 않는다. 식별자와 목록 화면만 다룬다 |
| II. Deterministic Replay (NON-NEGOTIABLE) | 해당 없음 | 재실행 경로에 LLM 호출을 더하지 않는다. 이 기능에 LLM 이 없다 |
| III. Stateful Interactive Runner | 해당 없음 | 러너 상태를 건드리지 않는다 |
| IV. Locator Resilience | 해당 없음 | 로케이터를 건드리지 않는다 |
| V. Asset Portability | **통과 — 강화됨** | 식별자는 사람이 읽는 평문으로 남고, 파일 이름 규칙도 그대로다. 접두어 모양이 넓어질 뿐 불투명해지지 않는다 |
| Cross-language schema duty | **이번에 위반을 고친다** | 화면이 접두어 정규식을 손으로 복제하고 있었다 (`TestGroupBar.tsx:142`). 생성물로 바꾼다 (R2) |
| 보안 — 입력 검증 | 통과 | 접두어는 경계에서 스키마로 검증된다. 규칙이 넓어져도 검증 지점은 그대로다 |
| 품질 게이트 3 — 검증 동반 | 통과 | 규칙·읽기 함수·파일명 파싱·끌어 놓기·하위 호환 각각에 검증을 둔다 |
| 품질 게이트 4 — 검증을 끄지 않는다 | 통과 | 기존 검증 중 접두어를 쓰는 것들이 새 규칙에서도 통과해야 한다 |
| 단순성 | 통과 | 끌어 놓기에 라이브러리를 더하지 않고, 합친 엔드포인트를 만들지 않는다 (R5 · R6) |

**Phase 1 이후 재확인**: 설계가 새 계약이나 새 저장 형식을 만들지 않았다. 판정 그대로다.

## Project Structure

### Documentation (this feature)

```text
specs/028-list-group-assignment/
├── plan.md              # 이 파일
├── research.md          # R1~R8 결정
├── data-model.md        # 접두어·식별자·읽기 함수·끌기 상태
├── quickstart.md        # 검증 절차
├── contracts/
│   ├── api-contract.md  # 제약 변경과 호출 순서
│   └── ui-contract.md   # UC-028-01~07
├── checklists/
│   └── requirements.md
└── tasks.md             # /speckit-tasks 가 만든다
```

### Source Code

```text
backend/src/itb/
├── domain/
│   ├── test_case.py          # 접두어·식별자 패턴, 읽기 함수 (새 단일 출처)
│   └── draft.py              # 접두어 읽기 1곳
├── storage/
│   ├── repository.py         # 파일 이름 정규식, 접두어 읽기 1곳
│   └── test_moves.py         # 번호 읽기 1곳
├── portability/
│   ├── importer.py           # 5곳 + validate_prefix
│   └── exporter.py           # 1곳
├── sharing/
│   ├── planner.py            # 2곳 + 자동 접두어 생성
│   └── builder.py            # 1곳
└── api/routes/
    ├── groups.py             # 2곳 (그중 하나는 파일명 손 복원)
    ├── tests.py              # 2곳
    └── sharing.py            # 1곳 (파일명에서)

frontend/
├── scripts/gen-types.mjs                   # 제약 상수 생성 추가
└── src/
    ├── types/generated/                    # 생성물 (손으로 고치지 않는다)
    ├── components/
    │   ├── TestGroupBar.tsx                # 손으로 적은 정규식 제거
    │   └── (신규) 끌기 표적 띠
    └── pages/TestList.tsx                  # 행 끌기, 표적 배선, 선택 띠 구멍 막기
```

### 검증

```text
backend/tests/    — 접두어 규칙 · 읽기 함수 · 파일명 파싱 · 하위 호환 · 경로별 회귀
frontend/tests/   — 끌기 표적 노출/숨김 · 끌기 대상 규칙 · 새 그룹 흐름 · 선택칸 구멍
```

## 실행 순서 (의존 관계)

```
1. 접두어 규칙 + 읽기 함수 (도메인)        ← 나머지 전부가 여기에 기댄다
2. 17개 호출 지점 전환 + 파일명 정규식
3. 스키마 내보내기 → 제약 상수 생성 → 화면 정규식 제거
4. 선택 띠 구멍 막기 (그룹 0개일 때)       ← 끌기와 독립, 먼저 값을 낸다
5. 끌기 표적 띠 + 행 끌기
6. 「새 그룹으로」 흐름
```

1~3 이 US1 이고, 4~6 이 US2·US3·US4 다. 1~3 없이 4~6 만 해도 화면은 동작하지만 사용자가
겪은 문제의 절반만 풀린다. 반대로 1~3 만 해도 `IT-PM` 그룹을 만들 수 있게 되므로 그
자체로 값을 낸다.

## Complexity Tracking

*헌법 원칙이 강제하지 않는데 더한 복잡도 — 없음.*

| 항목 | 왜 복잡도가 아닌가 |
|---|---|
| 도메인 읽기 함수 신설 | 17벌의 손 복제를 하나로 줄인다. 복잡도를 더하는 것이 아니라 덜어낸다 |
| 제약 상수 생성 추가 | 헌법 Cross-language schema duty 가 요구한다. 선택이 아니다 |
| 끌어 놓기 | 사용자가 요구한 기능 본체다. 라이브러리 없이 브라우저 기본 기능으로 구현한다 |

**연기(deferral) 없음.** 이 기능에는 나중으로 미루는 원칙 만족이 없다.
