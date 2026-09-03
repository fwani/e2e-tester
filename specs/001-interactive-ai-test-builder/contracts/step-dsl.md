# Test Step DSL Contract

**이것이 사용자에게 가장 중요한 계약이다.** 제품 UI나 API는 바뀔 수 있지만, 이 파일들은 사용자가 git에
커밋해 보관하는 자산이다 (FR-088b, 원칙 V).

**권위 정의**: `itb/domain/*.py` 의 Pydantic v2 모델. 여기서 `schema/step-dsl.schema.json` 을 내보내고,
그것으로 프론트엔드 TypeScript 타입을 생성한다 (research R6).
**저장 형식**: YAML, 안전 로더만 사용.
**호환성 정책**: 필드 추가는 부 버전, 의미 변경·필드 제거는 주 버전. `dsl_version` 을 파일에 기록한다.

---

## 전체 예 — 단일 탭

```yaml
dsl_version: 1
id: TC-001
name: 프로젝트 생성
authoring_mode: record
start_url: https://example.internal/login
browser: chromium
variables:
  - name: PROJECT_NAME
    value: TEST
    sensitive: false
  - name: LOGIN_PASSWORD
    value: null            # 민감 변수는 반드시 null (불변식)
    sensitive: true
steps:
  - id: step-01
    type: fill
    label: 비밀번호 입력
    author: human
    tab: 0
    timeout_ms: 5000
    value: "{{LOGIN_PASSWORD}}"
    target:
      tag: input
      label: { value: 비밀번호, status: verified }
      css:   { value: "#password", status: verified }

  - id: step-02
    type: click
    label: 프로젝트 생성 클릭
    author: human
    tab: 0
    timeout_ms: 5000
    target:
      tag: button
      test_id:         { value: create-project, status: verified }
      role: button
      accessible_name: 프로젝트 생성
      text:            { value: 프로젝트 생성, status: verified }
      css:             { value: ".project-header button:nth-child(2)", status: verified }

  - id: step-03
    type: assertion
    label: '"TEST" 표시 확인'
    author: human
    tab: 0
    timeout_ms: 5000
    assertion:
      kind: visible
      value: "{{PROJECT_NAME}}"
      target:
        text: { value: TEST, status: verified }
```

`step-02` 는 `StepInspector.dc.html` 이 표시하는 상태와 대응한다:
`test_id` → `사용 중`, `role`+이름 → `대체 1`, `label` → `수집되지 않음`, `text` → `대체 2`,
`stable_attr` → `수집되지 않음`, `css` → `최후`.

---

## 전체 예 — 멀티 탭 (FR-030)

새 탭에서 문서를 확인하고 닫은 뒤, 원래 탭의 상태를 검증하는 흐름.

```yaml
dsl_version: 1
id: TC-005
name: 약관 새 창 확인
authoring_mode: record
start_url: https://example.internal/signup
browser: chromium
variables: []
steps:
  - id: step-01
    type: click
    label: 약관 보기 클릭 (새 창 열림)
    author: human
    tab: 0                    # 최초 탭에서 클릭
    timeout_ms: 5000
    target:
      test_id: { value: terms-link, status: verified }
      role: link
      accessible_name: 약관 보기
      css: { value: "a.terms", status: verified }
    # 새 탭이 열리는 것 자체는 Step이 아니다 (FR-030b).
    # 이 클릭이 탭 1을 열게 하고, 다음 Step이 tab: 1 을 참조한다.

  - id: step-02
    type: assertion
    label: 새 창에 약관 제목이 보이는지 확인
    author: human
    tab: 1                    # 열린 순서로 부여된 탭 참조
    timeout_ms: 5000          # 탭 1이 열리기를 이 시간까지 기다린다 (FR-030d)
    assertion:
      kind: visible
      target:
        role: heading
        accessible_name: 서비스 이용약관
        text: { value: 서비스 이용약관, status: verified }

  - id: step-03
    type: close_tab
    label: 약관 창 닫기
    author: human
    tab: 1                    # 닫을 대상 탭 (FR-030c)
    timeout_ms: 5000

  - id: step-04
    type: assertion
    label: 원래 화면의 동의 체크박스가 보이는지 확인
    author: human
    tab: 0                    # 최초 탭으로 돌아온다
    timeout_ms: 5000
    assertion:
      kind: visible
      target:
        test_id: { value: agree-checkbox, status: verified }
```

**탭 참조는 열린 순서다.** 번호를 재사용하지 않는다 — 탭 1을 닫고 새 탭을 열면 그 탭은 2가 된다
(data-model §8 TabHandle 불변식). 재실행 시 이 순서가 달라지는 대상 앱에서는 해당 Step이 실패하며,
실패 메시지에 순서 불일치 가능성이 포함된다.

---

## `ai` 로 작성한 테스트

```yaml
dsl_version: 1
id: TC-002
name: 프로젝트 삭제
authoring_mode: ai
ai_instruction: |            # 작성 의도의 기록. 실행 대상이 아니다 (FR-063)
  로그인한 다음 프로젝트 메뉴로 이동해서
  TEST 프로젝트를 삭제해.
start_url: https://example.internal/login
browser: chromium
variables: []
steps:
  - id: step-01
    type: click
    label: 프로젝트 메뉴 클릭
    author: ai               # AI가 만들었다는 표시일 뿐, 실행 방식은 동일 (FR-014)
    tab: 0
    timeout_ms: 5000
    target:
      role: menuitem
      accessible_name: 프로젝트
      css: { value: "nav a:nth-child(2)", status: verified }

  - id: step-02
    type: click
    label: 삭제 클릭
    author: human            # 사람이 이어받아 만든 Step (FR-075)
    tab: 0
    timeout_ms: 5000
    target:
      text: { value: 삭제, status: verified }
      css:  { value: ".menu-popup button:last-child", status: verified }
```

**`ai_instruction` 은 문자열일 뿐이다.** 실행기는 이 필드를 읽지 않는다. 파일에 남아 있는 이유는 나중에
사람이 "이 테스트가 무엇을 의도했는지" 읽기 위한 것이다 — PRD §2 P2가 지적한 "Recorder 결과는 테스트
의도를 표현하지 못한다" 문제에 대한 답이기도 하다.

`step-01` 과 `step-02` 의 `author` 가 다르지만 구조가 완전히 같다는 점이 원칙 I의 사용자 향 증거다.

---

## 검증 규칙 (파일을 읽을 때 강제)

| 규칙 | 위반 시 |
|------|---------|
| `steps` 가 1개 이상 | 로드 거부 (FR-029) |
| `id` 가 `TC-\d{3}` 패턴 | 로드 거부 |
| 변수 이름이 `[A-Z][A-Z0-9_]*` | 로드 거부 |
| `sensitive: true` 인 변수의 `value` 가 null | **로드 거부** — 민감 값이 정의 파일에 있다는 뜻 (FR-082) |
| `target` 에 후보가 최소 1개 | 로드 거부 |
| `{{변수명}}` 참조가 `variables` 에 정의됨 | 로드 거부 |
| `timeout_ms` 가 1~60000 | 로드 거부 |
| `tab` 이 0 이상 정수 | 로드 거부 |
| `dsl_version` 이 지원 범위 | 명확한 안내와 함께 거부 |

로드 거부 시 **파일 경로와 문제 위치를 알려 사용자가 직접 고칠 수 있게 한다.** 사람이 읽고 편집할 수 있는
평문 형식을 택한 이유가 이것이다.

---

## Playwright Export 대비 (원칙 V, P2)

Export 자체는 이번 범위가 아니지만, DSL은 다음 대응이 성립하도록 설계했다.

| DSL | 생성될 Playwright 표현 |
|-----|------------------------|
| `type: click` + `target.test_id` | `await page.getByTestId('create-project').click()` |
| `type: fill` + `value: "{{V}}"` | `await page.getByLabel('...').fill(process.env.V)` |
| `type: assertion, kind: visible` | `await expect(...).toBeVisible()` |
| `type: assertion, kind: hidden` | `await expect(...).toBeHidden()` |
| `tab: 1` | `const [tab1] = await Promise.all([context.waitForEvent('page'), ...])` |
| `type: close_tab, tab: 1` | `await tab1.close()` |

후보 선택 규칙은 `choose_strategy` 순수 함수 하나에서 나오므로, Runner가 쓰는 판단과 생성되는 코드가
같은 후보를 고른다 (FR-022, research R4). **Export를 나중에 붙일 때 우선순위 로직을 다시 짜지 않는다.**
