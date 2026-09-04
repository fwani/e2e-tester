/**
 * 오류 표시의 **공용 통로** (003 EC-004 · RG-104-4).
 *
 * 화면이 `err.message` 를 직접 그리면 `next_action` 이 빠져도 아무도 모른다. 003 이전이
 * 그랬다 — 무엇이 잘못됐는지는 나오는데 무엇을 하면 되는지는 나오지 않았다.
 *
 * 이 통로는 **둘을 함께** 보여준다.
 *
 * - `category: "blocked"` — 사용자가 고칠 수 있다. 다음 행동이 구체적인 교정 방법이다
 * - `category: "broken"` — 사용자가 할 수 있는 일이 없다. 고칠 수 있는 것처럼 보이게 하지 않고,
 *   작업이 보존됐는지와 무엇을 남겨 보고할지를 알린다
 *
 * 계약 형태가 아닌 실패(연결 끊김 등)도 같은 통로를 지난다. 그때는 `broken` 이다 — 제품이
 * 스스로를 설명하지 못한 것이므로.
 */
import { ApiError } from "../api/client";
import type { Category, ErrorBody } from "../types/generated/error-response";

/** 화면이 상태에 담는 형태. 문자열 대신 이것을 담아야 다음 행동이 살아남는다. */
export interface ErrorInfo {
  message: string;
  nextAction: string;
  category: Category;
  code: string;
}

const FALLBACK_ACTION = "화면을 새로 고쳐 다시 시도하세요. 계속 발생하면 서버 로그를 확인하세요.";

/**
 * 잡은 것이 무엇이든 표시 가능한 형태로 바꾼다.
 *
 * `catch (exc: unknown)` 에서 그대로 부르면 된다. 계약 오류면 분류와 다음 행동이 그대로
 * 실리고, 그 밖의 실패는 `broken` 으로 다룬다.
 */
export function describeError(exc: unknown): ErrorInfo {
  if (exc instanceof ApiError) {
    return {
      message: exc.message,
      nextAction: exc.nextAction || FALLBACK_ACTION,
      category: exc.category,
      code: exc.code,
    };
  }
  return {
    message: exc instanceof Error ? exc.message : String(exc),
    nextAction: FALLBACK_ACTION,
    category: "broken",
    code: "UNKNOWN",
  };
}

/**
 * 화면이 스스로 내는 안내. 서버 오류가 아니라 화면 자체의 규칙에 걸린 경우다.
 *
 * 다음 행동을 **인자로 받는다** — 기본값을 두면 "화면을 새로 고치세요" 같은 쓸모없는
 * 문구가 조용히 붙는다. 화면이 스스로 막았다면 무엇을 하면 되는지도 알고 있어야 한다.
 */
export function localError(message: string, nextAction: string): ErrorInfo {
  return { message, nextAction, category: "blocked", code: "UNKNOWN" };
}

/**
 * 실시간 통로로 온 오류를 표시 가능한 형태로 바꾼다 (003 EC-008).
 *
 * 서버가 계약 본문(`error`)을 실어 보내면 분류와 다음 행동이 그대로 온다. 아직 문자열만
 * 오는 이벤트는 화면이 다음 행동을 붙인다 — 통로를 하나로 두기 위해서다.
 */
export function fromEvent(
  body: ErrorBody | undefined,
  reason: string,
  fallbackAction: string,
): ErrorInfo {
  if (body) {
    return {
      message: body.message,
      nextAction: body.next_action || fallbackAction,
      category: body.category,
      code: body.code,
    };
  }
  return { message: reason, nextAction: fallbackAction, category: "blocked", code: "UNKNOWN" };
}

const TONE: Record<Category, { border: string; bg: string; label: string }> = {
  // 막은 것 — 고치면 되는 일이라 경고 색으로 둔다.
  blocked: { border: "#C9A227", bg: "#FDF8E7", label: "확인이 필요합니다" },
  // 깨진 것 — 사용자가 할 수 있는 일이 없다. 실패 색으로 분명히 구분한다.
  broken: { border: "#B4453C", bg: "#FBEDEB", label: "도구에 문제가 생겼습니다" },
};

export function ErrorNotice({
  error,
  compact = false,
}: {
  error: ErrorInfo | null;
  /** 좁은 자리에서 제목 줄을 생략한다. 다음 행동은 생략하지 않는다. */
  compact?: boolean;
}) {
  if (error === null) return null;

  const tone = TONE[error.category];
  return (
    <div
      role="alert"
      data-error-notice
      data-category={error.category}
      data-code={error.code}
      style={{
        display: "flex",
        flexDirection: "column",
        gap: 6,
        padding: compact ? "8px 10px" : "12px 14px",
        border: `1px solid ${tone.border}`,
        background: tone.bg,
        borderRadius: 2,
      }}
    >
      {!compact && (
        <div
          style={{
            font: "700 12px/1 'IBM Plex Mono', ui-monospace, monospace",
            letterSpacing: "0.06em",
            color: tone.border,
          }}
        >
          {tone.label}
        </div>
      )}
      <div
        data-error-message
        style={{
          font: "500 14px/1.5 'IBM Plex Sans KR', system-ui, sans-serif",
          whiteSpace: "pre-wrap",
          // 아주 긴 입력이 그대로 되돌아와도 화면을 밀어내지 않는다 (AP-015).
          overflowWrap: "anywhere",
        }}
      >
        {error.message}
      </div>
      <div
        data-error-next-action
        style={{
          font: "400 13px/1.5 'IBM Plex Sans KR', system-ui, sans-serif",
          color: "#6B675C",
          overflowWrap: "anywhere",
        }}
      >
        {error.nextAction}
      </div>
    </div>
  );
}
