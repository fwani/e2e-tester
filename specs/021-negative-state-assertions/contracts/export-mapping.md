# Contract: DSL ↔ 표준 Playwright 대응

**Feature**: 021 | **헌법 원칙 V** (Asset Portability)

내보낸 테스트는 제품 안에서 실행한 것과 **같은 검증**을 해야 한다. 생성기가 이미
구현되어 있으므로([research.md R5](../research.md)), 새 종류를 반영하지 않으면 그 정의는
내보내는 순간 실패한다 — 선택이 아니라 필수다.

---

## 1. 이번에 더해지는 대응

| 검증 조건 | 생성되는 표현 |
|---|---|
| `text` + `not_equals` (대상 있음) | `await expect(loc).not.toHaveText(값, { timeout })` |
| `text` + `not_contains` (대상 있음) | `await expect(loc).not.toContainText(값, { timeout })` |
| `text` + `not_equals` (화면 전체) | `await expect(root.locator('body')).not.toHaveText(…)` |
| `text` + `not_contains` (화면 전체) | `await expect(root.locator('body')).not.toContainText(…)` |
| `url` + `not_equals` | `await expect(page).not.toHaveURL(값, { timeout })` |
| `url` + `not_contains` | `expect(page.url()).not.toContain(값)` |
| `enabled` | `await expect(loc).toBeEnabled({ timeout })` |
| `disabled` | `await expect(loc).toBeDisabled({ timeout })` |

**부정형이 `.not` 수식어에 그대로 대응한다.** 비교 방식 축에 부정을 넣은 결정이 대상
라이브러리의 구조와도 일치한다는 뜻이다 — 종류 축에 넣었다면 생성기에서 종류별 분기를
다시 부정형으로 갈라야 했다.

---

## 2. 의미론이 같은지 — 확인한 것

| 항목 | 제품 내 실행 | 내보낸 테스트 | 같은가 |
|---|---|---|---|
| 조건이 참이 될 때까지 대기 | 공통 도우미가 제한 시간까지 폴링 | `expect` 가 제한 시간까지 재시도 | **같다** |
| 참이 되면 즉시 통과 | 그렇다 | 그렇다 | **같다** |
| `url` + `contains` 를 정규식으로 만들지 않음 | 문자열 포함 비교 | `toContain` (문자열) | **같다** — 기존 판단을 부정형에도 그대로 적용한다. 화면에서 온 값이 패턴으로 해석되면 뜻이 달라진다 |
| 상태 검증에서 대상 부재 | 실패 | `expect` 가 요소를 찾지 못해 실패 | **같다** |
| 비폼 요소의 조작 가능 판정 | 브라우저가 주는 값 그대로 | 같은 브라우저 API | **같다** (같은 한계를 공유한다) |

---

## 3. 회귀를 막는 방법

생성기에는 검증 조합별 내보내기 회귀 테스트가 이미 있다. **이번에 더하는 8개 조합을 그
목록에 넣는다.** 생성기 분기는 알 수 없는 종류를 만나면 예외를 던지므로, 목록에 없는
조합은 조용히 잘못 생성되는 것이 아니라 명확히 실패한다 — 그 성질을 유지한다.
