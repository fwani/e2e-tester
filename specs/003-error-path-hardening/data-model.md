# Phase 1 Data Model: 이상 경로 견고성

**Feature**: `specs/003-error-path-hardening` | **Date**: 2026-09-04

이 라운드는 Step DSL 을 바꾸지 않는다. 새로 생기는 것은 **오류 계약**과 **이상 조작 시나리오
목록** 둘뿐이다.

---

## 1. 오류 계약 (Error Contract)

권위 정의 위치: `backend/src/itb/domain/error.py` (신설)
내보내기: `backend/schema/error-response.schema.json` → `frontend/src/types/generated/error-response.d.ts`

### 1.1 `Category` — 오류 분류

| 값 | 뜻 | 사용자가 할 수 있는 일 |
|---|---|---|
| `blocked` | 제품이 규칙에 따라 **의도적으로 거절**했다 | 있다. 입력이나 순서를 고쳐 다시 한다 |
| `broken` | 제품이 **처리하지 못했다** | 없다. 작업 보존 상태를 확인하고 보고한다 |

두 값뿐이다. `warning`, `unknown` 같은 세 번째 값을 두지 않는다 — 분류의 목적은 "내가 고칠 수
있는가"에 답하는 것이고, 답은 예/아니오 둘뿐이다. 판단이 서지 않는 오류는 `broken` 이다
(제품이 스스로를 설명하지 못한 것이므로).

### 1.2 `ErrorCode` — 오류 식별자

기존 23개를 그대로 유지하고 **하나를 더한다.**

| 추가 | 분류 | 쓰는 곳 |
|---|---|---|
| `INTERNAL_ERROR` | `broken` | 처리되지 않은 오류의 최종 처리기 |

`INTERNAL_ERROR` 를 만드는 이유는 EC-003 이다. 현재 최종 처리기는 `DEFINITION_INVALID` 를 쓰는데,
그 코드는 사용자가 잘못된 정의를 넣어 **정상적으로 거부당했을 때**도 쓰인다. 같은 코드가 두
분류에 걸쳐 있으면 분류 자체가 성립하지 않는다.

### 1.3 `CATEGORY` — 코드 → 분류 전수 대응표

모든 `ErrorCode` 가 정확히 하나의 `Category` 를 가진다. 대응표는 한 곳에만 있다.

| 코드 무리 | 분류 | 이유 |
|---|---|---|
| 프로젝트 (`PROJECT_NOT_OPEN`, `PROJECT_ALREADY_EXISTS`, `PROJECT_NOT_FOUND`, `INVALID_PATH`) | `blocked` | 사용자가 대상을 고르거나 만들면 된다 |
| 테스트 (`TEST_NOT_FOUND`, `STEP_LIST_EMPTY`, `DEFINITION_INVALID`) | `blocked` | 사용자가 내용을 고치면 된다 |
| 세션 (`SESSION_NOT_FOUND`, `SESSION_ALREADY_ACTIVE`, `NOT_PAUSED`, `INVALID_TRANSITION`, `TAB_NOT_FOUND`, `TAB_LIMIT_REACHED`) | `blocked` | 순서를 바꾸거나 기다리면 된다 |
| 세션 상실 (`SESSION_LOST`) | **판단 필요** | 브라우저가 사라진 원인이 외부인지 제품인지에 따라 갈린다. 구현 단계에서 정한다 — 기본은 `blocked`(외부 사정을 옮긴 것) |
| 비밀 값·키 (`KEY_MISSING`, `KEY_ALREADY_EXISTS`, `PASSPHRASE_REQUIRED`, `PASSPHRASE_INVALID`, `DECRYPT_FAILED`, `FINGERPRINT_MISMATCH`, `SECRET_NOT_FOUND`) | `blocked` | 사용자가 키·암호구를 다루면 된다 |
| 미지원 (`NOT_SUPPORTED`) | `blocked` | 다른 방법을 쓰면 된다 |
| 내부 (`INTERNAL_ERROR`) | `broken` | 사용자가 할 수 있는 일이 없다 |

**전수성은 자동으로 확인된다.** 코드를 추가하고 대응표에 넣지 않으면 검증이 실패한다 (RG-104-1).

### 1.4 `ErrorBody` — 오류 본문

| 필드 | 형 | 필수 | 설명 | 요구사항 |
|---|---|---|---|---|
| `code` | `ErrorCode` | ✓ | 오류 식별자 (기존) | — |
| `message` | 문자열 | ✓ | 사람이 읽는 이유. 그대로 화면에 보여줄 수 있다 (기존) | EC-004 |
| `detail` | 객체 | ✓ (기본 `{}`) | 기계가 읽는 부가 정보 (기존) | — |
| `category` | `Category` | ✓ | 막은 것 / 깨진 것 | EC-001 · EC-002 |
| `next_action` | 문자열 | ✓ (빈 문자열 금지) | 사용자가 지금 할 수 있는 일 | EC-004 |

**검증 규칙**

- `category` 는 호출부가 적지 않는다. `code` 로부터 대응표를 통해 결정된다 — 손으로 적으면 코드와 어긋난다
- `next_action` 은 코드마다 기본 문구를 두고, 상황에 따라 호출부가 덮어쓸 수 있다. 비어 있을 수 없다
- `message`·`next_action`·`detail` 어디에도 내부 파일 경로, 호출 스택, 비밀 값이 들어가지 않는다 (EC-005). 비밀 값 가리기는 001 의 기존 장치를 그대로 쓴다
- `category` 가 `broken` 인 오류는 `detail` 에 사용자 입력을 되돌리지 않는다 — 원인이 사용자 입력이 아니기 때문이다

### 1.5 `ErrorResponse` — 응답 봉투

```
{ "error": <ErrorBody> }
```

기존 형태 그대로다. 봉투를 바꾸지 않으므로 001·002 의 기존 검증이 깨지지 않는다 (RG-102).

### 1.6 실시간 통로의 오류 (EC-008)

진행 상황을 밀어 주는 연결로 전달되는 오류도 **같은 `ErrorBody`** 를 실어 보낸다. 이벤트 봉투만
다르고 본문은 같다. 화면은 요청 응답이든 실시간 통로든 **같은 통로**로 오류를 보여준다 (RG-104-4).

---

## 2. 이상 조작 시나리오 (Abnormal Scenario)

권위 정의 위치: `specs/003-error-path-hardening/contracts/abnormal-scenarios.json`
읽는 쪽: 백엔드 검증, 화면 검증, 커버리지 점검 — **모두 이 파일 하나를 읽는다**

### 2.1 필드

| 필드 | 형 | 필수 | 설명 |
|---|---|---|---|
| `id` | `AS-NNN` | ✓ | 시나리오 식별자. 검증 실패 보고와 tasks 추적에 쓴다 |
| `fault` | 열거 4종 | ✓ | `invalid-input` · `order-violation` · `external-failure` · `concurrency` |
| `surface` | 열거 3종 | ✓ | `api` · `ui` · `boundary` |
| `target` | 문자열 | ✓ | 조작 대상. `api` 면 경로, `ui` 면 화면 이름, `boundary` 면 경계 이름 |
| `operation` | 문자열 | ✓ | 무엇을 하는지 한 줄로. 사람이 읽는다 |
| `must_be_rejected` | 참/거짓 | ✓ | 이 조작이 **허용되어서는 안 되는가**. 판정축 ①의 "조용한 성공"을 판별하는 데 쓴다 |
| `preserves` | 문자열 \| `null` | ✓ | 이 조작 뒤 남아 있어야 하는 것 (판정축 ③). 보존 대상이 없으면 `null` |

**적지 않는 것**: 기대 응답 코드, 기대 메시지 문구, 기대 상태 코드. 명세의 결정에 따라 판정은
3축이 하며, 기대값을 시나리오에 적으면 구현이 틀렸을 때 기대값도 같이 틀린다.

`must_be_rejected` 는 예외다. 이것은 기대 응답이 아니라 **시나리오의 정의**다 — 무엇이 실패여야
하는지 모르면 "실패했는데 성공처럼 보이는 것"을 판별할 수 없다.

### 2.2 커버리지 규칙 (SC-206)

`fault` 4종 × `surface` 3종 = **12개 조합**. 각 조합에 최소 3건. 총 36건 이상.

커버리지는 자동으로 확인한다. 조합 하나라도 3건 미만이면 검증이 실패한다.

### 2.3 판정 결과 (Verdict)

시나리오마다 판정 3축의 결과를 가진다. 파일에 저장하지 않고 검증 실행 시점에 만들어진다.

| 축 | 통과 조건 |
|---|---|
| ① 응답의 형태 | 오류 스키마를 만족하고, `category`·`next_action` 이 있으며, 내부 경로·스택이 없다. `must_be_rejected` 가 참인데 성공하면 실패(조용한 성공) |
| ② 사용자 관점 | 결과가 화면에 드러나고, 무엇이 잘못됐는지와 다음 행동이 존재한다 |
| ③ 상태 보존 | `preserves` 가 가리키는 것이 조작 뒤에도 남아 있고 이어서 쓸 수 있다 |

**세 축을 모두 통과해야 그 시나리오가 통과다.** SC-201 은 전건 통과를 요구한다.

---

## 3. 바뀌지 않는 것

| 대상 | 상태 |
|---|---|
| Step DSL (`domain/step.py`, `domain/test_case.py`) | 변경 없음. 헌법 원칙 I·V 에 영향 없음 |
| 재실행 경로 | 변경 없음. LLM 호출이 새로 생기지 않는다 (헌법 원칙 II) |
| Locator 후보 해석 | 변경 없음 (헌법 원칙 IV) |
| 오류 응답 봉투 `{ "error": {...} }` | 형태 유지. 필드만 늘어난다 |
| 기존 `ErrorCode` 23개의 이름·값 | 유지. 개명하지 않는다 |
