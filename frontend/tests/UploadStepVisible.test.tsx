/**
 * 파일 업로드 Step 이 화면에 드러난다 (2026-09-09 사용자 보고).
 *
 * 보고 문장: 「파일업로드 녹화의 경우, 파일의 확장자 기록되 되어야함. 실제 서비스에서는
 * 확장자를 보는경우가 있기 때문」.
 *
 * 그래서 이 파일이 재는 것은 **확장자가 사용자에게 닿는가**다. 정의에 남아 있어도 화면이
 * 보여 주지 않으면 사용자는 어느 Step 이 어떤 파일을 올리는지 알 수 없고, 목록을 훑어
 * 「xlsx 를 올리는 Step」을 찾을 수 없다.
 *
 * 확장자를 **별도 칸으로 두지 않은 것**도 함께 고정한다 — 이름의 일부이므로 이름을 보이면
 * 확장자가 보인다. 둘을 따로 두면 「보고서.xlsx 인데 확장자는 csv」인 Step 이 만들어진다.
 */
import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { StepDetail } from "../src/components/workbench/StepDetail";
import { StepList } from "../src/components/workbench/StepList";
import { capabilitiesFor } from "../src/lib/capabilities";
import { uploadExtension } from "../src/lib/wording";
import { ALL_FACTS } from "./helpers/model";
import type { Step } from "../src/types/generated/step";

afterEach(cleanup);

const UPLOAD = {
  type: "upload",
  id: "st-1",
  label: "첨부 파일 에 보고서.xlsx 올리기",
  author: "human",
  frame_url: null,
  tab: 0,
  timeout_ms: 5000,
  target: {
    accessible_name: "첨부 파일",
    css: { status: "verified", value: "input[type=file]" },
    label: null,
    role: "button",
    role_status: "verified",
    stable_attr: null,
    tag: "input",
    test_id: null,
    text: null,
  },
  file_name: "보고서.xlsx",
} as unknown as Step;

describe("확장자 판정은 한 규칙이다 (`uploadExtension`)", () => {
  it("마지막 조각만 보고, 소문자로 돌려준다", () => {
    expect(uploadExtension("보고서.XLSX")).toBe("xlsx");
    expect(uploadExtension("archive.tar.gz")).toBe("gz");
  });

  it("확장자가 없으면 빈 문자열이다 — 오류가 아니다", () => {
    expect(uploadExtension("README")).toBe("");
    expect(uploadExtension("이름.")).toBe("");
    /*
      숨김 파일은 확장자가 없다. **백엔드와 같은 규칙이어야 한다**
      (`itb.domain.step.extension_of`) — 갈리면 화면이 「xlsx 로 올립니다」라고 적고
      실제로는 다른 것이 올라간다. 실제로 첫 판에서 갈렸고 백엔드 검사가 잡았다.
    */
    expect(uploadExtension(".gitignore")).toBe("");
  });
});

describe("Step 목록 행이 파일 이름을 보인다", () => {
  it("행을 열지 않고 확장자를 읽을 수 있다", () => {
    render(
      <StepList
        steps={[
          {
            id: "st-1",
            index: 0,
            step: UPLOAD,
            label: UPLOAD.label,
            outcome: "recorded",
            durationMs: null,
            isPausedHere: false,
          },
        ]}
        authoring="record"
        focusedStepId={null}
        onSelect={() => undefined}
      />,
    );
    // 값 칸이 파일 이름을 담는다 — `fill`·`select` 의 입력값과 같은 자리다.
    expect(screen.getAllByText("보고서.xlsx").length).toBeGreaterThan(0);
  });
});

describe("Step 상세에서 파일 이름을 고친다", () => {
  const detail = {
    step: UPLOAD,
    index: 0,
    attempts: null,
    candidates: null,
    dropCandidates: null,
    repickWaiting: null,
    failure: null,
  };

  it("이름 칸이 있고, 지금 확장자를 함께 말한다", () => {
    render(
      <StepDetail
        detail={detail}
        capabilities={capabilitiesFor("paused", ALL_FACTS)}
        ownFields
        onSave={() => undefined}
        onRepick={() => undefined}
        onClose={() => undefined}
      />,
    );
    const field = screen.getByLabelText("올릴 파일 이름") as HTMLInputElement;
    expect(field.value).toBe("보고서.xlsx");
    /*
      **한계를 숨기지 않는다.** 재실행은 같은 이름의 **빈** 파일을 올린다. 내용을 파싱하는
      서버에서 실패했을 때 사용자가 이유를 찾을 곳이 화면에 있어야 한다
      (`step_executor._upload` 의 한계 주석과 같은 사실).
    */
    expect(screen.getByText(/확장자 xlsx/)).toBeTruthy();
    expect(screen.getByText(/내용을 읽는 검증/)).toBeTruthy();
  });

  it("고친 이름을 `file_name` 으로 보낸다 — `value` 로 보내지 않는다", () => {
    const onSave = vi.fn();
    render(
      <StepDetail
        detail={detail}
        capabilities={capabilitiesFor("paused", ALL_FACTS)}
        ownFields
        onSave={onSave}
        onRepick={() => undefined}
        onClose={() => undefined}
      />,
    );
    fireEvent.change(screen.getByLabelText("올릴 파일 이름"), {
      target: { value: "자료.csv" },
    });
    (document.querySelector('button[data-action="step.update"]') as HTMLButtonElement).click();

    /*
      `upload` Step 은 `value` 필드를 갖지 않는다. 같은 칸으로 보내면 서버가 「입력값을
      갖지 않는 Step 에 값을 지정했다」로 거절한다 — 화면과 서버가 다른 필드를 말하는 상태다.
    */
    expect(onSave).toHaveBeenCalledWith(
      expect.objectContaining({ file_name: "자료.csv" }),
    );
    const patch = onSave.mock.calls[0]?.[0] as { value?: string } | undefined;
    expect(patch?.value).toBeUndefined();
  });
});
