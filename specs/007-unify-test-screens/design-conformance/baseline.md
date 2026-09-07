# 이행 전 기준선 (T005)

**측정 시각**: 2026-09-08 · 브랜치 `007-unify-test-screens` · 커밋 `8ad079d`

이행 중 **무엇이 새로 깨졌는지** 가릴 근거다. 「전부 통과했다」만 적힌 기록은 다음 사람이
무엇을 걸었는지 알 수 없게 한다.

## 1. 타입 검사

```
cd frontend && npm run typecheck
```

**통과.** `tsc --noEmit` 출력 없음 (`noUncheckedIndexedAccess` 아래).

## 2. 테스트

```
cd frontend && npx vitest run
```

| 항목 | 값 |
|---|---|
| 테스트 파일 | **35 통과 / 35** |
| 테스트 | **353 통과 / 353** |
| 미처리 오류 | **2** → T004 로 **0** |
| 소요 | 6.06s |

### 미처리 오류 2건 — 이행이 만든 것이 아니다

`tests/EditEntryPoints.test.tsx` 의 「브라우저 열어 Step 02 에서 멈추기」 케이스에서
`SessionScreen` 이 렌더될 때 난다.

```
TypeError: Cannot read properties of undefined (reading 'map')
  at SessionScreen src/pages/SessionScreen.tsx:645:31
      view.recorder_warnings.map(...)
```

원인은 테스트 픽스처의 `SessionView` 에 `recorder_warnings` 가 없는 것이다. 테스트는
통과하는데(단정이 끝난 뒤 비동기로 렌더가 이어진다) 오류가 콘솔로 흘러나온다.

**T004 로 2건 모두 닫았다.** 원인은 둘이었다.

1. `POST /api/sessions` 응답 픽스처에 `recorder_warnings` 등이 없었다
2. `POST /api/sessions/{id}/run-from` 이 처리기 없이 `{ ok: true }` 로 떨어져
   `SessionScreen` 이 **세션이 아닌 것**을 받았다

둘 다 `tests/helpers/workbench.ts` 의 `sessionView()` 팩토리로 교체했다.

| | 이행 전 | T004 후 |
|---|---|---|
| 테스트 | 353 통과 | 353 통과 |
| 미처리 오류 | 2 | **0** |

**이후 이 수가 늘면 007 이 만든 것이다.**

## 3. 왕복 화면 전환 수 (SC-009 의 기준)

측정 대상: **결과 확인 → 수정 → 재실행 → 결과 확인** 한 바퀴.

현재 경로 (`App.tsx` 의 화면 상태 기준):

| # | 전환 | 조작 |
|---|---|---|
| — | `result` (결과보기) | 실패한 Step 을 찾아 지목 |
| 1 | `result` → `definition` | 「Step nn 고치기」 |
| 2 | `definition` → `runner` | 「실행」 또는 「Step nn 부터 실행」 |
| 3 | `runner` → `result` | 실행이 끝난 뒤 「결과 보기」 |
| — | `result` | **지목했던 Step 을 목록에서 다시 찾는다** (S-10) |

**화면 전환 3회.** 그 밖에 **지목 Step 재탐색 1회**가 3번 전환 뒤에 필요하다 — 세션 →
결과 구간에서 맥락이 끊기기 때문이다.

**SC-009 의 판정**: 통합 후 화면 전환이 **3회를 넘지 않아야** 한다. 재탐색 1회는 SC-005
가 따로 세며 0회가 목표다.
