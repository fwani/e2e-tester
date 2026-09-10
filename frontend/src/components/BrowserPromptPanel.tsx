/**
 * 브라우저 요구를 화면이 대신 받는다 (010 T066 · FR-337~FR-339 · data-model §4).
 *
 * 대상 브라우저가 사용자에게 요구하는 것 중 **페이지 화면이 아닌 것**을 그린다 —
 * `alert`·`confirm`·`prompt` 대화상자와 파일 선택이다. 미러는 페이지 화면을 그리므로
 * 이것들은 거기 나타나지 않고, 창이 없으면 운영체제도 대신 보여 주지 않는다.
 *
 * **조용히 실패하지 않는 것이 이 컴포넌트의 존재 이유다** (FR-339 · SC-516). 가로채지
 * 않으면 대화상자가 대상 페이지를 세우고, 사용자에게는 「클릭했는데 아무 일도 없다」로
 * 보인다. 처리할 수 없는 요구(`unsupported`)도 **말한다** — 무엇이 막혔는지와 어떤 수단이
 * 남아 있는지를 같은 자리에 둔다 (FR-353a).
 *
 * ## 문구를 이스케이프한다
 *
 * `message` 는 **대상 페이지에서 온 값이다** (contracts §4). React 가 텍스트 노드를
 * 자동으로 이스케이프하므로 `dangerouslySetInnerHTML` 을 쓰지 않는 것으로 충분하다 —
 * 이 파일에 그것이 없다는 사실이 헌법 보안 요건(외부 입력은 경계에서 검증한다)의 구현이다.
 */

import { useState } from "react";

import type { BrowserPromptKind } from "../lib/wording";
import { promptTitle, promptDetail, PROMPT_ACTIONS } from "../lib/wording";

import { Button } from "../ui/Button";

export interface BrowserPromptState {
  promptId: string;
  kind: BrowserPromptKind;
  /** 대상 페이지에서 온 값. **텍스트로만 그린다** */
  message: string;
  multiple?: boolean;
  /** 응답이 없으면 대상 페이지가 멈추는가 */
  blocking?: boolean;
}

export interface BrowserPromptPanelProps {
  prompt: BrowserPromptState | null;
  /** 사용자의 선택을 서버로 보낸다 */
  onAnswer: (answer: { accept: boolean; text?: string; files?: File[] }) => void;
  /**
   * 실제 창으로 전환한다 (FR-353a).
   *
   * **`unsupported` 에서 이것이 유일하게 남은 수단이다.** 무엇이 막혔는지를 읽은 그
   * 자리에서 바로 전환할 수 있어야 한다.
   */
  onUseWindow?: () => void;
  /** 「실제 창에서 조작하기」를 지금 쓸 수 있는가. 없으면 그 버튼을 그리지 않는다 */
  canUseWindow?: boolean;
}

export function BrowserPromptPanel({
  prompt,
  onAnswer,
  onUseWindow,
  canUseWindow = false,
}: BrowserPromptPanelProps) {
  const [text, setText] = useState("");
  const [files, setFiles] = useState<File[]>([]);

  if (prompt === null) return null;

  const isDialog = prompt.kind.startsWith("dialog.");
  const isFile = prompt.kind === "file.choose";
  const isUnsupported = prompt.kind === "unsupported";

  return (
    <div
      className={isUnsupported ? "row tint-warn" : "row tint-run"}
      style={{ gap: 8, padding: "10px 14px", flexWrap: "wrap" }}
      role={prompt.blocking ? "alertdialog" : "status"}
      data-browser-prompt={prompt.kind}
    >
      <strong>{promptTitle(prompt.kind)}</strong>
      {/*
        대상 페이지에서 온 값이다. React 가 텍스트 노드로 이스케이프한다 —
        `dangerouslySetInnerHTML` 을 쓰지 않는 것이 그 보증이다 (contracts §4).
      */}
      {prompt.message !== "" && <span className="muted">{prompt.message}</span>}
      {prompt.message === "" && <span className="muted">{promptDetail(prompt.kind)}</span>}

      {prompt.kind === "dialog.prompt" && (
        <input
          type="text"
          value={text}
          onChange={(event) => setText(event.target.value)}
          aria-label={PROMPT_ACTIONS.textLabel}
          data-prompt-text
        />
      )}

      {isFile && (
        <input
          type="file"
          multiple={prompt.multiple === true}
          aria-label={PROMPT_ACTIONS.fileLabel}
          data-prompt-file
          onChange={(event) => setFiles(Array.from(event.target.files ?? []))}
        />
      )}

      <span className="spacer" />

      {isFile && (
        <Button
          type="button"
          variant="primary"
          data-prompt-accept
          disabled={files.length === 0}
          onClick={() => onAnswer({ accept: true, files })} >
          {PROMPT_ACTIONS.attach}
        </Button>
      )}

      {isDialog && (
        <Button
          type="button"
          variant="primary"
          data-prompt-accept
          onClick={() => onAnswer({ accept: true, text })} >
          {PROMPT_ACTIONS.accept}
        </Button>
      )}

      {/*
        **취소도 응답이다.** 고르지 않겠다는 선택을 보내지 않으면 대상 페이지는 계속
        기다리고, 그것이 조용한 실패가 된다 (FR-339).
      */}
      {(isDialog || isFile) && (
        <Button
          type="button"
          
          data-prompt-dismiss
          onClick={() => onAnswer({ accept: false })}>
          {PROMPT_ACTIONS.dismiss}
        </Button>
      )}

      {/*
        FR-353a — 막힌 상황에서 **전환 수단이 그 자리에 보인다.** 무엇이 막혔는지 읽은
        자리에서 바로 전환할 수 있어야 한다. `unsupported` 에서는 이것이 유일한 수단이다.
      */}
      {isUnsupported && canUseWindow && (
        <Button type="button" variant="primary" data-prompt-use-window onClick={onUseWindow}>
          {PROMPT_ACTIONS.useWindow}
        </Button>
      )}
    </div>
  );
}
