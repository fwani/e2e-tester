/**
 * 상태·작성 방식 배지. docs/design 의 표기를 따른다.
 *
 * **원칙 I**: 작성 주체는 배지로만 구분한다. Step 의 구조와 실행 방식은 동일하다.
 */
import { outcomeChip, outcomeLabel, outcomeTone } from "../lib/wording";
import type { Author } from "../types/generated/step";
import type { Outcome } from "../types/generated/run-result";

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
    return <span className="badge">미실행</span>;
  }
  // 색만으로 구분하지 않는다 — 칩에는 항상 텍스트 라벨이 있고, 스크린리더에는
  // 한국어 문장을 준다.
  return (
    <span className={`badge ${outcomeTone(outcome)}`} title={outcomeLabel(outcome)}>
      {outcomeChip(outcome)}
    </span>
  );
}

export function AuthoringBadge({ mode }: { mode: "record" | "ai" }) {
  // FR-002a — 테스트를 시작한 방식으로 고정한다. AI 로 시작해 사람이 이어받아도 AI 다.
  return (
    <span className={`badge ${mode === "ai" ? "ai" : ""}`}>
      {mode === "ai" ? "AI" : "RECORD"}
    </span>
  );
}

export function AuthorBadge({ author }: { author: Author }) {
  // FR-075 — Step 별 작성 주체. 표시만 다르고 실행은 동일하다.
  if (author === "ai") return <span className="badge ai">AI</span>;
  return <span className="badge">HUMAN</span>;
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
  return <span className="badge mono">{label[type] ?? type.toUpperCase()}</span>;
}

export function TabBadge({ tab }: { tab: number }) {
  // FR-030a — 탭 참조. 최초 탭(0)은 표시하지 않아 화면을 어지럽히지 않는다.
  if (tab === 0) return null;
  return <span className="badge warn mono">탭 {tab}</span>;
}
