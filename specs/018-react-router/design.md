# Design — 018 React Router 도입

**Date**: 2026-09-17 | **Branch**: `chore/react-router` | **Status**: 설계 확정 (사용자 승인)

화면 전환을 `App.tsx` 의 `screen` 상태에서 **React Router(Data 모드)** 로 옮긴다.
이 문서는 브레인스토밍에서 사용자가 승인한 설계를 옮겨 적은 것이다. 구현 계획은
[plan.md](./plan.md) 에 따로 둔다.

---

## 1. 왜 지금 라우터인가

005 research R8 은 **라우팅 라이브러리를 넣지 않기로** 했다. 그때 요구는 둘뿐이었다 —
결과 화면의 새로고침 복원(FR-166)과 뒤로가기 이탈 방지(FR-167). 그래서 `useScreenUrl` 이
`?screen=result&test=TC-001` 질의 문자열과 `pushState`/`popstate` 를 손으로 이었다.

이번에 사용자가 고른 목표는 넷이고, R8 이 풀지 않은 것들이다.

| 목표 | 지금 |
|------|------|
| 읽기 좋은 경로형 주소 | `?screen=definition&test=TC-001&step=step-02` |
| **모든 화면**의 새로고침·딥링크 | 실행·만들기·가져오기 미리보기는 새로고침하면 목록으로 떨어진다 |
| `App.tsx` 구조 정리 | 800줄 한 컴포넌트가 화면 10개의 분기와 콜백을 전부 쥔다 |
| 링크 기반 이동 | 모든 이동이 `onClick` — Cmd/가운데 클릭으로 새 탭을 열 수 없다 |

R8 의 근거(의존성 둘뿐 · 같은 시점의 다른 작업과 충돌)는 지금 성립하지 않는다 — 017 이
`@base-ui/react` 를 들였고, 이 라운드는 라우팅만 다룬다. **R8 은 이 문서로 뒤집힌다.**

### 결정: React Router v8 Data 모드

- 버전: `react-router@^8.4.0` (단일 패키지, ESM 전용). `RouterProvider` 는 `react-router/dom`
  에서, 나머지는 `react-router` 에서 가져온다.
- 호환: React 19.2.8(요구 ≥19.2.7) · TS target ES2022 · CI Node 22(요구 ≥22.22) — 전부 충족.

**버린 대안**

- **Declarative 모드** (`<BrowserRouter><Routes>`) — 라우트마다 로딩·오류·리다이렉트를 손으로
  만들어야 하고 `useBlocker`·loader 가 없다.
- **Framework 모드** (파일 라우트 + Vite 플러그인) — `index.html` 진입이 플러그인으로 넘어가
  현 vite/vitest 설정·순회 스크립트·실브라우저 하니스와 부딪친다. 로컬 단독 도구에 과하다.

---

## 2. 라우트 구조

```
root  (미들웨어: 프로젝트 조회 1회 → setExpectedProjectRoot · errorElement)
├─ /projects                 ProjectsRoute   ← 알림 층 밖 (지금과 같다)
└─ AppShell  (열린 프로젝트 필수 — 없으면 /projects 로)
   ├─ /                      ListRoute       (+ 옛 ?screen= 주소면 교체 이동)
   ├─ /tests/new             ComposeRoute    (loader: ?draft= → drafts.get)
   ├─ /tests/:testId/edit    EditRoute       (?step= → focusStepId)
   ├─ /tests/:testId/result  ResultRoute     (?step= → focusStepId)
   ├─ /sessions/:sessionId   SessionRoute    (loader: sessions.get)
   ├─ /import/:planId        ImportRoute
   ├─ /keys                  KeysRoute
   ├─ /secrets               SecretsRoute
   └─ *                      → / 로 교체 이동
```

화면 이름 대응 (옛 `Screen.name` → 경로):

| 옛 이름 | 경로 |
|---------|------|
| `setup` | `/projects` |
| `list` | `/` |
| `compose` | `/tests/new[?draft=]` |
| `definition` | `/tests/:testId/edit[?step=]` |
| `result` | `/tests/:testId/result[?step=]` |
| `runner` | `/sessions/:sessionId[?from=edit&step=]` |
| `import-preview` | `/import/:planId` |
| `keys` / `secrets` | `/keys` / `/secrets` |
| `loading` | 없음 — 미들웨어가 끝날 때까지 라우터가 첫 화면을 그리지 않는다 |

### 파일 배치

**새로 만든다 (`frontend/src/app/`)**

| 파일 | 하는 일 |
|------|---------|
| `router.tsx` | 라우트 표(`routes`). `createBrowserRouter` 에 넘기고, 테스트는 같은 표를 `createMemoryRouter` 에 넘긴다. |
| `AppShell.tsx` | 레이아웃 라우트. `Toaster` · 오류 토스트 · 가져오기 완료 알림 · `<Outlet />`. |
| `actions.tsx` | 세션을 여는 **유일한 경로**(`startRun`·`openBrowserAt`·`openRerecord`·`openSession`)와 `pendingRun`·만들기 잠금을 context 로 낸다. |
| `routes/*.tsx` | 라우트별 얇은 어댑터. URL 파라미터·loader 데이터를 **기존 페이지 prop 으로 옮기기만** 한다. |

**`paths.ts` 는 `src/lib/` 에 둔다** (구현 중 결정). 화면(`pages/*`)이 링크의 `href` 를 이것으로 얻는데,
화면이 `app/` 을 가져오면 `app → pages → app` 으로 층이 거꾸로 선다. `react-router` 도 가져오지 않는
순수 함수라 `lib/` 이 맞는 자리다.

**바뀐다**

- `main.tsx` — `<App />` 은 그대로 그린다.
- `App.tsx` — 800줄 본문을 지우고 **마운트 시점에** 브라우저 라우터를 만들어 `RouterProvider` 로
  그린다(`useState(() => createBrowserRouter(routes))`). import 시점에 만들면, 주소를
  `replaceState` 로 바꾼 **뒤에** `<App />` 을 그리는 기존 테스트가 옛 주소를 읽는다.
- `hooks/useScreenUrl.ts` — 삭제. 옛 주소 호환은 `paths.ts` 가 물려받는다.
- `pages/*` — prop 구조를 거의 유지한다. 순수 이동만 링크로 바꾼다(§4).

**범위 밖**: `TestList`(1754줄)·`SessionScreen`(3310줄) 같은 큰 페이지의 내부 구조 정리.

---

## 3. 상태와 데이터 흐름

### 3.1 여러 화면이 함께 쓰는 상태 — `AppShell`

지금 `App` 이 쥔 것 중 **화면을 넘어 살아야 하는 것**만 셸에 둔다.

| 상태 | 자리 | 비고 |
|------|------|------|
| 열린 프로젝트(`opened`) | 셸 | 미들웨어가 처음 채우고, `/projects` 에서 열면 셸이 갈아 끼운다 |
| 오류(`ErrorInfo`) | 셸 | `next_action`·`sessionId` 를 잃지 않도록 객체 그대로 (003 EC-004) |
| `pendingRun` | 셸(`actions.tsx`) | in-flight 가드는 한 곳에만 (005 U-06) |
| 만들기 잠금 | 셸(`actions.tsx`) | ref + 상태 한 쌍 그대로 — 같은 틱 두 번째 클릭을 ref 가 막는다 |
| 가져오기 완료 결과 | 셸 | 미리보기에서 만들어지고 목록에서 한 번 보인다 (014 FR-018a) |
| 가져오기 계획 | 셸 메모리 (`planId` → 계획) | §3.4 |
| 살아 있는 세션 목록 · 5초 주기 조회 | **`ListRoute`** | 목록에서만 쓴다 (005 FR-169) |

### 3.2 프로젝트 조회 순서 — 루트 미들웨어

Data 모드는 부모와 자식의 loader 를 **동시에** 돌린다. 그대로 두면 `/sessions/:id` 의 조회가
`setExpectedProjectRoot` 보다 먼저 나갈 수 있다 — `App.tsx` 가 "효과로 미루지 않는다"는
주석으로 막아 둔 뒤바뀜(2026-09-10 사용자 보고 1번)과 같은 것이다.

- 루트 **미들웨어**가 `project.current()` 를 끝내고 `setExpectedProjectRoot` 를 세운 **뒤에**
  자식 loader 가 돈다. v8 은 미들웨어가 항상 켜져 있다.
- 조회는 **처음 한 번만** 한다. 이후 기준은 셸 상태다.
- 프로젝트가 없으면 `/projects` 외의 모든 경로가 `/projects` 로 리다이렉트된다.
- `/projects` 에서 프로젝트를 열면 `setExpectedProjectRoot` → 셸 상태 갱신 → `/` 로 이동.
  「돌아가기」는 열린 프로젝트가 있을 때만 준다(지금과 같다).

### 3.3 실행 화면(`/sessions/:sessionId`)이 받던 것

지금 `runner` 화면은 세션 객체와 부가 정보 다섯을 들고 다닌다. **성격에 따라 자리를 나눈다.**

| 값 | 자리 | 이유 |
|----|------|------|
| 세션 객체 | loader (`sessions.get`) | URL 만으로 되살아나야 한다 |
| `draft` | 세션 응답의 `draft` | 서버가 이미 싣는다 (014 수렴 2회차) |
| `returnToEdit` | 쿼리 `?from=edit&step=step-03` | 새로고침해도 끝나면 편집으로 돌아가야 한다. `testId` 는 `session.test_id` |
| `aiInstruction` (기록) | `location.state` | 같은 탭 새로고침에는 남는다. 새 탭 딥링크에서는 없어도 막히지 않는다 |
| `recordOnArrival` · `instructionOnArrival` (**일회성 명령**) | `location.state` → 라우트가 **첫 렌더에 꺼내 보관**하고 곧바로 history.state 에서 지운다(`replace`) | `history.state` 는 새로고침에도 남는다. 지우지 않으면 새로고침이 AI 지시문을 다시 수행한다 |

일회성 명령은 **SessionScreen 이 소비할 때가 아니라 라우트가 처음 그릴 때** 꺼낸다
(`useState` 초기화). 소비는 세션이 도착점에 멈춘 뒤라서, 그 전에 history 를 지우면 prop 이
먼저 사라진다. 꺼낸 값은 컴포넌트 수명 동안 상태에 남는다.

`autoShowResult` 는 지금처럼 `returnToEdit` 의 유무로 정한다 — 이제 `?from=edit` 의 유무다.

### 3.4 만들기 · 가져오기 미리보기

- **만들기 `/tests/new?draft=`** — loader 가 초안을 읽는다. loader 가 끝날 때까지 목록이
  그대로 보이므로 "초안 읽기에 실패하면 화면을 바꾸지 않는다"(014 US3)가 유지된다.
  들어올 때마다 만들기 잠금을 푼다(지금 `onCreate`·`onRecordDraft` 가 하는 것).
- **가져오기 미리보기 `/import/:planId`** — 계획 객체를 **셸 메모리**에 둔다. `location.state`
  에 두면 새로고침에도 남아 만료된 계획을 그린다. 메모리에 없으면 「미리보기가 사라졌습니다 —
  파일을 다시 고르세요」를 알리고 `/` 로 교체 이동한다. **백엔드는 바꾸지 않는다** (계획은
  서버 메모리에만 있고 만료되며, 조회 API 가 없다 — 사용자 결정).

### 3.5 세션을 여는 경로 — `actions.tsx`

동작은 지금 `App.tsx` 의 네 함수와 같다. 마지막 걸음만 `setScreen(...)` 에서
`navigate(paths.session(id, …), { state })` 로 바뀐다.

- `startRun(testId, fromStepIndex?)` — `pendingRun` 가드 → `sessions.create(replay)` →
  (`runFrom`) → `/sessions/:id`
- `openBrowserAt(testId, stepIndex, stepId, instruction)` — 같은 가드 →
  `/sessions/:id?from=edit&step=` + state `{ aiInstruction, recordOnArrival, instructionOnArrival }`
- `openRerecord(testId, stepIds)` — 같은 가드 → `/sessions/:id?from=edit&step=<첫 Step>`
- `openSession(sessionId)` — `/sessions/:id`. 실패 처리는 loader/errorElement 가 한다(§5).

만들기의 `onRecord`·`onStartAi` 도 `actions.tsx` 의 만들기 잠금을 지난다.

---

## 4. 링크 기반 이동

- **`ui/ButtonLink.tsx`** 를 새로 둔다. `<Link>` 에 기존 `buttonVariants` 클래스를 입힌 부품이다.
  모습은 버튼 그대로, 요소는 `<a href>` — Cmd/가운데 클릭으로 새 탭이 열린다.
- **링크로 바꾸는 것: 부수효과가 없는 순수 이동만.** 후보 —
  - 목록 머리띠의 「프로젝트」「비밀 값」「키 관리」
  - 목록 행의 「결과 보기」「편집」
  - 비밀 값의 「키 관리」「닫기」, 키 관리의 「닫기」
  - 목록의 「테스트 만들기」, 초안의 「녹화」 — 초안 조회는 이제 `/tests/new` 의 loader 가 한다(§3.4)
- **버튼으로 남는 것**
  - 부수효과가 있는 조작 — 실행 · 녹화 시작 · 세션 열기
  - 이동 전에 확인을 거치는 것 — 편집 화면의 `guard(...)`(저장 안 한 변경)를 지나는 이동
- 후보는 구현 중 조작 하나하나를 확인해 확정한다. 행 메뉴(`MenuItem`)를 링크로 그릴 수 있는지는
  그때 Base UI API 로 확인하고, 안 되면 메뉴 항목은 버튼으로 남긴다.
- `RawElements` 가드는 `button·input·select·textarea` 만 보므로 `<a>` 는 막히지 않는다.
  다만 화면 파일에 원시 `<a>`/`<Link>` 를 직접 쓰지 않고 `ButtonLink` 를 지난다(017 부품 층 규율).
- `<a>` 와 `<button>` 은 계산 스타일이 다르다. L2(`design_compare_ba.py`)에서 나는 차이는
  **의도된 차이로 사유와 함께 등록**한다.

---

## 5. 오류 처리

| 상황 | 처리 |
|------|------|
| 렌더 중 예외 | **루트 `errorElement`** — 「화면을 그리지 못했습니다」와 「목록으로」 링크. 지금은 흰 화면이다. |
| `/sessions/:id` 가 404 (이미 끝난 세션) | 라우트 `errorElement` → 오류 없이 `/` 로 교체 이동 (지금 `openSession` 의 실패와 같다) |
| `/sessions/:id` 가 그 밖의 실패 | 라우트 `errorElement` → `/` 로 교체 이동. 지금과 같이 오류는 띄우지 않는다 |
| `/tests/new?draft=` 조회 실패 | 라우트 `errorElement` → 셸 오류 토스트 + `/` 로 교체 이동 |
| `/import/:planId` 인데 메모리에 계획 없음 | 안내 + `/` 로 교체 이동 (§3.4) |
| 프로젝트 없음 | `/projects` 로 리다이렉트 |
| 없는 경로 (`*`) | `/` 로 교체 이동 (지금 "알 수 없는 값은 목록" 과 같다) |
| 세션 생성 실패 (`startRun` 등) | 지금과 같이 셸 오류 토스트. `sessionId` 가 있으면 「실행 중인 세션 보기」 |

라우트 `errorElement` 는 셸의 `<Outlet />` 자리에 그려지므로 셸 context(오류 토스트)를 쓸 수 있다.

**범위 밖**: 편집 화면에서 저장 안 한 변경이 있을 때 **브라우저 뒤로가기**는 지금도 확인 없이
떠난다. 기존 동작이므로 그대로 둔다. 필요하면 후속으로 `useBlocker` 를 쓴다.

---

## 6. 옛 주소 호환

`useScreenUrl.ts` 의 규율 — **열어 둔 탭과 북마크를 끊지 않는다** — 을 이어받는다.
인덱스 라우트 loader 가 `?screen=` 를 보면 새 경로로 **교체 이동**한다(뒤로가기 기록에 남지 않는다).

| 옛 주소 | 새 주소 |
|---------|---------|
| `?screen=result&test=X[&step=Y]` | `/tests/X/result[?step=Y]` |
| `?screen=definition&test=X[&step=Y]` | `/tests/X/edit[?step=Y]` |
| `?screen=keys` | `/keys` |
| `?screen=secrets` | `/secrets` |
| `?screen=compose` · `create` · `ai-compose` | `/tests/new` |
| `?screen=runner&session=S` | `/sessions/S` |
| 그 밖의 값 · 필수 파라미터가 빠진 주소 | `/` |

---

## 7. 검증

### 7.1 새 테스트 (vitest)

- **`paths.test.ts`** — 경로 빌더, §6 변환 표 전부. `ScreenUrl.test.ts` 의 변환 테스트를 흡수한다.
- **`Routing.test.tsx`** (`createMemoryRouter` 로 원하는 주소에서 시작)
  - 주소마다 맞는 화면이 뜬다 — §2 의 경로 전부, `?step=` 지목 포함
  - `/sessions/:id` 딥링크로 실행 화면이 뜬다. `?from=edit` 가 있으면 끝났을 때 편집으로 간다
  - **일회성 명령이 되살아나지 않는다** — 첫 렌더 뒤 history.state 에 명령이 없다
  - `/import/:planId` 를 메모리 없이 열면 안내가 뜨고 `/` 로 간다
  - 프로젝트가 없으면 `/projects`, 없는 경로는 `/`
  - **프로젝트 조회가 자식 loader 보다 먼저 끝난다** — 요청 순서를 기록해 확인
  - 실행 연타에도 세션 생성 요청은 1건
- 순수 이동 조작이 `href` 를 가진 `<a>` 다.

### 7.2 고치는 기존 검증

| 대상 | 변경 |
|------|------|
| `EditEntryPoints` · `PhaseContext` · `RecheckPhase12` | `?screen=` 주소를 새 경로로. 옛 주소 복원도 한 건씩 남긴다 |
| `ScreenUrl.test.ts` | `useScreenUrl` 삭제에 맞춰 지우고 `paths.test.ts` 로 흡수 |
| `backend/tests/abnormal/test_ui_surface_restore.py` | 새 경로 기준 새로고침·뒤로가기 + 옛 주소 교체 이동 1건 |
| `scripts/screen_sweep.py` | `query` 를 새 경로로, `evidence` 의 `screen=secrets`·`screen=keys` 를 `/secrets`·`/keys` 로 |
| L2 대조 | 버튼 → 링크 요소를 의도된 차이로 등록 |

### 7.3 완료 판정 — 실제로 돌려서 본다

- `cd frontend && npx tsc --noEmit && npx vitest run`
- `cd backend && uv run pytest -m "browser and not timing"` — 실브라우저(새로고침 복원 포함)
- `scripts/screen_sweep.py` — 18화면 × 4폭에서 새로 생긴 깨짐 0
- 개발 서버로 직접: 딥링크 붙여넣기 · 새로고침 · 뒤로/앞으로 · Cmd+클릭 새 탭

### 7.4 서버 쪽

바꿀 것이 없다. UI 는 vite 개발 서버가 내보내고(히스토리 폴백 기본 제공),
`design_compare_ba.py` 의 정적 서버는 이미 없는 경로를 `index.html` 로 돌린다.

---

## 8. 문서

- `specs/005-ux-walkthrough-repair/research.md` R8 에 「018 에서 뒤집힘 — `specs/018-react-router/design.md`」 표시
- `README.md` 「현재 상태」에 018 단락
