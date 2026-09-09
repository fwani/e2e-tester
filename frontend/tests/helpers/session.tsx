/**
 * 세션 국면 화면의 검사 도우미 (007 T035·T039).
 *
 * 007 이전에는 국면마다 페이지 컴포넌트가 따로 있어서 검사도 그것을 직접 그렸다
 * (`Runner`·`RunnerPaused`·`Takeover`·`AiRecord`). 통합 뒤에는 그릴 것이 `SessionWorkbench`
 * 하나이고, **국면을 정하는 것은 `SessionView` 다** — 그래서 픽스처가 세션 뷰를 만들고
 * 화면은 그것으로 국면을 판정한다.
 *
 * `workbench.ts` 의 규칙을 그대로 따른다 — **팩토리는 항상 온전한 객체를 만든다.**
 */
import { render } from "@testing-library/react";

import { MirrorView, type MirrorPhase } from "../../src/components/MirrorView";
import { SessionWorkbench, type SessionWorkbenchProps } from "../../src/pages/SessionScreen";
import type { SessionView } from "../../src/api/client";
import { capabilitiesFor } from "../../src/lib/capabilities";
import { phaseOfSession } from "../../src/lib/phase";
import { sessionView } from "./workbench";

const noop = () => undefined;

const MIRROR_PHASE: Record<string, MirrorPhase> = {
  recording: "manipulation",
  takeover_recording: "manipulation",
  paused: "paused",
};

/**
 * **진짜 `MirrorView` 를 그린다** (010 T027·T036).
 *
 * 이전에는 `<div data-testid="mirror" />` 자리표를 넘겼다. 미러가 조작을 받지 않던
 * 동안에는 그것으로 충분했다 — 미러 안에 조작이 없었으므로 「감춰진 조작 0건」 검사가
 * 셀 것도 없었다.
 *
 * 010 이 미러 안에 조작 둘을 넣었다 (`mirror.control`·`mirror.useWindow`). 자리표를
 * 그대로 두면 `CapabilityUI` 는 그 둘이 **어느 국면에도 없다**고 세고, 그 실패는 화면의
 * 결함이 아니라 도우미의 거짓말이다. 검사가 재려는 것은 「화면이 표를 따르는가」이므로
 * 화면을 그려야 한다.
 *
 * 프레임을 한 장 주는 이유는 그것이 정상 상태이기 때문이다 — 프레임이 없으면 미러는
 * 조작을 받지 않고(FR-333), 그 상태만 재면 조작 국면의 화면을 한 번도 보지 못한다.
 */
function mirrorFor(view: SessionView) {
  const phase = phaseOfSession(view);
  const caps = capabilitiesFor(phase, {
    mirrorFrameSeen: true,
    mirrorLive: true,
    controlChannelOpen: true,
    controlSurfaceIsMirror: true,
  });
  return (
    <MirrorView
      frame="AAAABBBB"
      phase={MIRROR_PHASE[view.state] ?? "observation"}
      tabIndex={view.mirrored_tab_index}
      geometry={{ width: 800, height: 600 }}
      control={caps["mirror.control"]}
      useWindowCapability={caps["mirror.useWindow"]}
    />
  );
}

export function sessionProps(
  overrides: Partial<SessionWorkbenchProps> = {},
): SessionWorkbenchProps {
  const view = overrides.view ?? sessionView();
  return {
    view,
    outcomeOf: () => "pending",
    durationOf: () => undefined,
    mirror: mirrorFor(view),
    currentUrl: "https://x.test/",
    onSelectStep: noop,
    ...overrides,
  };
}

/** 세션 뷰 덮개까지 한 번에 준다 — 국면은 `state`·`authoring_mode` 가 정한다. */
export function renderSession(
  view: Partial<SessionView> = {},
  overrides: Partial<SessionWorkbenchProps> = {},
) {
  return render(
    <SessionWorkbench {...sessionProps({ view: sessionView(view), ...overrides })} />,
  );
}
