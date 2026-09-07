# 대체 관계 — 기존 artboard 6종 → 통합 화면 artboard (FR-254b)

**기준**: `docs/design/Workbench.dc.html` (초안 · 승인 대기)
**대체 대상**: `Main` · `RunnerPaused` · `Takeover` · `AiRecord` · `RunResult` ·
`StepInspector`
**대체하지 않는 것**: `TestList` · `CreateTest` — 한 테스트의 국면이 아니다 (FR-217a)

기존 artboard 를 **조용히 폐기하지 않는다.** 6종의 모든 영역이 어디로 갔는지 적는다.
판정 값은 넷뿐이다 — `그대로` / `이동` / `분리` / `옮기지 않음`.
`옮기지 않음` 은 **이유가 필수**다. 이유를 댈 수 없으면 요소를 잃은 것이며 DC-007 위반이다.

| 기존 artboard | 영역 | 새 위치 | 판정 | 근거 |
|---|---|---|---|---|
| | | | 미작성 | T030 이 채운다 |

## 빠짐없음 검사

002 §3 이 쓴 방법을 따른다 — 기존 6종의 `<div>` 총계와 인라인 `<svg>` 총계를 세어 이 표가
그 전부를 다루는지 확인한다.

| artboard | `<div>` | `<svg>` |
|---|---|---|
| | | 미측정 |
