# Quickstart — 002 결함 수정 라운드 검증 가이드

**Feature**: `specs/002-defect-fix-design-conformance`

이 문서는 **이 라운드가 실제로 끝났는지 확인하는 방법**이다. 각 절은 spec 의 Success
Criteria 하나 이상에 대응한다.

## 사전 준비

```bash
cd /Users/fwani/Documents/develop/e2e-tester

# 백엔드
cd backend && .venv/bin/python -m pytest --version

# 프런트엔드
cd ../frontend && npm ci
```

## 기준선 (이 라운드 시작 시점 실측)

| 대상 | 명령 | 시작 시점 |
|---|---|---|
| 백엔드 unit+contract | `cd backend && .venv/bin/python -m pytest tests/unit tests/contract -q` | **726 passed** |
| 프런트엔드 | `cd frontend && npx vitest run` | **62 passed / 8 files** |

**이 수는 줄어들 수 없다** (RG-001·SC-111). 늘어나는 것은 정상이다.

---

## §1 프로젝트 인식 (US1 · SC-101·SC-102)

```bash
# 서버를 아무 디렉터리에서나 띄운다 — 실행 경로가 무관해야 한다는 것이 요점이다
cd /tmp && /Users/fwani/Documents/develop/e2e-tester/backend/.venv/bin/uvicorn \
  itb.api.app:app --host 127.0.0.1 --port 4320
```

| 단계 | 기대 결과 | 근거 |
|---|---|---|
| 1. 첫 화면을 연다 | 경로를 타이핑하는 자유 입력란이 **하나도 없다** | SC-102 |
| 2. 이름만 넣고 프로젝트를 만든다 | 생성되고, **만들어진 위치가 화면에 표시된다** | DR-006 |
| 3. 서버를 껐다 켜고 첫 화면을 연다 | 그 프로젝트가 **목록에 보인다** | SC-101 |
| 4. 목록에서 고른다 | 경로 입력 없이 열린다 | DR-003 |
| 5. "기존 프로젝트 열기" → 폴더 탐색 | 홈 하위 디렉터리가 보이고, 프로젝트인 항목이 구분된다 | DR-005 |
| 6. 프로젝트가 아닌 폴더를 고른다 | **무엇이 없어서 열 수 없는지** 문장으로 나오고 첫 화면에 머문다 | DR-008 |
| 7. 외부 경로로 연 뒤 재시작 | 그 프로젝트도 목록에 있다 | DR-007 |
| 8. 프로젝트 폴더를 지우고 목록을 본다 | 접근 불가로 구분 표시되고, 목록에서 치울 수 있다 | DR-009 |

**경계 확인** (헌법 보안 요구):

```bash
curl -s 'http://127.0.0.1:4320/api/fs/browse?path=/etc' | head -c 300
# 기대: 400 INVALID_PATH — 홈 밖은 거절

curl -s 'http://127.0.0.1:4320/api/fs/browse?path=/Users/fwani/../../etc' | head -c 300
# 기대: 400 INVALID_PATH — 정규화 후 경계 검사
```

응답에 **파일 이름이 하나도 없어야 한다.** 디렉터리만 반환한다.

---

## §2 녹화 중지 (US2 · SC-103)

| 단계 | 기대 결과 | 근거 |
|---|---|---|
| 1. 직접 녹화 시작 → 브라우저에서 3개 이상 조작 | Step 이 쌓이는 것이 보인다 | 001 FR-026 |
| 2. **중지를 누른다** | **화면이 그대로 있고 Step 목록이 보인다** | DR-010 |
| 3. Step 을 하나 삭제하고 하나 수정한다 | 반영된다 | DR-012 |
| 4. 이름을 붙여 저장한다 | **저장에 성공한다** | DR-013 |
| 5. 목록으로 나간다 | 저장된 테스트가 보인다 | — |
| 6. 다시 녹화 → 중지 → 저장하지 않고 나가기 | **유실 경고와 확인**을 받는다 | DR-014 |
| 7. 녹화 중 브라우저 창을 손으로 닫는다 | 그때까지 Step 이 남아 검토·저장 가능 | DR-015 |
| 8. Step 0개로 저장 시도 | 거절되고 사유가 나온다 | 001 FR-029 |

**2번과 4번이 이 라운드의 핵심이다.** 시작 시점에는 2번에서 목록으로 튕기고,
설령 화면에 머물러도 4번이 `SESSION_NOT_FOUND` 로 실패했다 (research R1).

**회귀 확인** — `review` 상태가 브라우저 명령을 거절하는지:

```bash
# 중지 후 세션 id 로
curl -s -X POST "http://127.0.0.1:4320/api/sessions/<id>/resume"
# 기대: 409 INVALID_TRANSITION — 브라우저가 없다 (001 FR-043a)
```

---

## §3 AI로 만들기 (US3 · SC-104·SC-105)

**자격 증명이 없는 상태에서 먼저 확인한다.** 이 라운드가 고치는 것이 바로 이 경로다.

```bash
env -u ANTHROPIC_API_KEY -u ANTHROPIC_AUTH_TOKEN \
  /Users/fwani/Documents/develop/e2e-tester/backend/.venv/bin/uvicorn \
  itb.api.app:app --host 127.0.0.1 --port 4320
```

| 단계 | 기대 결과 | 근거 |
|---|---|---|
| 1. 테스트 만들기 → AI로 만들기 | **시작 전에** 자격 증명이 없다는 사실과 조치 방법이 안내된다 | DR-021 |
| 2. 그래도 실행한다 | 화면이 즉시 바뀐다. **아무 변화 없이 끝나지 않는다** | SC-104 |
| 3. 실패한다 | **사람이 읽을 수 있는 실패 사유가 화면에 보인다** | SC-105 |
| 4. 그때까지 Step 이 있었다면 | 보존되어 있다 | 001 FR-067 |

시작 시점에는 1~3이 전부 무반응이었다 — `ai_error` 가 상태에 담기지만 그것을 그리는
컴포넌트가 `isAiSession` 뒤에 숨어 렌더되지 않았다 (research R2).

**자격 증명이 있는 상태**:

| 단계 | 기대 결과 | 근거 |
|---|---|---|
| 5. 자연어 지시를 넣고 실행 | AI 수행 화면(D3)으로 **독립 전환**된다 | DR-016·DC-008 |
| 6. 수행 중 | 시도 중인 동작이 보이고 성공한 Step 이 쌓인다 | DR-017·DR-018 |
| 7. 완료 | Step 목록 + 저장 수단 + "지시문은 저장되지 않는다" 안내 | DR-019 |

**원칙 II 확인** — 저장 후 재실행 시 언어모델 호출 0건 (SC-112):

```bash
cd backend && .venv/bin/lint-imports   # itb.execution → itb.llm 금지 계약
```

---

## §4 비밀 값 인라인 입력 (US4 · SC-106)

| 단계 | 기대 결과 | 근거 |
|---|---|---|
| 1. 비밀번호 필드가 있는 Step 을 편집 | **그 자리에서** 비밀 값을 넣을 수 있다. 화면 이동 0회 | SC-106 |
| 2. 공개키가 없는 상태에서 시도 | 그 자리에서 키 생성이 안내되고 이어서 진행된다 | DR-025 |
| 3. 값을 저장 | Step 에는 `{{변수명}}` 만 남는다 | DR-024 |
| 4. 이미 등록된 변수가 있으면 | 이름 중에서 고를 수도 있다 | DR-026 |

**보안 확인** (헌법 보안 요구 · 001 SC-010):

```bash
# 저장된 정의에 평문이 없어야 한다
grep -r "<입력한 비밀값>" ~/.local/share/itb/projects/<프로젝트>/tests/
# 기대: 결과 없음

# 값을 돌려주는 엔드포인트가 없어야 한다
curl -s http://127.0.0.1:4320/api/secrets | python3 -m json.tool
# 기대: 이름과 존재 여부만. 값 없음
```

---

## §5 키 쌍 만들기 (US5 · SC-107)

| 단계 | 기대 결과 | 근거 |
|---|---|---|
| 1. 키 관리 → 암호구절 없이 만들기 | 성공하고 상태가 갱신된다 | DR-028·DR-031 |
| 2. 8자 미만 암호구절 입력 | **제출 전에** 제약이 안내된다 | DR-029 |
| 3. 그래도 제출 | HTTP 상태 코드가 아닌 읽을 수 있는 사유 | DR-030·SC-107 |
| 4. 이미 있는데 다시 만들기 | 읽을 수 있는 안내 | DR-030 |

**전역 422 핸들러 확인** — 이것이 §5의 실제 수정이다 (research R3):

```bash
curl -s -X POST http://127.0.0.1:4320/api/keys/generate \
  -H 'Content-Type: application/json' -d '{"passphrase":"short"}' | python3 -m json.tool
```

기대:

```json
{ "error": { "code": "DEFINITION_INVALID", "message": "...", "detail": { "fields": [...] } } }
```

**`{"detail": [...]}` 형태가 나오면 실패다** — 그것이 시작 시점의 결함이다.

---

## §6 디자인 준수 (US6 · SC-108·SC-109·SC-110)

### 자동으로 확인되는 것

```bash
cd frontend

# DC-004 — 확정 디자인에 border-radius 가 0회이므로 구현에도 없어야 한다
grep -rn "border-radius\|--radius" src/ && echo "위반" || echo "OK"

# 기준: docs/design 에 radius 가 0회임을 재확인
grep -oi radius ../docs/design/*.dc.html | wc -l   # 기대: 0
```

### 사람이 확인하는 것

```bash
# 확정 디자인을 브라우저로 나란히 연다
open docs/design/TestList.dc.html
```

| 확인 | 방법 | 근거 |
|---|---|---|
| 8화면 대조 | `specs/002-.../design-conformance/<Screen>.md` 8개의 `판정` 칸을 채운다. `불일치`·`미판정` 0건이어야 한다 | SC-108 |
| 독립 화면 도달 | 8종 각각에 화면 전이로 도달한다. 특히 D3·D5·D6·D8 — 시작 시점에 Runner 안의 패널이었다 | SC-109 |
| 미정의 상태 기록 | `undefined-states.md` 의 건수가 실제 결정 건수와 같다 | SC-110 |

**판정은 구현자가 하지 않는다.** 자기 구현을 자기가 체크하면 대조가 아니라 자기
확인이다 (001 T156 이 같은 이유로 미완이다).

---

## §7 회귀 (US7 · SC-111·SC-112)

```bash
cd backend && .venv/bin/python -m pytest tests/unit tests/contract -q   # ≥726
cd backend && .venv/bin/lint-imports                                    # 원칙 II
cd frontend && npx vitest run                                           # ≥62
cd frontend && npx tsc --noEmit
```

**통합·e2e** (브라우저와 픽스처 앱이 필요하다):

```bash
cd backend && .venv/bin/python -m pytest tests/integration tests/e2e -q
```

### 테스트를 고쳐야 할 때

전면 재작성에서 깨지는 유일한 정당한 이유는 **표시 문구 변경**이다 (research R7 —
프런트엔드 테스트 62건이 전부 텍스트·역할·레이블로 질의하고 CSS·구조로 찾는 것이 하나도
없다).

| 상황 | 처리 |
|---|---|
| dc.html 의 문구가 현재 구현과 달라 `getByText` 실패 | 기대값을 **dc.html 의 문구로** 바꾼다. 근거(어느 파일의 어느 문구)를 남긴다 |
| 그 밖의 이유 | **고치지 않는다.** 구현이 틀린 것이다 |

삭제·`skip`·단언 제거는 어떤 경우에도 하지 않는다 (헌법 품질 게이트 4 · RG-002).

---

## 완료 판정 요약

| # | 확인 | 방식 | SC |
|---|---|---|---|
| 1 | 경로 입력란 0개, 재시작 후 목록에 100% 표시 | 사람 | SC-101·102 |
| 2 | 중지 후 Step 100% 보존·저장 성공 | 사람 | SC-103 |
| 3 | AI 실행 시 무반응 0건, 실패 사유 100% 표시 | 사람 | SC-104·105 |
| 4 | 비밀 값 입력까지 화면 이동 0회 | 사람 | SC-106 |
| 5 | 원시 상태 코드 노출 0건 | 사람 + `curl` | SC-107 |
| 6 | 8화면 대조 불일치 0건 | **리뷰어** | SC-108·109·110 |
| 7 | 백엔드 ≥726, 프런트 ≥62, 약화 0건 | 자동 | SC-111 |
| 8 | 재실행 시 언어모델 호출 0건 | 자동 (`lint-imports`) | SC-112 |
