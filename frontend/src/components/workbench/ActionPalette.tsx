/**
 * Step 패널 바닥의 **공통 조작 팔레트** (007 T058~T062 · FR-234·FR-235).
 *
 * ## 왜 한 파일인가
 *
 * FR-235 는 "같은 조작은 어느 국면에서나 같은 자리에 같은 라벨로" 를 요구한다. 자리를
 * 국면마다 조립하면 한 국면이 하나를 빠뜨리고, 빠진 것이 **감춰진 조작**이 된다 —
 * 그것이 사용자가 "화면마다 다 달라서" 라고 말한 것의 실체다.
 *
 * 그래서 순서와 구성을 이 파일이 갖는다. 국면은 **무엇을 할 수 있는지**만 권한표로
 * 넘기고, 무엇을 그릴지는 정하지 않는다.
 *
 * ## 조작의 집 (ui-contract §4-1 의 배치 규칙)
 *
 *   국면 띠      run.* (실행·일시정지·계속·중지·속도)
 *   헤더          session.open · result.show · nav.editStep · nav.back
 *   대상 앱 영역  browser.openAt · artifact.select · tab.select
 *   Step 행       step.select
 *   Step 상세     step.update · step.markSensitive · step.repick
 *   **이 팔레트** 나머지 전부 — Step 작성·순서·삭제, 테스트 속성, 저장
 *
 * 「해당 없음」인 조작은 `ActionButton` 이 스스로 그리지 않는다. 그래서 국면이 달라도
 * 코드가 같고, 화면에는 그 국면의 조작만 남는다.
 */
import type { ReactNode } from "react";

import type { ActionId } from "../../lib/actions";
import type { CapabilityMap, CapabilityState } from "../../lib/capabilities";
import { ACTION_LABEL } from "../../lib/wording";
import { ActionButton } from "./ActionButton";


/**
 * 버튼 줄의 **고정 순서**. 국면이 이 순서를 바꾸지 않는다.
 *
 * `step.update`·`step.markSensitive`·`step.repick` 은 여기 없다 — 그것들은 Step 상세가
 * 집이고, 두 곳에 두면 같은 라벨이 두 자리에 생긴다 (FR-235).
 */
export const PALETTE_ACTIONS: ActionId[] = [
  "step.recordStart",
  "step.recordStop",
  "step.addAssertion",
  "step.insertManual",
  "step.moveUp",
  "step.moveDown",
  "step.delete",
  "run.fromHere",
  "browser.openAt",
  "ai.start",
  "save.overwriteStale",
];

export interface ActionPaletteProps {
  capabilities: CapabilityMap;
  /** 그 조작을 실제로 실행한다. 「해당 없음」인 것은 불리지 않는다. */
  onRun: (action: ActionId) => void;
  /** 비활성 조작의 해소 방법을 눌렀을 때 */
  onRemedy: (action: ActionId) => void;
  /** 상황에 따라 바뀌는 라벨 (`run.fromHere` 의 시작 지점 등) */
  labels?: Partial<Record<ActionId, string>>;
  /**
   * 화면이 아는 사실로 표를 한 겹 더 좁힌다.
   *
   * 표는 **국면**을 말한다. "지목한 Step 이 없다" 는 국면이 아니므로 표에 담을 수 없고,
   * 담지 않으면 무엇에 걸지 모르는 조작이 활성으로 남아 눌러도 아무 일이 없다.
   */
  narrow?: (action: ActionId, base: CapabilityState) => CapabilityState;

  /** 자연어로 Step 추가 (FR-078). 입력칸과 버튼이 한 쌍이다 */
  nl: { value: string; onChange: (v: string) => void; onSubmit: () => void };

  /**
   * 직접 입력으로 Step 추가 (009 FR-285). **자연어 입력과 같은 문법이다** — 조작 하나가
   * 그 자리에서 입력면을 여닫는다.
   *
   * 주지 않으면 버튼만 그린다(눌러도 아무 일이 없는 것이 아니라 `onRun` 이 받는다).
   * 화면이 폼을 다른 자리에 두기로 했으면 그렇게 할 수 있다.
   */
  insert?: {
    open: boolean;
    /** 열려 있을 때 그 자리에 그릴 것. 화면이 만든다 — 팔레트가 폼을 소유하지 않는다 */
    form: ReactNode;
  };

  /** 테스트 이름 (`test.rename`). 세션에서는 저장 이름을 겸한다 */
  name: string;
  onNameChange: (v: string) => void;
  /** 시작 주소 (`test.setStartUrl`) */
  startUrl: string;
  onStartUrlChange: (v: string) => void;
  /** AI 지시문 (`ai.compose`). 기록이며 국면에 따라 읽기 전용이다 (FR-063) */
  instruction: string | null;
  onInstructionChange?: (v: string) => void;

  /** 저장 버튼의 라벨. 세션과 편집이 규칙이 다르다 (005 FR-156 · 006 FR-195) */
  saveLabel: string;
  /** 표가 허락해도 화면이 아는 사실로 더 좁힐 때 (이름이 비었다 · 바꾼 것이 없다) */
  saveCapability?: CapabilityState;
  /** 저장 성공 확인줄 등, 저장 블록 아래에 붙는 것 */
  saveNotice?: ReactNode;

  stepCount: number;
  /** Step 이 0개일 때의 안내. 국면마다 다르다 */
  emptyHint?: string;
  /**
   * 이 국면에서는 **다른 자리가 집인** 조작.
   *
   * 편집 국면의 `browser.openAt` 은 대상 앱 영역이 갖고(T079), 충돌 중의
   * `save.overwriteStale` 은 「다시 읽기」와 짝을 이뤄 보조 영역이 갖는다(FR-209).
   * 여기 이름을 넣는 것은 조작을 **없애는** 것이 아니라 **자리를 옮기는** 것이며,
   * `CapabilityUI` 가 그 자리에 실제로 있는지 센다.
   */
  hidden?: ActionId[];
}

export function ActionPalette({
  capabilities,
  onRun,
  onRemedy,
  labels = {},
  narrow,
  nl,
  name,
  onNameChange,
  startUrl,
  onStartUrlChange,
  instruction,
  onInstructionChange,
  saveLabel,
  saveCapability,
  saveNotice,
  stepCount,
  emptyHint,
  hidden = [],
  insert,
}: ActionPaletteProps) {
  const capabilityOf = (action: ActionId): CapabilityState => {
    const base = capabilities[action];
    return narrow ? narrow(action, base) : base;
  };
  const usable = (action: ActionId) => capabilityOf(action).kind === "enabled";
  const shown = (action: ActionId) =>
    capabilities[action].kind !== "not_applicable" && !hidden.includes(action);

  const button = (action: ActionId, run: () => void) => (
    <ActionButton
      key={action}
      action={action}
      capability={capabilityOf(action)}
      label={labels[action]}
      compact
      onRun={run}
      onRemedy={onRemedy}
    />
  );

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
      <div className="lbl">지금 할 수 있는 것</div>

      {/* 자연어로 Step 추가 (FR-078). 쓸 수 없으면 입력칸을 잠그고 이유는 버튼이 말한다. */}
      {shown("step.addNaturalLanguage") && (
        <div style={{ display: "flex", gap: 10, alignItems: "flex-start" }}>
          <input
            aria-label="자연어로 Step 추가"
            value={nl.value}
            disabled={!usable("step.addNaturalLanguage")}
            onChange={(e) => nl.onChange(e.target.value)}
            placeholder="생성된 프로젝트가 목록에 있는지 확인해."
            className="ai"
            style={{ flex: "1", minWidth: 0 }}
          />
          {button("step.addNaturalLanguage", () => {
            if (nl.value.trim() === "") return;
            nl.onSubmit();
          })}
        </div>
      )}

      <div style={{ display: "flex", flexWrap: "wrap", gap: 10, alignItems: "flex-start" }}>
        {PALETTE_ACTIONS.filter(shown).map((action) => button(action, () => onRun(action)))}
      </div>

      {/*
        009 — 삽입 입력면. **닫혀 있으면 자리를 차지하지 않는다** (008 FR-218e 와 같은
        규칙) — 빈 영역이 남아 다른 영역의 자리를 바꾸지 않는다.
      */}
      {insert?.open === true && insert.form}

      {/* ─── 테스트 속성 (FR-247 — 통합으로 사라지는 조작이 없다) ────────────── */}
      {(shown("test.rename") || shown("test.setStartUrl")) && (
        <div
          className="rule-top"
          style={{ display: "flex", flexDirection: "column", gap: 8, paddingTop: 12 }}
        >
          {shown("test.rename") && (
            <Field
              action="test.rename"
              label="테스트 이름"
              capability={capabilityOf("test.rename")}
              value={name}
              onChange={onNameChange}
              maxLength={200}
              onRemedy={onRemedy}
            />
          )}
          {shown("test.setStartUrl") && (
            <Field
              action="test.setStartUrl"
              label="시작 주소"
              capability={capabilityOf("test.setStartUrl")}
              value={startUrl}
              onChange={onStartUrlChange}
              maxLength={2000}
              mono
              onRemedy={onRemedy}
            />
          )}
        </div>
      )}

      {/*
        AI 지시문 (001 FR-063·FR-064). **수행 중에는 고칠 수 없고 기록으로 계속 보인다.**
        보이지 않으면 사용자는 자기가 무엇을 시켰는지 잃는다 (UX U-07).
      */}
      {shown("ai.compose") && (
        <Field
          action="ai.compose"
          label="AI 지시문"
          capability={capabilityOf("ai.compose")}
          value={instruction ?? ""}
          onChange={(v) => onInstructionChange?.(v)}
          maxLength={4000}
          multiline
          onRemedy={onRemedy}
        />
      )}

      {/* ─── 저장 (005 FR-155·FR-156 · 006 FR-195) ────────────────────────── */}
      {shown("save") && (
        <div
          className="rule-top"
          style={{
            display: "flex",
            gap: 10,
            paddingTop: 12,
            alignItems: "flex-start",
            flexWrap: "wrap",
          }}
        >
          <ActionButton
            action="save"
            capability={saveCapability ?? capabilityOf("save")}
            label={saveLabel}
            compact
            emphasis
            onRemedy={onRemedy}
            onRun={() => onRun("save")}
          />
          {shown("edits.revert") && button("edits.revert", () => onRun("edits.revert"))}
          {/*
            `save.overwriteStale` 은 여기 없다. 그것은 **두 선택 중 하나**이고(FR-209),
            다른 하나(「바뀐 내용으로 다시 읽기」)와 나란히 있어야 무엇을 버리는지 고를
            수 있다. 그 짝의 집은 국면 보조 영역의 충돌 블록이다.
          */}
        </div>
      )}

      {saveNotice}

      {stepCount === 0 && emptyHint !== undefined && (
        <div className="why">{emptyHint}</div>
      )}
    </div>
  );
}

/**
 * 값을 고치는 조작 하나 — 입력칸이 곧 그 조작이다.
 *
 * 버튼이 아니라 입력칸인 조작에도 **같은 규칙**이 적용된다 (FR-234): 쓸 수 없으면
 * 같은 자리에 비활성으로 남고 이유가 붙는다. `data-action` 을 달아 두면 "감춰진 조작
 * 0건" 을 세는 검사가 버튼과 입력칸을 가리지 않고 셀 수 있다 (SC-004).
 */
function Field({
  action,
  label,
  capability,
  value,
  onChange,
  maxLength,
  mono = false,
  multiline = false,
  placeholder,
  onRemedy,
}: {
  action: ActionId;
  label: string;
  capability: CapabilityState;
  value: string;
  onChange: (v: string) => void;
  maxLength: number;
  mono?: boolean;
  multiline?: boolean;
  /**
   * 빈 칸이 무엇을 받는지 말한다.
   *
   * 라벨만 두면 칸이 비었을 때 무엇을 넣어야 하는지가 라벨 하나에 달린다 —
   * 실브라우저 계층(AS-008)이 이 자리를 `placeholder` 로 찾는 것도 그것이 사용자가
   * 칸을 알아보는 방식이기 때문이다.
   */
  placeholder?: string;
  onRemedy: (action: ActionId) => void;
}) {
  if (capability.kind === "not_applicable") return null;
  const disabled = capability.kind === "disabled";
  const reasonId = `reason-${action}`;
  const common = {
    "data-action": action,
    "aria-label": label,
    placeholder: placeholder ?? label,
    value,
    disabled,
    maxLength,
    "aria-describedby": disabled ? reasonId : undefined,
    onChange: (e: { target: { value: string } }) => onChange(e.target.value),
    className: mono ? "mono" : undefined,
    style: { flex: 1, minWidth: 0 } as const,
  };

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 4 }}>
      <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
        <span className="field-label" style={{ width: 76 }}>
          {label}
        </span>
        {multiline ? (
          <textarea {...common} rows={2} style={{ ...common.style, minHeight: 48 }} />
        ) : (
          <input {...common} style={{ ...common.style, height: 40, minHeight: 40 }} />
        )}
      </div>
      {disabled && (
        <span
          id={reasonId}
          data-disabled-reason={action}
          className="why"
          style={{ paddingLeft: 84 }}
        >
          {capability.reason}
          {capability.remedy !== null && (
            <>
              {" "}
              <button
                type="button"
                data-remedy-for={action}
                className="textlink"
                onClick={() => onRemedy(capability.remedy!.action)}
              >
                {ACTION_LABEL[capability.remedy.action]}
              </button>
            </>
          )}
        </span>
      )}
    </div>
  );
}
