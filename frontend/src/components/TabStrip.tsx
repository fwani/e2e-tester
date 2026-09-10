/**
 * 탭 표시·전환 (T069). **확정 디자인에 없는 화면**이므로 8화면의 시각 언어를 따른다
 * (spec 디자인 차이 3).
 *
 * 미러는 한 번에 한 탭만 스트리밍한다 — 모든 탭을 동시에 보내면 프레임률 목표를
 * 탭 수로 나누게 된다 (research R3). 그래서 "표시 중인 탭" 개념이 필요하다.
 */
import type { TabView } from "../api/client";

import { Button } from "../ui/Button";

export interface TabStripProps {
  tabs: TabView[];
  mirroredTabIndex: number;
  maxTabs: number;
  onSelect: (tabIndex: number) => void;
}

export function TabStrip({ tabs, mirroredTabIndex, maxTabs, onSelect }: TabStripProps) {
  const open = tabs.filter((t) => !t.closed);
  if (open.length <= 1) return null; // 탭이 하나면 표시할 이유가 없다

  return (
    <div
      className="row rule-bottom"
      style={{ gap: 4, padding: "6px 8px", overflowX: "auto" }}
    >
      {open.map((tab) => (
        <Button
          key={tab.tab_index}
          size="sm"
          variant={tab.tab_index === mirroredTabIndex ? "primary" : "default"}
          aria-current={tab.tab_index === mirroredTabIndex ? "true" : undefined}
          onClick={() => onSelect(tab.tab_index)}
          style={{ whiteSpace: "nowrap", maxWidth: 220, overflow: "hidden" }}
          title={tab.url}
        >
          <span className="mono">탭 {tab.tab_index}</span>
          {tab.title ? ` · ${tab.title}` : ""}
        </Button>
      ))}
      <span className="spacer" />
      <span className="dim mono">
        {open.length} / {maxTabs}
      </span>
    </div>
  );
}
