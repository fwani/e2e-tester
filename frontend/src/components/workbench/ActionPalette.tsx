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
 * ## 조작의 집
 *
 * **정본은 007 계약 §2-7 이다.** 011 이 그 표를 계약으로 올렸다 — 그 전까지 규칙은 이
 * 주석에만 있었고, 주석은 자기 근거를 계약에 없는 절(§4-1 「비활성의 의무」)로 적고
 * 있었다. 코드 주석이 유일한 근거이면 그것을 옮기는 변경이 계약 개정으로 보이지 않는다.
 *
 *   국면 띠      run.* (실행·일시정지·계속·중지·속도) · save · edits.revert · test.rename
 *   헤더          session.open · result.show · nav.editStep · nav.back
 *   대상 앱 영역  browser.openAt · artifact.select · tab.select · mirror.*
 *   Step 행       step.select · step.toggleDeleteTarget
 *   Step 패널 머리 step.selectAllDeleteTargets
 *   Step 상세     step.update · step.markSensitive · step.repick
 *   **이 팔레트** 나머지 전부 — Step 작성·순서·삭제 · test.setStartUrl · ai.compose
 *
 * 「해당 없음」인 조작은 `ActionButton` 이 스스로 그리지 않는다. 그래서 국면이 달라도
 * 코드가 같고, 화면에는 그 국면의 조작만 남는다.
 *
 * ## 2026-09-10 (011) — 저장과 이름이 이 파일을 떠났다
 *
 * 사용자 보고: 「테스트를 저장하는 버튼과 이름을 지정하는게 오른쪽 아래에 존재하는데,
 * ux 적으로 매우 불편함」. 이 팔레트는 우측 460px Step 패널의 **바닥**이다 — 저장하려면
 * Step 목록을 다 지나 내려와야 했고, 못 찾고 나가면 기록이 사라졌다.
 *
 * `save`·`edits.revert`·`test.rename` 은 국면 띠로 갔다 (`PhaseBar.tsx`).
 *
 * **`test.setStartUrl`·`ai.compose` 는 남았다.** 국면 띠에 표시되지 않는 값이므로
 * 「보이는 곳에서 고친다」 논리가 성립하지 않고, 48px 한 줄은 긴 URL 도 여러 줄 지시문도
 * 담을 수 없다 (research R1).
 */
import type { ReactNode } from "react";

import type { ActionId } from "../../lib/actions";
import { isShown, type CapabilityMap, type CapabilityState } from "../../lib/capabilities";
import { ACTION_LABEL } from "../../lib/wording";
import { ActionButton } from "./ActionButton";

/**
 * 버튼 줄의 **고정 순서**. 국면이 이 순서를 바꾸지 않는다.
 *
 * `step.update`·`step.markSensitive`·`step.repick` 은 여기 없다 — 그것들은 Step 상세가
 * 집이고, 두 곳에 두면 같은 라벨이 두 자리에 생긴다 (FR-235).
 */
export const PALETTE_ACTIONS: ActionId[] = [
  /*
    `step.recordStart`·`step.recordStop`·`step.addNaturalLanguage` 는 여기 없다 — 011 이
    셋을 **Step 을 더하는 묶음**으로 모았다 (`AUTHORING_ROW` · FR-374).

    이전에는 자연어 입력칸이 버튼 줄 **위**에 따로 있고 녹화 시작은 버튼 줄 **안**에
    섞여 있었다. 같은 일을 하는 두 길이 다른 무게로 놓이면 사용자는 한쪽을 「주된 방법」
    으로 읽는다 — 그것이 사용자 보고 3번의 절반이다.
  */
  "step.addAssertion",
  "step.insertManual",
  "step.moveUp",
  "step.moveDown",
  "step.delete",
  /*
    011 복수 삭제 (FR-382·FR-383). **`step.delete` 바로 뒤다** — 셋이 같은 종류의 일이므로
    묶여 있어야 하고, 순서가 「하나 → 고른 것 → 이 뒤 전부」로 범위가 넓어지는 차례여야
    사용자가 무엇을 누르는지 헷갈리지 않는다.

    행마다의 체크(`step.toggleDeleteTarget`)와 전부 고르기는 여기 없다 — 그것들의 집은
    Step 행과 패널 머리다 (007 계약 §2-7).
  */
  "step.deleteSelected",
  "step.deleteAfter",
  "run.fromHere",
  "browser.openAt",
  "ai.start",
  "save.overwriteStale",
];
/**
 * Step 을 더하는 두 길이 나란히 서는 줄 (011 FR-374).
 *
 * 자연어 입력칸 바로 아래다. `PALETTE_ACTIONS` 에서 뽑아낸 이유는 자리이지 성격이
 * 아니다 — 같은 묶음에 있어야 대등하게 읽힌다.
 */
const AUTHORING_ROW: ActionId[] = ["step.recordStart", "step.recordStop"];

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
  /*
    **테스트 이름은 이 팔레트가 받지 않는다** (011). 국면 띠가 표시와 편집을 함께 갖고,
    화면은 `Workbench` 의 `phaseName` 으로 그것을 넘긴다 (UC-011-2). 여기 다시 받으면
    같은 값에 자리가 둘이 된다.
  */
  /** 시작 주소 (`test.setStartUrl`) */
  startUrl: string;
  onStartUrlChange: (v: string) => void;
  /** AI 지시문 (`ai.compose`). 기록이며 국면에 따라 읽기 전용이다 (FR-063) */
  instruction: string | null;
  onInstructionChange?: (v: string) => void;
  /*
    **저장 버튼도 이 팔레트가 받지 않는다** (011). 라벨과 좁힌 권한은 국면 띠의 저장
    조작이 갖는다 — 화면이 `phaseActions` 로 만들어 넘긴다 (007 계약 §2-7).
  */
  /**
   * 저장 성공 확인줄 (005 FR-154·FR-158).
   *
   * **조작이 아니라 결과 보고이므로 여기 남는다.** 무엇이 저장됐는지는 Step 목록을
   * 보면서 확인하는 사실이고, 국면 띠 48px 한 줄은 그 문장을 담을 수 없다.
   */
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
  startUrl,
  onStartUrlChange,
  instruction,
  onInstructionChange,
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
  /*
    그 조작을 이 자리에 그리는가.

    **좁힌 뒤의 상태를 본다** (`capabilityOf`, 이전에는 `capabilities[action]` 이었다).
    화면이 좁혀 붙이는 사유(「먼저 Step 을 고르세요」)는 `keep` 이고, 표가 「이 상태의
    조작이 아니다」로 정한 것은 `hide` 다. 좁히기 전의 상태를 보면 그 둘이 갈리지 않는다.
  */
  const shown = (action: ActionId) => isShown(capabilityOf(action)) && !hidden.includes(action);

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
    <div className="flex flex-col gap-s3">
      <div className="font-mono text-[11px] font-semibold leading-none tracking-[.08em] uppercase text-ink-3">지금 할 수 있는 것</div>

      {/*
        ─── Step 을 더하는 두 길 (011 FR-374 · UC-011-23) ──────────────────────

        **같은 묶음, 같은 무게다.** 지시문은 입력칸 + 버튼이고 녹화는 버튼 하나라 모양이
        다를 수밖에 없지만, 자리가 붙어 있고 버튼이 같은 `compact` 형이면 둘 중 하나가
        「주된 방법」으로 읽히지 않는다.

        011 이전에는 입력칸이 버튼 줄 **위**에 따로 있고 녹화 시작은 버튼 줄 **안**에
        다른 조작들과 섞여 있었다. 사용자 보고: 「스텝을 새로 녹화하는것처럼, ai
        지시문으로도 스텝을 추가할 수 있어야한다」.

        쓸 수 없으면 입력칸을 잠그고 이유는 버튼이 말한다 (FR-234).
      */}
      {AUTHORING_ROW.some(shown) || shown("step.addNaturalLanguage") ? (
        <div className="flex flex-col gap-s2">
          {shown("step.addNaturalLanguage") && (
            <div className="flex gap-[10px] items-start">
              <input
                aria-label="자연어로 Step 추가"
                value={nl.value}
                disabled={!usable("step.addNaturalLanguage")}
                onChange={(e) => nl.onChange(e.target.value)}
                placeholder="생성된 프로젝트가 목록에 있는지 확인해."
                className="border-ai flex-1 min-w-0"
              />
              {button("step.addNaturalLanguage", () => {
                if (nl.value.trim() === "") return;
                nl.onSubmit();
              })}
            </div>
          )}
          <div className="flex flex-wrap gap-[10px] items-start">
            {AUTHORING_ROW.filter(shown).map((action) => button(action, () => onRun(action)))}
          </div>
        </div>
      ) : null}

      <div className="flex flex-wrap gap-[10px] items-start">
        {PALETTE_ACTIONS.filter(shown).map((action) => button(action, () => onRun(action)))}
      </div>

      {/*
        009 — 삽입 입력면. **닫혀 있으면 자리를 차지하지 않는다** (008 FR-218e 와 같은
        규칙) — 빈 영역이 남아 다른 영역의 자리를 바꾸지 않는다.
      */}
      {insert?.open === true && insert.form}

      {/*
        ─── 테스트 속성 (FR-247 — 통합으로 사라지는 조작이 없다) ─────────────────

        **`test.rename` 은 011 에서 빠졌다.** 이름은 국면 띠가 이미 표시하고 있었고,
        여기에도 입력칸이 있어 같은 값에 자리가 둘이었다. 011 이 표시와 편집을 국면 띠
        하나로 합쳤다 (UC-011-2).
      */}
      {shown("test.setStartUrl") && (
        <div
          className="border-t border-hair flex flex-col gap-s2 pt-s3"
        >
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

      {/*
        ─── 저장은 여기 없다 (011) ────────────────────────────────────────────

        `save`·`edits.revert` 의 집은 **국면 띠**다 (007 계약 §2-7 · 011 UC-011-1).
        여기 다시 그리면 같은 조작이 두 자리를 갖고, `CapabilityUI` 의 「한 조작에 한
        자리」와 `LabelUniqueness` 가 함께 잡는다.

        `save.overwriteStale` 도 여기 없다. 그것은 **두 선택 중 하나**이고(FR-209), 다른
        하나(「바뀐 내용으로 다시 읽기」)와 나란히 있어야 무엇을 버리는지 고를 수 있다.
        그 짝의 집은 국면 보조 영역의 충돌 블록이다.

        저장 확인줄(`saveNotice`)은 **남는다.** 그것은 조작이 아니라 결과 보고이고, 자리는
        Step 목록 곁이 맞다 — 무엇이 저장됐는지는 목록을 보면서 확인하는 사실이다.
      */}
      {saveNotice}

      {stepCount === 0 && emptyHint !== undefined && (
        <div className="font-sans text-[11px] leading-[1.4] font-normal text-ink-3">{emptyHint}</div>
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
  // 「이 상태의 조작이 아니다」는 그리지 않는다 (2026-09-09 · `capabilities.ts`).
  if (capability.kind === "disabled" && capability.visibility === "hide") return null;
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
    <div className="flex flex-col gap-s1">
      <div className="flex items-center gap-s2">
        <span className="font-sans text-[12px] leading-none font-normal text-ink-3 w-[76px]">
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
          className="font-sans text-[11px] leading-[1.4] font-normal text-ink-3 pl-[84px]"
        >
          {capability.reason}
          {capability.remedy !== null && (
            <>
              {" "}
              <button
                type="button"
                data-remedy-for={action}
                className="border-0 p-0 h-auto bg-transparent shadow-none text-run font-sans text-[12px] font-semibold leading-[1.4] underline cursor-pointer"
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
