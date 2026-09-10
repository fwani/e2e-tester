# Quickstart: Tailwind CSS 전환 검증

**Feature**: 015 | **Date**: 2026-09-10 | **Phase**: 1

전환이 끝났는지, 그리고 **끝났다는 말이 사실인지**를 확인하는 절차다.
§1~§3 은 기계가 판정하고, §4 는 사람이 판정한다.

---

## 0. 사전 준비

```bash
cd frontend && npm install
```

전환 전 상태를 기준선으로 떠 둔다 (§3 에서 쓴다). **전환 시작 전에 해야 한다.**

```bash
# 전환 전 커밋에서 기준선을 뜬다
backend/.venv/bin/python scripts/design_compare_ba.py --baseline
```

---

## 1. 기계 판정 — 전환이 실제로 됐는가

### 1-1. 기존 테스트 전량 통과 (SC-003)

```bash
cd frontend && npm test -- --run
```

**기대**: 전량 통과. 건너뛴 테스트 0건.

**주의**: 통과했다고 끝이 아니다. 아래로 단언이 줄지 않았는지 확인한다.

```bash
# 전환 전후 단언 수 비교 (헌법 Quality Gate 4)
grep -rc 'expect(' frontend/tests --include='*.test.ts*' | awk -F: '{s+=$2} END {print "단언 총수:", s}'
```

전환 전 수치와 비교해 **줄었으면 그 자리를 지목하고 이유를 대야 한다.**
줄어든 채로 통과시키는 것이 이 기능에서 가장 쉽고 가장 나쁜 실패다.

### 1-2. 인라인 스타일 잔량 (SC-002)

```bash
grep -rc 'style={{' frontend/src --include='*.tsx' | grep -v ':0$'
```

**기대**: 남은 것이 전부 `theme/exceptions.ts` 에 등록되어 있고, 각 `reason` 이
런타임 계산값임을 말한다. 등록되지 않은 잔량 0건.

### 1-3. 값 리터럴 (SC-004, 가드 G-A)

```bash
cd frontend && npm test -- --run VisualLanguage    # 판정
node frontend/scripts/count-violations.mjs         # 고칠 곳 보기 (원시 계수)
```

**기대**: 테스트 통과.

> **두 수치가 다를 수 있다.** 계수기는 예외 등록부를 보지 않는 **원시 계수**이고,
> 판정은 테스트가 한다 — 규칙으로 세고 `theme/exceptions.ts` 로 거른 뒤 단언한다.
> 계수기 합계가 0 이 아니어도 그것이 곧 위반은 아니다. 등록된 정당한 이탈이 몇 개인지
> 보려면 계수기를, 「위반이 있는가」를 물으려면 테스트를 쓴다.

가드가 살아 있는지 확인한다 — 일부러 어긴 뒤 되돌린다.

```bash
# .tsx 하나에 색 리터럴을 넣고
node frontend/scripts/count-violations.mjs   # 1 이 나와야 한다
git checkout -- <그 파일>
```

### 1-4. 클래스 실재 (가드 G-B)

```bash
cd frontend && npm test -- --run ClassExistence
```

**기대**: 코드가 쓰는 모든 Tailwind 클래스가 빌드 산출 CSS 에 존재한다.

이 가드가 실제로 잡는지 확인한다 — 오타를 하나 넣어 본다.

```bash
# 어느 컴포넌트의 클래스명에 오타를 내고 (예: basis-[460px] → bass-[460px])
cd frontend && npm test -- --run ClassExistence   # 실패해야 한다
git checkout -- <그 파일>
```

**이 확인을 건너뛰지 않는다.** G-B 가 동작하지 않으면 화면이 조용히 무스타일로 렌더되는
실패를 아무도 잡지 못한다.

### 1-5. 체계 혼용 (가드 G-C)

```bash
cd frontend && npm test -- --run SingleSystem
```

**기대**: 한 요소에 의미 클래스와 유틸리티가 동시에 걸린 곳 0건.
전환 중에는 이 수치가 **진행률 계기**다.

### 1-6. 행선지 대응 (SC-009, 가드 G-D)

```bash
cd frontend && npm test -- --run ClassMigration
```

**기대**: `tokens.css` 에 남은 의미 클래스 수 == 대응표의 「완료」 아닌 행 수.
전환 완료 시 양쪽 모두 0.

### 1-7. 컴파일 시점 강제가 살아 있는가 (SC-011)

`Phase` 에 국면을 하나 임시로 추가하고 타입 검사를 돌린다.

```bash
cd frontend && npm run typecheck   # 실패해야 한다 — 배치 표가 새 국면을 요구한다
```

**기대**: `lib/layout.ts` 의 `Record<Phase, …>` 가 컴파일 오류를 낸다.
통과하면 FR-020a 가 깨진 것이다. 확인 후 되돌린다.

### 1-8. 배포 산출물 크기 (SC-007)

```bash
cd frontend && npm run build && du -sh dist/assets/*.css
```

**기대**: 전환 전 대비 늘지 않는다.

---

## 2. 정본이 하나인가 (SC-005)

### 2-1. 정본 파일 무변경 (계약 C-2)

```bash
git diff <전환 시작 커밋> -- frontend/src/theme/tokens.css
```

**기대**: 차이 없음. 정본은 이 기능에서 손대지 않는다.

### 2-2. Tailwind 테마에 값이 없음 (계약 C-1·C-8, 가드 G-A1·G-A5)

```bash
cd frontend && npm test -- --run TailwindThemeLiteral
```

**기대**: 통과. 네 가지를 본다 — `@theme` 선언을 실제로 읽었는가, 오른쪽이 전부
`var(정본토큰)` 인가, 정본을 `layer(base)` 로 들였는가, 참조하는 토큰이 실재하는가.

> **왜 `grep` 이 아닌가**: 1회차 절차는 `grep -nE '…(?!var\()'` 였다. 그것은 PCRE
> lookahead 라 **macOS 기본 grep 에서 동작하지 않는다** — 오류 없이 0건을 내고, 절차는
> 통과한 것처럼 보인다. 검사할 수 없는 절차는 지켜지지 않는 규칙과 같다.

### 2-3. L1 대조가 여전히 통과 (기존 장치)

```bash
backend/.venv/bin/python scripts/design_render.py --compare
cd frontend && npm test -- --run CanonMatchesDesign
```

**기대**: 통과. Tailwind 도입이 정본↔디자인 관계를 건드리지 않았다.

---

## 3. 시각 동일성 — 기계가 볼 수 있는 만큼 (SC-001)

```bash
backend/.venv/bin/python scripts/design_compare_ba.py --compare
```

전환 전 기준선(§0)과 현재 화면을 chromium 으로 렌더해 `getComputedStyle` 을 대조한다.

**기대**: 불일치 0건. 불일치가 있으면 각 항목이 **의도된 것인지** 판단해야 하며,
의도되지 않은 것이 하나라도 있으면 전환이 끝난 것이 아니다.

**이 검사의 한계**: 계산된 스타일 값만 본다. 겹침 순서, 스크롤 위치, 애니메이션,
실제 픽셀은 보지 못한다. 그래서 §4 가 필요하다.

---

## 4. 사람 판정 — 기계가 볼 수 없는 것

`docs/PENDING-HUMAN-VERIFICATION.md` §15 에 등록하고, 아래를 직접 조작해 판정한다.
각 항목은 **전환 전 화면을 나란히 놓고** 본다.

| # | 화면 · 흐름 | 무엇을 보나 |
|---|---|---|
| H-1 | 작업대 — 국면 전체(대기·녹화·일시정지·편집·결과) | 두 자리의 세로 배분이 국면마다 전과 같은가. **S-12 재발 여부가 여기서 보인다** |
| H-2 | Step 목록 | 행 높이 52px 유지. 상태별(통과·실패·경고·일시정지·지목) 구별이 전과 같은가 |
| H-3 | 토스트 알림 | 오른쪽 위 고정. 여러 줄 알림이 잘리지 않는가. 종류별 색 구별 |
| H-4 | Step 상세 층 | 목록을 덮지 않는 자리. 폭 640px |
| H-5 | 프로젝트 설정 · 가져오기 미리보기 | 인라인이 가장 많던 화면(55·41곳). 격자 정렬 |
| H-6 | 키 관리 · 비밀값 | 마스킹 표현이 유지되는가 (헌법 보안 요건) |
| H-7 | **키보드만으로 전체 순회** | 초점 표시가 사라진 요소 0건 (SC-008). 순서가 전과 같은가 |
| H-8 | 한글 입력(IME) | 조합 중 입력이 깨지지 않는가 |

**H-1 과 H-7 이 가장 중요하다.** H-1 은 이 전환이 되살릴 수 있는 가장 큰 결함을 보고,
H-7 은 기계 검사가 원리적으로 덮지 못하는 접근성 회귀를 본다.

---

## 완료 판정

위 §1~§4 가 전부 통과했을 때만 완료다. 하나라도 미판정이면 미완료로 보고한다.

| 절 | 판정자 | 미통과 시 |
|---|---|---|
| §1 기계 판정 | 자동 | 완료 아님 |
| §2 정본 단일성 | 자동 | 완료 아님 |
| §3 시각 대조 | 자동 + 사람 해석 | 의도되지 않은 불일치가 있으면 완료 아님 |
| §4 사람 판정 | 사람 | 미판정이면 **미완료로 보고한다.** 통과로 가정하지 않는다 |
