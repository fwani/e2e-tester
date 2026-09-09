/**
 * 층② 국면 띠 (007 T019 · FR-218d·FR-219 · 48px).
 *
 * 담는 것은 넷이고 **순서가 고정이다** — 국면 표시 → 테스트 이름 → 진행 → 결말 요약 →
 * 그 국면의 주요 조작.
 *
 * **결말 요약은 이 띠에만 있다** (FR-218d · 005 FR-140). 이전에는 결과 화면과 세션 화면이
 * 같은 문장을 각자 만들어 나란히 그렸고, 사용자는 어느 것이 지금 실행인지 알 수 없었다
 * (U-19). `data-run-summary` 로 표시해 화면에 하나뿐임을 검사가 셀 수 있게 한다.
 *
 * ## 2026-09-08 (008)
 *
 * 이전 판은 국면 표시를 **채운 색 상자**로 그렸다 — 결말 색을 배경으로 깔고 흰 글자를
 * 얹었다. v2 는 색을 상태에만 쓰되 **채우지 않는다**: 옅은 바탕 + 같은 계열 테두리 +
 * 같은 계열 글자다 (`.chip` 과 그 변형). 색이 화면을 지배하지 않으면서 상태는 그대로
 * 읽힌다. 띠 자체도 `#F2F4F7` 바탕 + 잉크 테두리에서 정본의 `.phase` 로 옮겼다.
 */
import type { ReactNode } from "react";

import { chipClassForTone } from "../../theme/tone";
import type { PhaseBar as PhaseBarModel } from "./model";

export interface PhaseBarProps {
  bar: PhaseBarModel;
  testName: string;
  /** 그 국면의 주요 조작. 오른쪽에 온다 */
  actions: ReactNode;
}

export function PhaseBar({ bar, testName, actions }: PhaseBarProps) {
  return (
    <div data-workbench-phase-bar className="phase" style={{ flex: "0 0 48px" }}>
      {/*
        국면 표시. **화면에 하나뿐이다** (FR-219). 색만으로 국면을 알리지 않으므로 라벨이
        항상 텍스트로 있다 (ui-contract §7). 어느 변형인지는 `theme/tone.ts` 가 정한다 —
        화면이 결말을 스스로 가르면 중지가 실패로 보인다 (U-03).
      */}
      <div
        data-phase-pill
        className={chipClassForTone(bar.phaseTone)}
        style={{ height: "22px", flex: "0 0 auto" }}
      >
        {bar.phaseLabel}
      </div>

      <div className="phase-name" style={{ maxWidth: 300 }} title={testName}>
        {testName}
      </div>

      {bar.progressLabel !== null && (
        <div className="phase-progress" style={{ flex: "0 0 auto" }}>
          {bar.progressLabel}
        </div>
      )}

      {/*
        결말 요약 — **이 자리 하나뿐이다** (FR-218d · 005 FR-140 · U-19).

        **한 줄로만 그린다** (사용자 보고 · 2026-09-09). 이 칸은 남는 폭을 가져가는
        자리이고 `minWidth: 0` 이라 줄일 수 있는데, 줄 바꿈을 허용해 두면 폭이 모자랄 때
        폭 0 까지 찌그러진 채 **글자 하나씩 세로로 쌓인다** — 실제로 그 화면이 나왔다.
        말줄임이면 좁아져도 읽히는 만큼은 읽히고, 폭을 되찾으면 그대로 돌아온다.
      */}
      {bar.runSummary !== null && (
        <div
          data-run-summary
          className="line"
          style={{
            flex: 1,
            minWidth: 0,
            whiteSpace: "nowrap",
            overflow: "hidden",
            textOverflow: "ellipsis",
          }}
          title={typeof bar.runSummary === "string" ? bar.runSummary : undefined}
        >
          {bar.runSummary}
        </div>
      )}

      {bar.runSummary === null && <div className="spacer" />}

      {/*
        조작 묶음. **줄어들 수 있어야 한다** (`0 1 auto` · `minWidth: 0`).

        `0 0 auto` 였을 때, 여러 조작이 동시에 잠겨 이유 문구가 나란히 붙으면 이 묶음이
        제 내용 폭을 끝까지 요구했고 띠가 창 밖으로 밀려났다. 줄어드는 몫은 이유 문구가
        받는다 — 버튼과 해소 수단은 `ActionButton` 이 `0 0 auto` 로 지킨다.
      */}
      <div className="row" style={{ flex: "0 1 auto", minWidth: 0 }}>
        {actions}
      </div>
    </div>
  );
}
