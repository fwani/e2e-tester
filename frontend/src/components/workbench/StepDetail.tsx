/**
 * **단일 Step 상세** (007 T022 · FR-229·FR-230·FR-231).
 *
 * 이 파일이 생기기 전 Step 상세를 그리는 구현이 **2벌**이었다.
 *
 *   `pages/StepInspector.tsx`         ← 세션 화면이 겹침으로 띄운다 (640×1140)
 *   `pages/TestDefinition.tsx:633`    ← 편집 화면이 목록 아래 인라인으로 편다
 *
 * 같은 Step 을 보는데 국면에 따라 **열리는 자리**가 달랐다 (S-05). 007 은 하나로 합치고
 * 자리를 고정한다 — 우측에서 겹치는 640px 이며 일곱 국면 전부에서 같다 (FR-230).
 *
 * **`attempts` 와 `candidates` 를 둘 다 갖는다.** 결과 국면에서 사용자가 알아야 하는 것은
 * "정의에 무엇이 있는가" 가 아니라 "그때 무엇을 시도했고 왜 못 찾았는가" 다. 편집
 * 국면에서는 반대다. 한 칸에 뭉개면 국면에 따라 같은 자리가 다른 뜻을 갖는다.
 *
 * **조작 가능 여부는 스스로 판단하지 않는다** — `capabilities` 를 받아 그대로 따른다
 * (UC-000). 이전에는 편집 화면과 세션 화면이 각자 판단했고, 그래서 편집 화면은 "실행을
 * 시작해 일시정지한 뒤 하세요" 라고 안내하면서 그리로 가는 버튼을 주지 않았다 (006 E-03).
 *
 * ## 2026-09-08 (008)
 *
 * 형태는 정본이 갖는다. 이 화면이 검정 바탕 머리 띠를 **두 곳**(패널 머리 · 시도한
 * locator 표 머리)에 갖고 있었는데, 640px 판 안에서 잉크 띠 둘은 내용보다 무겁다.
 * 둘 다 옅은 우물(`.pane-hd`)로 내렸다 — 색은 상태에만 쓴다.
 */
import { useEffect, useState, type ReactNode } from "react";

import type { RepickSlot } from "../../api/client";
import { InlineSecretInput, referenceName } from "../InlineSecretInput";
import { LocatorPriorityTable } from "../LocatorPriorityTable";
import { isShown, type CapabilityMap } from "../../lib/capabilities";
import {
  CLEAR_MISMATCH_HINT,
  CLEAR_MISMATCH_LABEL,
  EXPECTED_LABEL,
  MISMATCH_HINT,
  MISSING_SHOT_REASON,
  OBSERVED_LABEL,
  OBSERVED_TRUNCATED,
  SENSITIVE_NO_VALUE,
  assertionSummary,
  stepNumber,
  uploadFileNote,
} from "../../lib/wording";
import type { Step } from "../../types/generated/step";
import { ActionButton } from "./ActionButton";
import type { StepDetail as StepDetailModel } from "./model";

import { Button } from "../../ui/Button";
import { Chip } from "../../ui/Chip";
import { Checkbox } from "../../ui/Checkbox";
import { Input } from "../../ui/Input";
import { StepEditFields } from "../StepEditFields";
import { DetailPanel, DetailPanelTitle } from "../../ui/OverlayPane";
import { Disclosure } from "../../ui/Disclosure";
import { Tooltip } from "../../ui/Tooltip";
/** 값이 `{{변수명}}` 참조인가. 민감 값은 참조로만 저장된다 (FR-082). */
function isReference(value: string): boolean {
  return /^\{\{[A-Z][A-Z0-9_]*\}\}$/.test(value);
}

function hasValue(step: Step): step is Extract<Step, { value: string }> {
  return step.type === "fill" || step.type === "select";
}
/**
 * 파일 이름을 갖는 Step 인가 (2026-09-09 · `upload`).
 *
 * **`hasValue` 와 갈라 둔다.** `upload` 는 `value` 필드를 갖지 않고 `file_name` 을 갖는다.
 * 한 칸으로 뭉개면 서버로 보내는 필드가 갈리고(`value` vs `file_name`), 서버는 「입력값을
 * 갖지 않는 Step 에 값을 지정했다」로 거절한다.
 */
function hasFileName(step: Step): step is Extract<Step, { file_name: string }> {
  return step.type === "upload";
}
/** 저장된 정의 그대로의 미리보기 (FR-016). 파일 내용과 일치해야 한다. */
function dslPreview(step: Step): string {
  return JSON.stringify(step, null, 2);
}

export interface StepDetailProps {
  detail: StepDetailModel;
  capabilities: CapabilityMap;
  /**
   * 그 Step 이 끝난 시점의 화면 (011 UC-011-20·21).
   *
   * **주지 않으면 그 판을 그리지 않는다.** 결과 국면에만 있는 것이고, 다른 국면에서 빈
   * 판을 그리면 「여기도 화면이 남는다」로 읽힌다.
   *
   * `url` 이 `null` 이면 없다는 뜻이고 `note` 가 그 사유다 — 둘 중 하나는 반드시 있다.
   */
  shot?: { url: string | null; note: string };
  /**
   * 이 컴포넌트가 **자기 편집 입력을 갖는가** (008).
   *
   * 기본은 갖는다 — 세션 국면들은 여기가 유일한 편집면이고, 지역 상태에 모아 두었다가
   * 「저장」으로 한 번에 넘긴다.
   *
   * 편집 국면은 다르다. 그 국면은 `extraFields` 로 **입력할 때마다 변경 연산을 쌓는**
   * 편집면을 넣는다 (006 FR-188~FR-190 — 변경 건수가 실시간으로 는다). 둘을 함께 그리면
   * 같은 값에 입력칸이 둘 생기고, 커밋 방식이 다른 둘이 한 화면에 놓인다.
   *
   * FR-231 은 국면에 따라 **읽기·편집을 전환**하는 것을 허용한다. 항목의 순서는 그대로다.
   */
  /**
   * 027 — 민감 변수 이름. **안내 문구를 고르는 데** 쓴다.
   *
   * 화면이 알면 주고 모르면 빈 배열이다 — 참조가 읽기 전용인 것은 이 값과 무관하므로
   * 모른다고 편집이 열리지 않는다 (`StepEditFields`).
   */
  sensitiveNames?: string[];
  /**
   * 027 FR-004 — **입력이 즉시 반영되어야 하는 화면**이 쓰는 통로.
   *
   * 편집 화면은 입력할 때마다 편집 연산을 쌓는다 (006 FR-189 의 변경 건수가 사람이 센
   * 것과 맞아야 한다). 이 화면은 로컬에 모았다가 「저장」으로 한 번에 보낸다.
   *
   * **저장 방식의 차이는 화면의 것이고, 편집면은 하나다.**
   */
  onFieldChange?: (patch: {
    label?: string;
    value?: string;
    timeout_ms?: number;
    tab?: number;
    url?: string;
    assertion_value?: string;
    file_name?: string;
  }) => void;
  busy?: boolean;
  onSave: (patch: {
    label?: string;
    value?: string;
    timeout_ms?: number;
    sensitive?: boolean;
    tab?: number;
    url?: string;
    assertion_value?: string;
    /** 올릴 파일의 이름 — `upload` Step 만 갖는다 (2026-09-09) */
    file_name?: string;
  }) => void;
  onRepick: (slot: RepickSlot) => void;
  onClose: () => void;
  /** 비활성 조작의 해소 방법을 눌렀을 때 */
  onRemedy?: (action: keyof CapabilityMap) => void;
  /**
   * 편집 국면의 나머지 필드 (`tab`·`url`·`assertion_value`)와 잠긴 대상의 이유.
   *
   * 세션 국면에는 이 필드들이 없다 — 세션의 편집 경로(`PATCH …/steps/{id}`)가 다루지
   * 않기 때문이다. 그래서 **국면이 주는 자리**로 두고, 그리는 규칙은 여전히 하나다
   * (FR-230: 상세는 어느 국면에서나 같은 자리·같은 구성).
   */
  extraFields?: ReactNode;

  /**
   * 어긋남 표시를 걷어낸다 (020 FR-027).
   *
   * **없으면 조작을 그리지 않는다.** 결과 국면처럼 정의를 고칠 수 없는 자리에서는
   * 걷어내기가 성립하지 않고, 그때 눌리지 않는 단추를 두면 사용자가 왜 안 되는지
   * 묻게 된다 (`ownFields` 와 같은 판단).
   */
  onClearMismatch?: () => void;
}

export function StepDetail({
  detail,
  capabilities,
  shot,
  sensitiveNames = [],
  onFieldChange,
  busy = false,
  onSave,
  onRepick,
  onClose,
  onRemedy,
  extraFields,
  onClearMismatch,
}: StepDetailProps) {
  const step = detail.step;
  /**
   * 그 화면 파일이 실제로는 없었다 (011 FR-396b).
   *
   * 결과 파일에 경로가 있어도 파일은 사라졌을 수 있다 — 보관이 테스트당 최근 1회분이므로,
   * 지난 실행의 결과를 열면 그 화면은 이미 이번 실행이 지웠다.
   *
   * **지목이 바뀌면 되돌린다.** 한 Step 에서 깨졌다고 다음 Step 까지 없는 것으로 두면,
   * 있는 화면을 보여 주지 못한다.
   */
  const [shotBroken, setShotBroken] = useState(false);
  useEffect(() => setShotBroken(false), [shot?.url]);
  const [label, setLabel] = useState(step?.label ?? "");
  const [value, setValue] = useState(step && hasValue(step) ? step.value : "");
  const [fileName, setFileName] = useState(step && hasFileName(step) ? step.file_name : "");
  const [timeoutMs, setTimeoutMs] = useState(step?.timeout_ms ?? 5000);
  const [sensitive, setSensitive] = useState(false);
  const [showDsl, setShowDsl] = useState(false);
  const [secretOpen, setSecretOpen] = useState(false);
  // 다른 Step 을 고르면 입력값을 그 Step 기준으로 다시 잡는다.
  useEffect(() => {
    setLabel(step?.label ?? "");
    setValue(step && hasValue(step) ? step.value : "");
    setFileName(step && hasFileName(step) ? step.file_name : "");
    setTimeoutMs(step?.timeout_ms ?? 5000);
    setSensitive(false);
    setSecretOpen(false);
  }, [step]);

  const canEdit = capabilities["step.update"].kind === "enabled";
  const canMarkSensitive = capabilities["step.markSensitive"].kind === "enabled";
  const hasValueField = step !== null && hasValue(step);
  const hasFileField = step !== null && hasFileName(step);
  const alreadyReference = hasValueField && isReference(value);

  /**
   * 027 — **로컬 상태를 얹은 Step.**
   *
   * `StepEditFields` 는 상태를 갖지 않고 `step` 에서 읽어 그린다. 이 화면은 입력을
   * 로컬에 모았다가 「저장」으로 보내므로, 모아 둔 값을 얹은 Step 을 넘긴다.
   */
  const draftStep =
    step === null
      ? null
      : ({
          ...step,
          label,
          ...(hasValueField ? { value } : {}),
          ...(hasFileField ? { file_name: fileName } : {}),
          timeout_ms: timeoutMs,
        } as typeof step);

  /** 편집면이 알린 변경을 로컬 상태에 반영하고, 원하면 화면에도 즉시 알린다 */
  const applyFieldChange = (patch: Parameters<NonNullable<typeof onFieldChange>>[0]) => {
    if (patch.label !== undefined) setLabel(patch.label);
    if (patch.value !== undefined) setValue(patch.value);
    if (patch.file_name !== undefined) setFileName(patch.file_name);
    if (patch.timeout_ms !== undefined) setTimeoutMs(patch.timeout_ms);
    onFieldChange?.(patch);
  };

  /**
   * 020 — 어긋남은 **검증 Step 에만** 있다 (도메인이 그렇게 정했다).
   *
   * 판별 유니온을 좁혀서 읽는다. `getattr` 식으로 물으면 타입이 넓어지고, 넓어진
   * 타입은 다른 Step 종류에 이 칸이 생길 수 있다는 잘못된 신호를 준다.
   *
   * **`?? null` 이 필요하다.** 생성된 타입은 이 칸을 필수로 표기하지만(직렬화 스키마의
   * 규칙), 020 이전 서버가 보낸 Step 에는 칸 자체가 없다 — 그때 값은 `null` 이 아니라
   * `undefined` 이고, `!== null` 만 보면 없는 기록을 그리려다 터진다.
   */
  const condition =
    step !== null && step.type === "assertion" ? step.assertion : null;
  const mismatch =
    step !== null && step.type === "assertion" ? (step.mismatch ?? null) : null;
  const expectedValue =
    step !== null && step.type === "assertion" ? (step.assertion.value ?? "") : "";

  return (
    <DetailPanel
      data-workbench-step-detail
      /*
        **대화상자다** — 역할이 dialog 이고, 열리면 초점이 판 안으로 가며, Esc 로 닫히고, 닫히면 연 자리로
        초점이 돌아간다. **모달은 아니다** (017 research R7) — 판을 연 채 목록의 다른 행을 누를 수 있어야
        하므로 초점을 가두지 않는다. 뒤의 미러를 막는 것은 `Workbench` 의 가림막이다 (010).

        2026-09-09 에 배치가 하나로 돌아오면서 `region` 갈래가 없어졌다. 인라인 배치가
        있던 동안에는 그것을 `region` 으로 두어야 했다 — 가리지 않는 것을 대화상자라고
        말하면 보조 기술이 "닫아야 뒤로 갈 수 있다" 고 잘못 안내한다.
      */
      onClose={onClose}
      // `w-detail` 은 `--w-detail`(640px) — 우측 고정 폭이며 모든 국면에서 같다 (FR-230).
      layout="w-detail flex flex-col overflow-y-auto"
    >
      <div
        className="bg-sunken border-b border-hair-2 text-ink-2 flex-[0_0_44px] flex items-center gap-s3 py-0 px-s4"
      >
        {/*
          머리 띠 문구는 두 배치에서 같다. 「STEP nn 편집」처럼 배치마다 다르게 쓰면
          그것은 껍데기가 아니라 **내용**이 갈리는 것이고, 가드가 그것을 잡는다
          (WorkbenchShell.test.tsx — 「배치는 껍데기만 바꾼다」). 번호와 종류는 바로
          아래 줄이 이미 말한다.
        */}
        <DetailPanelTitle>STEP 상세</DetailPanelTitle>
        <div className="flex-1" />
        {/* 017 T064 — 글자 없는 닫기의 이름을 포인터·초점에 보여 준다. 판이 열릴 때 초점은 판 자체로 가므로 저절로 뜨지 않는다. */}
        <Tooltip content="닫기" side="left">
        <Button /*
            011 UC-011-10 — 닫는 조작은 **상세 안에** 있고 모든 국면에서 같은 자리다.
            표식을 두는 이유: 011 이 상세를 대상 앱 위로 옮겼으므로, 닫을 방법이 판 안에
            있다는 것이 검사로 세져야 한다. 겹침이 미러를 덮은 채 닫을 수 없으면 사용자는
            조작 위치를 잃는다.
          */
          data-detail-close
          aria-label="닫기"
          size="icon" variant="quiet"
          onClick={onClose}
        >
          <svg width="16" height="16" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="2.4">
            <path d="M4 4l8 8M12 4l-8 8" />
          </svg>
        </Button>
        </Tooltip>
      </div>

      <div className="p-s4 flex flex-col gap-s4">
        <div className="flex flex-col gap-[10px]">
          <div className="flex items-center gap-[10px]">
            <div className="font-mono text-[12px] leading-none font-normal text-ink-3">{stepNumber(detail.index)}</div>
            {step !== null && (
              <>
                <Chip>{step.type.toUpperCase()}</Chip>
                <Chip tone={step.author === "ai" ? "ai" : "default"} layout="py-s2 px-s3">
                  {step.author === "ai" ? "AI" : "RECORD"}
                </Chip>
              </>
            )}
          </div>
          {/* 640px 안에서 혼자 서므로 크게 둔다 */}
          <div className="font-sans text-[20px] font-bold leading-[1.3]">
            {step?.label ?? "이 결과 이후 정의에서 사라진 Step"}
          </div>
        </div>

        {/*
          실패 사유 — 결과 국면에만 있다. 국면에 따라 자리가 달라지지 않게 상세의
          **항목 순서 안에** 둔다 (FR-231).
        */}
        {detail.failure !== null && (
          <div
            role="note"
            className="bg-fail-t border border-fail-line rounded-base font-sans text-[14px] leading-[1.4] font-normal text-fail py-s3 px-[14px]"
          >
            {detail.failure.message ?? "실패 이유가 기록되지 않았습니다."}
          </div>
        )}

        {/*
          **민감 값 지정의 자리는 값 칸 옆이다.** 값을 갖지 않는 Step 에서도 자리를
          비우지 않고 이유를 남긴다 (FR-234) — 비우면 사용자는 그 조작이 이 제품에
          없는 줄 안다.
        */}
        {step !== null && !hasValue(step) && isShown(capabilities["step.markSensitive"]) && (
          <span
            id="reason-step-sensitive"
            data-action="step.markSensitive"
            data-disabled-reason="step.markSensitive"
            className="font-sans text-[12px] leading-[1.4] font-normal text-ink-3"
          >
            {SENSITIVE_NO_VALUE}
          </span>
        )}

        {step === null ? (
          <p className="font-sans text-[14px] leading-[1.7] font-normal text-ink-2">
            이 실행에는 있었지만 지금 정의에는 없는 Step 입니다. 결말과 소요 시간은 그때의
            기록이고, 동작 종류·대상 요약·값은 보여줄 수 없습니다.
          </p>
        ) : (
          <>
            {/*
              027 FR-008 — **편집면은 하나다.**

              표시 이름·입력값·올릴 파일·대기 시간 칸이 각각 이 파일에 있었고, 편집
              화면은 그것을 끄고(`ownFields={false}`) 자기 것을 끼웠다. 편집면이 둘이면
              한쪽에 칸을 더할 때마다 다른 쪽에 없는 칸이 생기고, 사용자에게는 「이
              화면에서는 못 고치는 것」으로 보인다.

              **민감 값 지정과 안내는 아래에 남는다** — 그것은 편집칸이 아니라 이
              화면이 세운 조작이다.
            */}
            {draftStep !== null && (
              <StepEditFields
                step={draftStep}
                sensitiveNames={sensitiveNames}
                editable={canEdit}
                onChange={applyFieldChange}
              />
            )}

            {hasValueField && (
              <div>
                {/* 입력칸은 위 편집면이 그린다 (027). 여기 남는 것은 **민감 값 조작**이다 */}
                {alreadyReference ? (
                  <>
                    <p className="font-sans text-[12px] leading-[1.4] font-normal text-ink-3 mt-s1 mx-0 mb-0">
                      변수 참조입니다. 실제 값은 비밀 파일의 암호문에 있으며 화면에 표시되지
                      않습니다.
                    </p>
                  </>
                ) : (
 <label className="flex items-center gap-[6px] mt-[6px]">
                    <Checkbox
                      data-action="step.markSensitive"
                      aria-describedby={canMarkSensitive ? undefined : "reason-step-sensitive"}
                      checked={sensitive}
                      disabled={!canMarkSensitive}
                      onChange={(e) => setSensitive(e.target.checked)}
                    />
                    <span>
                      민감 값으로 지정 — 값을 변수 참조로 옮기고 봉인합니다 (되돌릴 수
                      없습니다)
                    </span>
                  </label>
                )}

                {/*
                  DR-023·SC-106 — 화면 이동 0회. 비밀 값을 이 자리에서 넣는다.

                  017 T065 — 단추가 ▸/▾ 글자를 바꿔 그리던 토글(참조일 때 「다시 넣기」 · 아닐 때 「여기서 넣기」 두 벌)을
                  `Disclosure` 하나로 모았다. 펼침 상태를 낭독기가 알고, 다른 Step 을 고르거나 봉인하면 접는다(`secretOpen`).
                  입력 칸은 **펼쳤을 때만** 그린다 — 접힌 채로 그리면 열지도 않은 Step 마다 등록된 변수 목록을 불러온다.
                */}
                {canMarkSensitive && (
                  <Disclosure
                    tone="action"
                    layout="mt-s1"
                    open={secretOpen}
                    onOpenChange={setSecretOpen}
                    summary={alreadyReference ? "비밀 값 다시 넣기" : "여기서 비밀 값 넣기"}
                  >
                    {secretOpen && (
                      <div className="mt-s2">
                        <InlineSecretInput
                          currentName={alreadyReference ? referenceName(value) : null}
                          busy={busy}
                          onLinked={(reference) => {
                            setValue(reference);
                            setSecretOpen(false);
                          }}
                        />
                      </div>
                    )}
                  </Disclosure>
                )}
              </div>
            )}

            {/*
              올릴 파일 (2026-09-09 사용자 보고 — 「파일의 확장자 기록되 되어야함」).

              **확장자를 따로 묻지 않는다.** 확장자는 이름의 일부이고, 둘을 따로 두면
              「보고서.xlsx 인데 확장자는 csv」인 Step 이 만들어질 수 있다. 아래 안내가
              지금 이름에서 읽히는 확장자를 그대로 보여 주므로, 사용자는 자기가 고친
              이름이 어떤 확장자로 올라가는지 확인할 수 있다.
            */}
            {hasFileField && (
              <div>
                {/* 이름 칸은 위 편집면이 그린다 (027). 여기 남는 것은 **확장자 안내**다 */}
                <p className="font-sans text-[12px] leading-[1.4] font-normal text-ink-3 mt-s1 mx-0 mb-0">
                  {uploadFileNote(fileName)}
                </p>
              </div>
            )}

            {/*
              021 FR-023 — **무엇을 검증하는지 먼저 말한다.**

              021 이전 상세는 기대값 편집 칸만 보였다. 목록에서 「텍스트가 `오류` 를
              포함하지 않음」을 읽고 상세를 열면 그 정보가 사라져, 편집하려고 연
              화면에서 무엇을 편집하는지 알 수 없었다.

              문구는 목록과 **같은 함수**에서 받는다. 상세가 자기 문구를 만들면 같은
              검증이 두 화면에서 다르게 불린다.
            */}
            {condition !== null && (
              <div data-field="assertion-condition">
                <label htmlFor="detail-condition">검증 조건</label>
                <Input
                  id="detail-condition"
                  value={assertionSummary(condition)}
                  disabled
                  readOnly
                />
              </div>
            )}

            {/*
              020 FR-015 — 어긋난 검증은 **기대값과 그때 화면을 나란히** 보여 준다.

              기대값만 보여 주면 사용자는 왜 결함 후보인지 알 수 없고, 관찰값만
              보여 주면 무엇을 요구했는지 알 수 없다. 둘이 같은 자리에 있어야
              「이 둘이 달랐다」가 한눈에 읽힌다.

              **여기서 민감값을 다시 거르지 않는다.** 관찰값은 저장 시점에 이미
              스크러버를 지났다 — 거르는 곳이 둘이면 어느 쪽이 기준인지 말할 수 없다.
            */}
            {mismatch !== null && (
              <div data-field="mismatch">
                <p className="font-sans text-[12px] leading-[1.4] font-normal text-ink-3 mt-0 mx-0 mb-s1">
                  {MISMATCH_HINT}
                </p>
                <label htmlFor="detail-expected">{EXPECTED_LABEL}</label>
                <Input id="detail-expected" value={expectedValue} disabled readOnly />
                <label htmlFor="detail-observed">{OBSERVED_LABEL}</label>
                <Input id="detail-observed" value={mismatch.observed} disabled readOnly />
                {mismatch.truncated && (
                  <p className="font-sans text-[12px] leading-[1.4] font-normal text-ink-3 mt-s1 mx-0 mb-0">
                    {OBSERVED_TRUNCATED}
                  </p>
                )}
                {onClearMismatch !== undefined && (
                  <>
                    <Button
                      type="button"
                      variant="ghost"
                      disabled={!canEdit}
                      onClick={onClearMismatch}
                    >
                      {CLEAR_MISMATCH_LABEL}
                    </Button>
                    <p className="font-sans text-[12px] leading-[1.4] font-normal text-ink-3 mt-s1 mx-0 mb-0">
                      {CLEAR_MISMATCH_HINT}
                    </p>
                  </>
                )}
              </div>
            )}

            {extraFields}


          </>
        )}

        {/*
          011 UC-011-20·21 — **그 Step 이 끝난 시점의 화면.**

          자리는 여기다. 새 영역을 만들지 않는다 — 사용자가 「몇 번째에서 무엇이 화면에
          있었는가」를 묻는 곳이 Step 상세이고, 그것을 위해 결과 국면에서 이 판을 연다.

          **시도한 locator 표 위에 온다.** 화면은 「무엇이 보였나」이고 표는 「왜 못 찾았나」
          라 순서가 그 차례다. 그리고 다른 표시를 밀어내지 않는다 (UC-011-22) — 판 자체가
          세로로 스크롤하므로 아래가 잘리지 않는다.

          **없으면 사유를 말한다.** 빈 채로 두면 사용자는 제품이 못 찍은 것인지 자기가 못
          볼 이유가 있는 것인지 알 수 없다.
        */}
        {shot !== undefined && (
          <div className="bg-panel border border-hair rounded-base" data-step-shot>
            <div className="bg-sunken border-b border-hair-2 text-ink-2 font-sans text-[12px] font-semibold leading-[1.4] text-ink-2 h-[36px] flex items-center py-0 px-s3">
              이 STEP 이 끝난 화면
            </div>
            {shot.url !== null && !shotBroken ? (
              <img
                data-step-shot-image
                src={shot.url}
                alt={`${stepNumber(detail.index)} 이 끝난 시점의 화면`}
                className="block w-full h-auto"
                /*
                  011 FR-396b — **파일이 사라졌을 수 있다.**

                  결과 파일에는 경로가 있는데 그 실행의 화면은 이후 실행이 지웠다
                  (보관은 테스트당 최근 1회분이다). 그대로 두면 깨진 이미지 아이콘이
                  뜨고, 그것은 제품이 고장난 것으로 읽힌다 — UX U-03 이 정확히 그
                  형태였다.

                  깨지면 사유로 바꾼다. 「없다」를 말할 수 있으면 깨진 그림을 보이지 않는다.
                */
                onError={() => setShotBroken(true)}
              />
            ) : (
              <div
                data-step-shot-missing
                className="font-sans text-[12px] leading-[1.4] font-normal text-ink-3 p-s3"
              >
                {shotBroken ? MISSING_SHOT_REASON.superseded : shot.note}
              </div>
            )}
          </div>
        )}

        {/*
          그 실행에서 **실제로 시도한** locator — 결과 국면. 정의의 후보와 다른 축이다.
          정의는 "무엇으로 찾을 계획인가" 이고 이것은 "무엇을 시도했고 몇 개가 맞았나" 다.
        */}
        {detail.attempts !== null && detail.attempts.length > 0 && (
          <div className="bg-panel border border-hair rounded-base">
            <div className="bg-sunken border-b border-hair-2 text-ink-2 font-sans text-[12px] font-semibold leading-[1.4] text-ink-2 h-[36px] flex items-center py-0 px-s3">
              시도한 LOCATOR (우선순위 순)
            </div>
            {detail.attempts.map((a, i) => (
              /*
                **머리 띠와 같은 좌우 여백을 준다** (2026-09-15 브라우저 확인). 전에는 여백이 없어 후보 이름과
                「맞음」이 판 테두리에 붙었고, 11px 글자가 줄 사이 간격 없이 붙어 표가 아니라 겹친 글처럼 읽혔다.
              */
              <div
                key={`${a.candidate}-${i}`}
                className={`flex items-center gap-s2 min-h-[28px] py-[6px] px-s3 border-t border-hair font-sans text-[12px] leading-[1.4] font-normal ${a.matched ? "text-ink-3" : "text-ink-2"}`}
              >
                <span className="font-bold w-[84px]">
                  {a.candidate}
                </span>
                <span className="flex-1 min-w-0 overflow-hidden text-ellipsis">
                  {a.expression}
                </span>
                <span className="w-[54px] text-right">{a.match_count}개</span>
                <span className="w-[62px] text-right">{a.waited_ms} ms</span>
                <span className="font-bold w-[44px] text-right">
                  {a.matched ? "맞음" : "아님"}
                </span>
              </div>
            ))}
          </div>
        )}

        {/*
          정의가 가진 후보와 적용 순서. **순서는 제품 전역의 고정 규칙이다** —
          Step 마다 바꾸지 않는다 (Principle IV · 006 FR-187).
        */}
        {detail.candidates !== null && (
          <LocatorPriorityTable
            target={detail.candidates}
            title={step?.type === "drag" ? "끄는 대상" : "대상 요소"}
            onRepick={
              capabilities["step.repick"].kind === "enabled" ? () => onRepick("target") : undefined
            }
            repicking={detail.repickWaiting === "target"}
            busy={busy}
          />
        )}

        {detail.dropCandidates !== null && (
          <LocatorPriorityTable
            target={detail.dropCandidates}
            title="놓는 위치"
            onRepick={
              capabilities["step.repick"].kind === "enabled"
                ? () => onRepick("drop_target")
                : undefined
            }
            repicking={detail.repickWaiting === "drop_target"}
            busy={busy}
          />
        )}

        {step !== null && (
          <Disclosure tone="action" open={showDsl} onOpenChange={setShowDsl} summary="테스트 DSL 미리보기">
            {showDsl && (
              <pre className="bg-ink text-panel rounded-base font-mono text-[12px] leading-[1.6] font-normal p-[10px] overflow-x-auto mt-[6px] mx-0 mb-0">
                {dslPreview(step)}
              </pre>
            )}
          </Disclosure>
        )}

        {/*
          조작은 **감추지 않는다.** 쓸 수 없으면 비활성으로 남고 이유와 해소 방법이
          붙는다 (FR-234). 「해당 없음」인 국면에서만 `ActionButton` 이 `null` 을 낸다.
        */}
        <div className="flex gap-[10px] flex-wrap">
          <ActionButton
            action="step.update"
            capability={capabilities["step.update"]}
            label="저장"
            emphasis
            onRemedy={onRemedy}
            onRun={() =>
              onSave({
                label: label.trim() !== "" ? label.trim() : undefined,
                value: hasValueField && !alreadyReference ? value : undefined,
                file_name: hasFileField && fileName.trim() !== "" ? fileName.trim() : undefined,
                timeout_ms: timeoutMs,
                sensitive: sensitive || undefined,
              })
            }
          />
          <ActionButton
            action="step.repick"
            capability={capabilities["step.repick"]}
            label="다시 집기"
            onRemedy={onRemedy}
            onRun={() => onRepick("target")}
            icon={
              <svg className="text-fail" width="15" height="15" viewBox="0 0 20 20">
                <circle cx="10" cy="10" r="5" fill="currentColor" />
              </svg>
            }
          />
        </div>
      </div>
    </DetailPanel>
  );
}
