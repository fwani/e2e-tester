/**
 * 상태·작성 방식 표식. 확정 디자인의 `.chip` 과 그 변형 5개를 쓴다.
 *
 * ## 2026-09-08 (008) — `.badge` 에서 `.chip` 으로
 *
 * 정본이 정의하는 이름은 `.chip` 이다. 코드는 같은 모양을 `.badge` 라는 **다른 이름**으로
 * 갖고 있었다 — 뜻이 같은 형태에 이름이 둘이면 어느 쪽이 기준인지 화면이 말하지 못하고,
 * 다음 개정에서 한쪽만 바뀐다. 이름과 뜻은 확정 디자인 그대로 둔다 (FR-264 · C-4).
 *
 * **원칙 I**: 작성 주체는 표식으로만 구분한다. Step 의 구조와 실행 방식은 동일하다.
 */
import { outcomeChip, outcomeLabel } from "../lib/wording";
import { chipTone } from "../theme/tone";
import type { Author } from "../types/generated/step";
import type { Outcome } from "../types/generated/run-result";

import { Chip } from "../ui/Chip";
/**
 * 실행 결말 배지 (005 T039 · FR-141).
 *
 * **네 결말을 전부 다룬다.** `outcome === "pass" ? "PASS" : "FAIL"` 로 갈리던 이분법은
 * 중지와 부분 성공을 실패로 뭉갰다 — 사용자가 누른 중지가 `FAIL` 칩으로 보였다 (U-03).
 *
 * 라벨과 색 역할은 `lib/wording` 이 정한다. 배지가 문구를 직접 만들면 화면마다 다른
 * 말이 다시 생긴다 (U-20).
 */
export function OutcomeBadge({ outcome }: { outcome: Outcome | null }) {
  if (outcome === null) {
    return <Chip tone={chipTone(null)}>미실행</Chip>;
  }
  // 색만으로 구분하지 않는다 — 칩에는 항상 텍스트 라벨이 있고, 스크린리더에는
  // 한국어 문장을 준다.
  return (
    <Chip tone={chipTone(outcome)} title={outcomeLabel(outcome)}>
      {outcomeChip(outcome)}
    </Chip>
  );
}

export function AuthoringBadge({ mode }: { mode: "record" | "ai" }) {
  // FR-002a — 테스트를 시작한 방식으로 고정한다. AI 로 시작해 사람이 이어받아도 AI 다.
  return (
    <Chip tone={mode === "ai" ? "ai" : "default"}>
      {mode === "ai" ? "AI" : "RECORD"}
    </Chip>
  );
}

export function AuthorBadge({ author }: { author: Author }) {
  // FR-075 — Step 별 작성 주체. 표시만 다르고 실행은 동일하다.
  if (author === "ai") return <Chip tone="ai">AI</Chip>;
  return <Chip>HUMAN</Chip>;
}

export function StepTypeBadge({ type }: { type: string }) {
  const label: Record<string, string> = {
    click: "CLICK",
    fill: "FILL",
    select: "SELECT",
    navigate: "GOTO",
    assertion: "ASSERT",
    close_tab: "CLOSE TAB",
    hover: "HOVER",
    drag: "DRAG",
  };
  return <Chip>{label[type] ?? type.toUpperCase()}</Chip>;
}

export function TabBadge({ tab }: { tab: number }) {
  // FR-030a — 탭 참조. 최초 탭(0)은 표시하지 않아 화면을 어지럽히지 않는다.
  if (tab === 0) return null;
  return <Chip tone="warn">탭 {tab}</Chip>;
}
