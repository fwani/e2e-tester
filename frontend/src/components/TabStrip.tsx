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

  // 껍데기(`.row rule-bottom`)의 인라인은 아직 옮기지 못했다. 그 두 클래스가 해체되기
  // 전에 유틸리티를 함께 붙이면 한 요소에 두 체계가 걸린다 (LC-5 · 가드 G-C).
  // T023(판·머리 군)·T027(수식 군) 뒤에 온다 — 배치는 부품보다 나중이다 (research R6).
  return (
    <div
 className="flex items-center border-b border-hair gap-s1 py-[6px] px-s2 overflow-x-auto"
    >
      {open.map((tab) => (
        <Button
          key={tab.tab_index}
          size="sm"
          variant={tab.tab_index === mirroredTabIndex ? "primary" : "default"}
          aria-current={tab.tab_index === mirroredTabIndex ? "true" : undefined}
          onClick={() => onSelect(tab.tab_index)}
          /* 배치는 자리가 정한다 — 부품은 자기 폭을 모른다 (LC-1).
             `whitespace-nowrap` 은 Button 이 이미 갖고 있다. */
          layout="max-w-[220px] overflow-hidden"
          title={tab.url}
        >
          <span className="font-mono">탭 {tab.tab_index}</span>
          {tab.title ? ` · ${tab.title}` : ""}
        </Button>
      ))}
      <span className="flex-1" />
      <span className="text-ink-3 font-mono">
        {open.length} / {maxTabs}
      </span>
    </div>
  );
}
