# Contract: DSL ↔ 표준 Playwright 대응

**Feature**: 021 | **헌법 원칙 V** (Asset Portability)

내보낸 테스트는 제품 안에서 실행한 것과 **같은 검증**을 해야 한다. 생성기가 이미
구현되어 있으므로([research.md R5](../research.md)), 새 종류를 반영하지 않으면 그 정의는
내보내는 순간 실패한다 — 선택이 아니라 필수다.

---

## 1. 상태 검증 — 그대로 대응한다

| 검증 조건 | 생성되는 표현 |
|---|---|
| `enabled` | `await expect(loc).toBeEnabled({ timeout })` |
| `disabled` | `await expect(loc).toBeDisabled({ timeout })` |

둘 다 「참이 될 때까지 기다린다」이고 Playwright 의 재시도 의미론과 같다.

## 2. 부정 검증 — **`.not` 하나로는 맞지 않는다** *(구현 중 정정)*

`.not` 수식어는 있다. 문제는 **의미론이 다르다**는 것이다.

| | 제품 내 실행 | `await expect(loc).not.toContainText(x)` |
|---|---|---|
| 뜻 | 기간 동안 유지되는지 지켜본다 | 조건이 참이 **되면** 통과 |
| 0.8초 뒤 오류가 뜨는 화면 | **실패** (잡는다) | **통과** (놓친다) |

`.not` 만 쓰면 내보낸 테스트가 제품 안에서 잡은 결함을 놓친다. 원칙 V 가 요구하는
「같은 검증」이 성립하지 않는다 — **표현의 차이가 아니라 결과의 차이다.**

### 생성하는 형태 — 명시적 관찰 루프

```js
// 「오류」가 1200ms 동안 화면에 나타나지 않아야 한다
{
  const deadline = Date.now() + 1200;
  for (;;) {
    await expect(page.locator('body')).not.toContainText('오류', { timeout: 1 });
    if (Date.now() >= deadline) break;
    await page.waitForTimeout(50);
  }
}
```

장황하지만 **표준 Playwright 다** — 별도 런타임도, 제품 API 도 쓰지 않는다. 조건이
깨지는 순간 `expect` 가 던지므로 제품 내 실행과 같은 시점에 같은 이유로 실패한다.

`timeout: 1` 은 「재시도하지 말고 지금 판정하라」는 뜻이다. 재시도를 켜 두면 안쪽에서
또 기다려 바깥 루프의 기간과 겹친다.

| 검증 조건 | 루프 안의 판정 |
|---|---|
| `text` + `not_equals` (대상 있음) | `await expect(loc).not.toHaveText(값, { timeout: 1 })` |
| `text` + `not_contains` (대상 있음) | `await expect(loc).not.toContainText(값, { timeout: 1 })` |
| `text` + `not_equals` (화면 전체) | `await expect(root.locator('body')).not.toHaveText(…)` |
| `text` + `not_contains` (화면 전체) | `await expect(root.locator('body')).not.toContainText(…)` |
| `url` + `not_equals` | `expect(page.url()).not.toBe(값)` |
| `url` + `not_contains` | `expect(page.url()).not.toContain(값)` |

주소 검증은 원래도 동기 판정(`page.url()`)을 쓰므로 루프 안에 그대로 들어간다.


## 3. 의미론이 같은지 — 확인한 것

| 항목 | 제품 내 실행 | 내보낸 테스트 | 같은가 |
|---|---|---|---|
| 긍정 조건이 참이 될 때까지 대기 | 제한 시간까지 폴링 | `expect` 가 제한 시간까지 재시도 | **같다** |
| 긍정 조건이 참이 되면 즉시 통과 | 그렇다 | 그렇다 | **같다** |
| 부정 조건을 기간 동안 지켜봄 | 50ms 간격 폴링 | 같은 간격의 명시적 루프 | **같다** (§2 의 형태로) |
| 부정 조건이 깨지면 즉시 실패 | 그렇다 | `expect` 가 그 자리에서 던진다 | **같다** |
| `url` + `contains` 를 정규식으로 만들지 않음 | 문자열 포함 비교 | `toContain` (문자열) | **같다** — 기존 판단을 부정형에도 그대로 적용한다. 화면에서 온 값이 패턴으로 해석되면 뜻이 달라진다 |
| 상태 검증에서 대상 부재 | 실패 | `expect` 가 요소를 찾지 못해 실패 | **같다** |
| 비폼 요소의 조작 가능 판정 | 브라우저가 주는 값 그대로 | 같은 브라우저 API | **같다** (같은 한계를 공유한다) |

---


## 4. 회귀를 막는 방법

생성기에는 검증 조합별 내보내기 회귀 테스트가 이미 있다. **이번에 더하는 8개 조합을 그
목록에 넣는다.** 생성기 분기는 알 수 없는 종류를 만나면 예외를 던지므로, 목록에 없는
조합은 조용히 잘못 생성되는 것이 아니라 명확히 실패한다 — 그 성질을 유지한다.
