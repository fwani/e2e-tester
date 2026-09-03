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

## 새 탭 경로 2종 (FR-030)

- `target="_blank"` 링크 (`약관 보기`)
- `window.open(...)` 팝업 (`약관 팝업으로 보기`)

`context.on("page")` 가 두 경로 모두에서 발생하는지 확인하는 데 쓴다 (research R1 검증 항목).
