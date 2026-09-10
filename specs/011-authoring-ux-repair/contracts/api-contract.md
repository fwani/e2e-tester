# API 계약 — 011

**대상**: [data-model.md](../data-model.md) §2

서버가 바뀌는 것은 **셋**이다. 기존 라우트는 하나도 없어지지 않는다.

---

## 1. 세션 Step 배치 삭제 (신규)

```
POST /api/sessions/{session_id}/steps:delete
```

**요청**

```json
{ "step_ids": ["s3", "s4", "s5"] }
```

| 필드 | 제약 |
|---|---|
| `step_ids` | 1개 이상. 각 항목 1~100자. 중복 불가. `extra="forbid"` |

**응답** — `200 StepsResponse` (기존 Step 조작 응답과 같은 형)

**오류**

| 상황 | 코드 | 본문 |
|---|---|---|
| 세션 없음 | `404 SESSION_NOT_FOUND` | 기존 규칙 |
| `step_ids` 중 없는 것이 있다 | `404 STEP_NOT_FOUND` | **어느 id 인지 전부** 나열. 아무것도 지우지 않는다 |
| 중복 id | `400 DEFINITION_INVALID` | 어느 id 가 중복인지 |
| 국면이 편집 가능하지 않다 | 기존 국면 검사 그대로 | 기존 규칙 |

**원자성** (FR-388): Step 목록을 한 번에 교체한다. 검증 → 새 목록 구성 → 교체 순이며, 검증에서
걸리면 목록에 손대지 않는다. 부분 적용을 만드는 경로가 없다.

**왜 `POST …:delete` 인가**: 이 저장소가 이미 쓰는 형태다 (`steps:manual`·`steps:reorder`).
`DELETE` 에 본문을 싣는 것은 프록시·클라이언트에 따라 벗겨지고, 쿼리에 싣는 것은 목록이 길면
URL 길이에 걸리며 삭제 대상이 접근 로그에 남는다.

---

## 2. 저장된 테스트 편집 — 변경 없음

```
PUT /api/tests/{test_id}/definition
```

`edits` 에 `{"op": "delete", "step_id": "…"}` 를 **여러 개** 실으면 이미 원자적 복수 삭제다.
라우트·모델을 바꾸지 않는다.

```json
{
  "revision": "…",
  "edits": [
    { "op": "delete", "step_id": "s5" },
    { "op": "delete", "step_id": "s6" },
    { "op": "delete", "step_id": "s7" }
  ]
}
```

**주의**: `edits` 는 순서대로 적용된다. `delete` 는 id 로 대상을 찾으므로 순서에 의존하지 않는다 —
화면이 인덱스로 보내면 앞의 삭제가 뒤의 인덱스를 밀어 다른 Step 이 지워진다. **id 로 보낸다.**

---

## 3. Step 별 스크린샷 서빙 (신규)

```
GET /api/tests/{test_id}/result/steps/{index}/screenshot
```

| 항목 | 값 |
|---|---|
| `index` | 0 기반 Step 인덱스. `ge=0` |
| 성공 | `200`, `image/png`, `FileResponse` |

**오류**

| 상황 | 코드 | `next_action` |
|---|---|---|
| 결과 없음 | `404 TEST_NOT_FOUND` | 「먼저 실행하세요」 |
| 결과를 읽을 수 없음 | `400 DEFINITION_INVALID` | 기존 `get_result` 규칙과 같다 |
| `index` 가 그 실행의 Step 수 이상 | `404 TEST_NOT_FOUND` | 그 실행의 Step 수를 밝힌다 |
| `screenshot === null` | `404 TEST_NOT_FOUND` | `screenshot_note` 를 사유로 실어 보낸다 |
| 파일이 사라졌다 | `404 TEST_NOT_FOUND` | 「실행 산출물(.runs/)이 지워졌을 수 있습니다」 (기존 문구) |
| 경로가 프로젝트 루트 밖 | `400 INVALID_PATH` | 기존 `get_artifact` 의 경계 검사를 **공유한다** |

**`kind` 를 늘리지 않는 이유**: `GET …/result/artifacts/{kind}` 는 실행 전체에 하나씩인 산출물을
위한 것이고, `kind` 별 media type 표가 그 전제 위에 있다. Step 별은 인덱스를 갖는 다른 성질이며,
`kind` 에 넣으면 인덱스를 실을 자리가 없어 쿼리 매개변수가 `kind` 마다 달라진다.

**경계 검사를 공유한다**: 프로젝트 루트 밖을 가리키는 경로를 서빙하지 않는 검사가 `get_artifact`
안에 인라인으로 있다. 그것을 함수로 뽑아 둘이 함께 쓴다 — 복제하면 한쪽만 고쳐지는 날이 온다.

---

## 4. 결과 모델의 확장 (호환)

`StepResult` 에 선택 필드 둘이 는다.

```
screenshot:      str | None = None    # 프로젝트 루트 기준 상대 경로
screenshot_note: str | None = None    # 남기지 못한 사유
```

**기존 `result.json` 은 그대로 읽힌다** — 둘 다 기본값이 있다 (SC-613).
`backend/tests/contract/test_schema_drift.py` 가 스키마 변화를 잡으므로 그 검사의 기대값을
함께 갱신한다.

`Artifacts` 는 바꾸지 않는다. 실패 스크린샷(`failure_screenshot`)은 그대로 남고, 실패 Step 의
`screenshot` 이 **같은 경로**를 가리킨다 — 파일은 한 벌이다 (FR-394).

---

## 5. 산출물 디스크 구조

```
.runs/
├── TC-001/
│   ├── result.json
│   ├── result-full.json
│   ├── failure.png          ← 기존. 실패 시점 (실패 Step 의 screenshot 이 이것을 가리킨다)
│   ├── console.log          ← 기존
│   ├── network.log          ← 기존
│   └── steps/               ← 신규
│       ├── 0.png
│       ├── 1.png
│       └── 3.png            ← 2 는 민감 값이 있어 쓰지 않았다 (구멍이 정상이다)
└── _draft/
    └── steps/               ← 저장 전 초안 세션도 같은 구조
```

**보관** (FR-396a): `.runs/<ID>/` 는 이미 테스트당 하나이고 「최근 1건만」이다
(`repository.py` 주석). 실행 **시작 시** `steps/` 를 비우면 clarify 결정 3 이 그대로 충족된다.
새 보관 장치를 만들지 않는다.

**비우기 실패**: 실행을 막지 않는다 (FR-396c). 사유를 `ArtifactPaths.notes` 에 남긴다 —
기존에 산출물을 남기지 못한 사유를 담는 자리다.

**`.gitignore`**: `.runs/` 가 이미 들어 있다 (`repository.py:49`). 하위 디렉터리가 늘어도
추가 작업이 없다.
