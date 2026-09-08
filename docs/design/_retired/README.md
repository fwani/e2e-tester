# 폐기된 디자인 (2026-09-08)

이 디렉터리의 것은 **더 이상 디자인이 아니다.** 대조 기준이 아니고, 새 화면의 근거가
아니며, 여기 있는 값을 코드로 옮기지 않는다.

대체한 것: [`docs/design/008-visual-language/`](../008-visual-language/) 18장.
대응 관계: [`replacement-map.md`](../008-visual-language/replacement-map.md).

## 무엇이 폐기됐나

| 폐기 대상 | 성격 | 라운드 |
|---|---|---|
| `TestList` · `CreateTest` · `AiRecord` · `Main` · `RunnerPaused` · `Takeover` · `RunResult` · `StepInspector` | 확정 디자인 8종 | 001 · 002 |
| `Workbench.dc.html` | 통합 화면 1회차 초안 | 007 |
| `007-rework/` 11장 | 통합 화면 2회차 초안 | 007 |
| `canvas.json` | 위 항목들의 캔버스 배치 | — |
| `interactive-ai-test-builder-screens.html` | 최초 디자인 export (2.6MB) | 001 |

## 왜 지우지 않고 남겼나

002 · 007 의 **대조 기록(design-conformance)** 이 이 파일들을 대상으로 한 판정이다.
파일을 지우면 그 판정이 무엇을 본 것인지 알 수 없게 된다 — 헌법의 Compliance review 가
과거 판정을 다시 읽을 수 있어야 한다고 요구한다.

`scripts/design_baseline.py` 는 더 이상 이 디렉터리를 읽지 않는다. 남아 있는 이유는
**이력을 읽기 위해서**이지 기준으로 쓰기 위해서가 아니다.

완전히 지우려면 이 디렉터리를 통째로 삭제하면 된다 — git 이력에는 남는다.
