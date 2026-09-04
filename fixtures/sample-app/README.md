# 픽스처 앱 (검증용 대상 웹 앱)

Interactive AI Test Builder 의 녹화·실행·후보 수집을 검증하기 위한 최소 웹 앱.
표준 라이브러리만 쓰므로 npm 설치가 필요 없다.

```bash
python fixtures/sample-app/serve.py --port 4300
# http://127.0.0.1:4300/login.html
```

## 화면

| 경로 | 용도 |
|------|------|
| `login.html` | 로그인. 비밀번호 유형 필드로 민감값 처리 검증 |
| `projects.html` | 프로젝트 목록·생성 모달·⋮ 메뉴 삭제·새 탭 링크 2종 |
| `terms.html` | 새 탭으로 열리는 약관 화면 |
| `data.html` | 파일 입력(네이티브 대화상자 한계 검증) |
| `analysis.html` | 화면 이동 검증용 |
| `interactions.html` | **hover 전용 메뉴와 끌어다 놓기** (FR-023c 검증용) |
| `noisy.html` | 아주 긴 텍스트와 제어문자를 담은 요소 (003 AS-015) |
| `nameless.html` | 접근 가능한 이름이 전혀 없는 요소만 (003 AS-016) |

## 이상 경로 (003 T011)

대상 사이트가 느리거나, 응답을 끝내지 않거나, HTML 이 아닌 본문을 오류와 함께 돌려주는
상황은 **바깥에서 벌어지는 일**이다. 제품에 실패 주입 스위치를 넣어 흉내 내지 않고
(헌법 원칙 II), 바깥이 실제로 그렇게 굴게 만든다.

| 경로 | 무엇이 일어나는가 | 시나리오 |
|------|------------------|---------|
| `/slow?ms=2000` | 그만큼 늦게 정상 화면을 준다 (상한 30초) | AS-031 |
| `/hang` | 헤더만 보내고 본문을 끝내지 않는다 (상한 60초) | AS-041 |
| `/boom?status=503` | HTML 이 아닌 이진 본문을 오류 상태와 함께 준다 | AS-017 |

`/hang` 이 한 연결을 붙잡고 있는 동안에도 다른 요청이 답을 받아야 하므로 서버는 요청을
스레드로 받는다.

## 후보 수집률 측정 설계 (SC-008)

`data-testid` 가 **있는 요소와 없는 요소를 의도적으로 섞었다.**

| 요소 | `data-testid` | 확보 가능한 다른 후보 |
|------|---------------|----------------------|
| 이메일 입력 | `login-email` | label, css |
| **비밀번호 입력** | **없음** | label(비밀번호), css |
| 로그인 버튼 | `login-submit` | role+name, text, css |
| 프로젝트 생성 버튼 | `create-project` | role+name, text, css |
| **프로젝트명 입력** | **없음** | label(프로젝트명), css |
| 유형 셀렉트 | `project-type` | label, css |
| 저장 버튼 | `save-project` | role+name, text, css |
| **⋮ 메뉴 버튼** | **없음** | role+aria-label, css |
| **삭제 메뉴 항목** | **없음** | text(삭제), css |
| 약관 링크 | `terms-link` | role+name, text, css |

testId 가 없는 요소도 label·role+name·text 중 하나 이상이 잡히도록 만들었다.
`data-testid` 없는 요소가 전체의 약 40% 이므로 SC-008(후보 2개 이상 90%)이
자동으로 통과하지 않는다 — 실제 수집 품질을 측정할 수 있다.

## hover·drag 검증 설계 (FR-023c)

`interactions.html` 은 **클릭만으로는 도달할 수 없는 요소**를 의도적으로 둔다.

- `도구` 버튼의 하위 메뉴는 CSS `:hover` 로만 열린다. hover Step 이 없으면 `내보내기` 를
  누를 수 없어 재실행이 실패한다 — hover 기록이 실제로 필요한지 이 화면이 판정한다.
- `events` 칩을 `보관함` 으로 끌어다 놓으면 DOM 이 옮겨진다. 끌기 시작(`dragstart`)과
  놓기(`drop`)가 모두 발생하므로 리코더가 두 요소를 함께 잡을 수 있다.

## 새 탭 경로 2종 (FR-030)

- `target="_blank"` 링크 (`약관 보기`)
- `window.open(...)` 팝업 (`약관 팝업으로 보기`)

`context.on("page")` 가 두 경로 모두에서 발생하는지 확인하는 데 쓴다 (research R1 검증 항목).
