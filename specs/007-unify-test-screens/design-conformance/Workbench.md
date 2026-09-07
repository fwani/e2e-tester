# 디자인 대조 — Workbench (통합 작업 화면)

> **이 artboard 는 승인 대기 중이며 대조 기준으로 확정되지 않았다** (FR-254c ·
> `contracts/design-conformance-007.md` §5). 승인 전 판정은 성립하지 않는다.

**기준**: `docs/design/Workbench.dc.html` (1440×900, 초안)
**대상**: `frontend/src/components/workbench/*` · `frontend/src/pages/{SessionScreen,ResultView,EditView}.tsx`

`축`·`항목`·`기준값` 은 `scripts/design_baseline.py` 가 기계적으로 채운다.
`관측값`·`판정`·`비고` 는 **사람이 채운다** — 구현자가 자기 구현을 판정하면 대조가 아니라
자기 확인이다 (002 §4).

축은 6개 — 구조 / 컴포넌트 / 치수 / 타이포·색 / 상태 / 가감.
**`상태` 축은 국면마다 행을 갖는다** — 일곱 국면이 하나의 화면이므로 상태가 일곱이다.

| 축 | 항목 | 기준값 | 관측값 | 판정 | 비고 |
|---|---|---|---|---|---|
| | | | | 미판정 | T080 이 기준값을 채운다 |

**완료 판정**: `불일치`·`미판정` 이 0건. 단 artboard 승인 후에만 성립한다.
