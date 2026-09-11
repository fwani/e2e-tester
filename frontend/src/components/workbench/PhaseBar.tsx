/**
 * 층② 국면 띠 (007 T019 · FR-218d·FR-219 · 48px).
 *
 * 담는 것은 넷이고 **순서가 고정이다** — 국면 표시 → 테스트 이름 → 진행 → 결말 요약 →
 * 그 국면의 주요 조작.
 *
 * **결말 요약은 이 띠에만 있다** (FR-218d · 005 FR-140). 이전에는 결과 화면과 세션 화면이
 * 같은 문장을 각자 만들어 나란히 그렸고, 사용자는 어느 것이 지금 실행인지 알 수 없었다
 * (U-19). `data-run-summary` 로 표시해 화면에 하나뿐임을 검사가 셀 수 있게 한다.
 *
 * ## 2026-09-08 (008)
 *
 * 이전 판은 국면 표시를 **채운 색 상자**로 그렸다 — 결말 색을 배경으로 깔고 흰 글자를
 * 얹었다. v2 는 색을 상태에만 쓰되 **채우지 않는다**: 옅은 바탕 + 같은 계열 테두리 +
 * 같은 계열 글자다 (`.chip` 과 그 변형). 색이 화면을 지배하지 않으면서 상태는 그대로
 * 읽힌다. 띠 자체도 `#F2F4F7` 바탕 + 잉크 테두리에서 정본의 `.phase` 로 옮겼다.
 *
 * ## 2026-09-10 (011) — 이 띠가 저장의 집이 됐다
 *
 * 사용자 보고: 「테스트를 저장하는 버튼과 이름을 지정하는게 오른쪽 아래에 존재하는데,
 * ux 적으로 매우 불편함」. 저장은 작성 흐름의 종착점인데 그 자리가 우측 460px 패널
 * 바닥 — Step 목록을 다 지난 곳 — 이었다. 저장을 못 찾아 나가면 기록이 사라진다.
 *
 * 이 띠로 온 이유는 둘이다. 여기는 이미 **주요 조작**(`run.*`)이 사는 자리이고,
 * **테스트 이름을 표시하는** 자리이기도 하다. 두 번째가 특히 중요하다 — 이름이 보이는
 * 곳에서 바로 고치면 같은 값에 입력칸이 둘 생기지 않는다 (UC-011-2). 011 이전에는 이름이
 * 화면에 두 번 있었다: 여기의 표시와 팔레트의 입력칸.
 *
 * 그래서 이 파일이 더한 것은 **`rename`** 하나다. 저장 버튼 자체는 `actions` 로 들어온다 —
 * 국면 어댑터가 만들고 이 컴포넌트는 자리만 준다. 표시와 소유를 나눈 007 의 배치를
 * 그대로 따른다.
 */
import type { ReactNode } from "react";

import type { ActionId } from "../../lib/actions";
import type { CapabilityState } from "../../lib/capabilities";
import { ACTION_LABEL } from "../../lib/wording";
import { chipToneForTone } from "../../theme/tone";
import type { PhaseBar as PhaseBarModel } from "./model";
import { Chip } from "../../ui/Chip";
/**
 * 이름을 그 자리에서 고치는 데 필요한 것 (011 · `test.rename`).
 *
 * **주지 않으면 표시만 한다.** 이름을 고칠 수 없는 자리(만들기 국면처럼 아직 대상이
 * 없는 곳)에서 입력칸을 그리지 않기 위한 것이 아니라 — 그런 곳도 자리는 남긴다
 * (FR-234) — 이 컴포넌트를 쓰는 다른 맥락이 생겼을 때 표시 전용으로 쓸 수 있게 하는
 * 여지다.
 */
export interface PhaseNameEdit {
  capability: CapabilityState;
  onChange: (value: string) => void;
  onRemedy: (action: ActionId) => void;
  /**
   * 이름 **옆에** 오는 저장 상태 (011 · 「초안」·「저장됨」·「저장하지 않은 변경 있음」).
   *
   * **이름 안에 넣지 않는다.** 011 이전에는 한 문장이었다 — 「TC-001 · 저장됨」. 이름
   * 자리가 입력칸이 되면 그 문장이 그대로 저장 이름이 된다.
   */
  status?: ReactNode;
}
/**
 * 저장할 그룹 (013 FR-443 · converge T062).
 *
 * **이름 옆에 둔다.** 이름과 그룹은 「이 테스트가 무엇으로 저장되는가」를 함께 정하고,
 * 그룹은 식별자에 들어가므로(`USER-001`) 저장 시점에 정해져야 한다.
 *
 * **아직 저장되지 않은 세션에만** 준다. 이미 저장된 테스트의 그룹을 바꾸는 것은 파일과
 * 실행 산출물을 옮기는 일이고, `POST /api/tests:move` 가 원자성 규약과 함께 그것을 한다 —
 * 저장에 자산 이동을 숨기지 않는다.
 */
export interface PhaseGroupPick {
  options: { prefix: string; name: string }[];
  /** 고른 접두어. `null` 이면 그룹 없음 (`TC-###`). */
  value: string | null;
  onChange: (prefix: string | null) => void;
}

export interface PhaseBarProps {
  bar: PhaseBarModel;
  testName: string;
  /** 이름을 그 자리에서 고친다 (011 UC-011-2). 없으면 읽기 전용 표시 */
  rename?: PhaseNameEdit;
  /** 저장할 그룹 (013 FR-443). 고를 그룹이 없으면 주지 않는다 — 자리를 뺏지 않는다 */
  group?: PhaseGroupPick;
  /** 그 국면의 주요 조작. 오른쪽에 온다 */
  actions: ReactNode;
}

export function PhaseBar({ bar, testName, rename, group, actions }: PhaseBarProps) {
  return (
 <div data-workbench-phase-bar className="h-phase flex items-center gap-s3 px-s4 bg-panel border-b border-hair-2 flex-[0_0_48px]">
      {/*
        국면 표시. **화면에 하나뿐이다** (FR-219). 색만으로 국면을 알리지 않으므로 라벨이
        항상 텍스트로 있다 (ui-contract §7). 어느 변형인지는 `theme/tone.ts` 가 정한다 —
        화면이 결말을 스스로 가르면 중지가 실패로 보인다 (U-03).
      */}
      <Chip data-phase-pill tone={chipToneForTone(bar.phaseTone)} layout="h-[22px] flex-none">
        {bar.phaseLabel}
      </Chip>

      <PhaseTestName testName={testName} rename={rename} />

      {/*
        013 FR-443 — 그룹을 이름 옆에서 고른다. **그룹이 하나도 없으면 그리지 않는다**
        (SC-627): 그룹을 쓰지 않는 사용자에게 새 칸을 강요하지 않는다.
      */}
      {group !== undefined && group.options.length > 0 && (
        <select
          data-phase-group
          aria-label="저장할 그룹"
          value={group.value ?? ""}
          onChange={(e) => group.onChange(e.target.value === "" ? null : e.target.value)}
          className="m-0 flex-none max-w-[160px]"
        >
          <option value="">그룹 없음</option>
          {group.options.map((g) => (
            <option key={g.prefix} value={g.prefix}>
              {g.name}
            </option>
          ))}
        </select>
      )}

      {bar.progressLabel !== null && (
        <div className="font-sans text-[12px] leading-none font-normal text-ink-3 flex-none">
          {bar.progressLabel}
        </div>
      )}

      {/*
        결말 요약 — **이 자리 하나뿐이다** (FR-218d · 005 FR-140 · U-19).

        **한 줄로만 그린다** (사용자 보고 · 2026-09-09). 이 칸은 남는 폭을 가져가는
        자리이고 `minWidth: 0` 이라 줄일 수 있는데, 줄 바꿈을 허용해 두면 폭이 모자랄 때
        폭 0 까지 찌그러진 채 **글자 하나씩 세로로 쌓인다** — 실제로 그 화면이 나왔다.
        말줄임이면 좁아져도 읽히는 만큼은 읽히고, 폭을 되찾으면 그대로 돌아온다.
      */}
      {bar.runSummary !== null && (
        <div
          data-run-summary
          className="font-sans text-[13px] leading-[1.4] font-normal flex-1 min-w-0 whitespace-nowrap overflow-hidden text-ellipsis"
          title={typeof bar.runSummary === "string" ? bar.runSummary : undefined}
        >
          {bar.runSummary}
        </div>
      )}

      {bar.runSummary === null && <div className="flex-1" />}

      {/*
        조작 묶음. **줄어들 수 있어야 한다** (`0 1 auto` · `minWidth: 0`).

        `0 0 auto` 였을 때, 여러 조작이 동시에 잠겨 이유 문구가 나란히 붙으면 이 묶음이
        제 내용 폭을 끝까지 요구했고 띠가 창 밖으로 밀려났다. 줄어드는 몫은 이유 문구가
        받는다 — 버튼과 해소 수단은 `ActionButton` 이 `0 0 auto` 로 지킨다.

        011 이 여기에 저장·되돌리기를 더했다. 같은 위험이 커지므로 규칙은 그대로 유지한다.
      */}
      {/* 조작 묶음 — 검사가 이 자리를 찾는 표식이다 (015: `.row` 셀렉터를 대체). */}
      <div data-phase-actions className="flex items-center gap-s2 flex-initial min-w-0">
        {actions}
      </div>
    </div>
  );
}
/**
 * 테스트 이름 — **표시와 편집이 같은 자리다** (011 UC-011-2).
 *
 * `data-phase-test-name` 은 검사가 「이름을 보여주는 자리와 고치는 자리가 하나인가」를
 * 셀 수 있게 하는 표식이다. 좌표나 CSS 가 아니라 영역으로 재면 배치가 바뀌어도 같은
 * 질문이 성립한다.
 */
function PhaseTestName({
  testName,
  rename,
}: {
  testName: string;
  rename?: PhaseNameEdit;
}) {
  /*
    `not_applicable` 이면 고칠 수 없는 것이 아니라 **그 국면에 그 조작이 없는** 것이다.
    이름 자체는 여전히 보여야 하므로 읽기 전용 표시로 떨어진다 — 자리를 없애면 「이
    화면에는 원래 이름이 없는 것」과 구별되지 않는다.
  */
  if (rename === undefined || rename.capability.kind === "not_applicable") {
    return (
      <div
        data-phase-test-name
        className="font-sans text-[17px] font-bold leading-none whitespace-nowrap overflow-hidden text-ellipsis max-w-[300px] min-w-0"
        title={testName}
      >
        {testName}
      </div>
    );
  }

  const disabled = rename.capability.kind === "disabled";
  const remedy = rename.capability.kind === "disabled" ? rename.capability.remedy : null;
  const reasonId = "reason-test.rename";

  return (
    <div
      data-phase-test-name
      className="flex items-center gap-s2 max-w-[420px] min-w-0"
    >
      <input
        data-action="test.rename"
        aria-label={ACTION_LABEL["test.rename"]}
        /*
          정본 `input.phase-name` 이 주던 것을 함께 옮긴다 (015 L2 대조가 잡았다).
          이것이 없으면 전역 `input{}` 규칙이 이겨 **이름 칸이 32px 짜리 회색 테두리
          입력칸으로 보인다** — 띠 안에서 제목처럼 보이던 것이 폼 칸이 된다.
          초점 표시는 테두리와 바탕으로 한다 (정본이 `outline:none` 으로 정한 자리이며
          `theme/exceptions.ts` 에 등록돼 있다).
        */
        className="font-sans text-[17px] font-bold leading-none whitespace-nowrap overflow-hidden text-ellipsis flex-initial min-w-0 max-w-[300px] w-auto min-h-[26px] px-[6px] border border-transparent bg-transparent text-ink enabled:hover:border-hair-2 focus:border-hair-2 focus:bg-panel focus:outline-none disabled:border-transparent disabled:text-ink-2"
        value={testName}
        disabled={disabled}
        maxLength={200}
        placeholder={ACTION_LABEL["test.rename"]}
        aria-describedby={disabled ? reasonId : undefined}
        title={testName}
        onChange={(e) => rename.onChange(e.target.value)}
      />
      {/*
        015 T073 — 여기서 칩 모양을 손으로 조립하고 있었다. 같은 종류의 표식이 화면마다
        다른 조합을 얻는 것이 SC-010 이 막으려는 것이므로 부품으로 되돌린다.
      */}
      {rename.status !== undefined && rename.status !== null && (
        <Chip data-phase-save-state layout="flex-[0_0_auto]">
          {rename.status}
        </Chip>
      )}
      {/*
        잠긴 이유 — **`ActionButton` 과 같은 구조를 쓴다** (`flex: 0 1 auto` · `minWidth: 0`
        · `maxWidth: 260` · 안쪽 텍스트만 말줄임).

        띠에서 줄어드는 몫은 이유 문구가 받는다 (`PhaseBarWidth` 검사). 폭 상한이 없으면
        긴 사유가 제 내용 폭을 요구해 조작이 화면 밖으로 밀려난다 — 실제로 그 화면이
        보고됐다. 해소 수단은 `0 0 auto` 로 지켜, 말줄임에 잘리지 않는다 (계약 §4-1 의 3번).
      */}
      {disabled && (
        <span
          id={reasonId}
          data-disabled-reason="test.rename"
          className="font-sans text-[11px] leading-[1.4] font-normal text-ink-3 inline-flex items-center gap-s1 flex-initial min-w-0 max-w-[260px]"
        >
          <span
            data-disabled-reason-text
            title={rename.capability.kind === "disabled" ? rename.capability.reason : undefined}
            className="min-w-0 overflow-hidden text-ellipsis whitespace-nowrap"
          >
            {rename.capability.kind === "disabled" ? rename.capability.reason : ""}
          </span>
          {remedy !== null && (
            <button
              type="button"
              data-remedy-for="test.rename"
              className="border-0 p-0 h-auto bg-transparent shadow-none text-run font-sans text-[12px] font-semibold leading-[1.4] underline cursor-pointer flex-none"
              onClick={() => rename.onRemedy(remedy.action)}
            >
              {ACTION_LABEL[remedy.action]}
            </button>
          )}
        </span>
      )}
    </div>
  );
}
