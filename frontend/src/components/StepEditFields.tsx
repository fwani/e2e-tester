/**
 * Step 하나의 편집 가능한 필드 (006 T036 · FR-183).
 *
 * **판정하지 않는다.** 어느 Step 종류가 어느 필드를 갖는지는 생성된 타입(`step.d.ts`)에서
 * 오고, 최종 판정은 서버가 한다. 이 컴포넌트가 규칙을 스스로 정하면 편집 규칙의 두 번째
 * 구현이 생긴다 — 006 research R3 이 없애려던 것이 그것이다.
 *
 * **민감 참조 값은 읽기 전용이다** (FR-212·FR-213). 평문이 이 화면에 들어올 자리를 만들지
 * 않으면, 마스킹을 잊는 코드 경로가 생기지 않는다.
 *
 * 각 입력의 변경은 **하나의 `update` 연산**이 된다. 같은 Step 의 연속 편집은 부모가 하나로
 * 합친다 (FR-189 의 변경 건수가 사람이 센 것과 맞아야 한다).
 */
import type { Step } from "../types/generated/step";
import { SENSITIVE_VALUE_NOTICE } from "../lib/wording";

/** 이 Step 이 값을 갖는가. 생성된 타입의 판별자를 그대로 쓴다. */
function hasValue(step: Step): step is Extract<Step, { value: string }> {
  return step.type === "fill" || step.type === "select";
}

function isNavigate(step: Step): step is Extract<Step, { url: string }> {
  return step.type === "navigate";
}

/** 민감 값은 참조로만 저장된다 (FR-082). 참조는 그대로 보여도 안전하다. */
function isReference(value: string): boolean {
  return /^\{\{[A-Z][A-Z0-9_]*\}\}$/.test(value);
}

export interface StepEditFieldsProps {
  step: Step;
  /** 민감 변수 이름. 이 참조를 담은 값 칸은 읽기 전용이 된다. */
  sensitiveNames: string[];
  /** 편집 가능한가. 실행 중이면 거짓이다 (FR-206). */
  editable: boolean;
  onChange: (patch: {
    label?: string;
    value?: string;
    timeout_ms?: number;
    tab?: number;
    url?: string;
    assertion_value?: string;
  }) => void;
}

/** 한 줄의 배치 — 라벨 92px + 입력칸. 015 가 인라인에서 클래스로 옮겼다. */
const ROW_CLASS = "grid grid-cols-[92px_1fr] gap-s2 items-center mt-s2";

export function StepEditFields({
  step,
  sensitiveNames,
  editable,
  onChange,
}: StepEditFieldsProps) {
  const value = hasValue(step) ? step.value : null;
  const valueIsSecret =
    value !== null &&
    isReference(value) &&
    sensitiveNames.some((n) => value === `{{${n}}}`);

  return (
    <div>
      <label className={ROW_CLASS}>
        <span className="font-sans text-[12px] leading-none font-normal text-ink-3">
          표시 이름
        </span>
        <input
          aria-label="Step 표시 이름"
          value={step.label}
          disabled={!editable}
          maxLength={200}
          onChange={(e) => onChange({ label: e.target.value })}
        />
      </label>

      {value !== null && (
        <>
          <label className={ROW_CLASS}>
            <span className="font-sans text-[12px] leading-none font-normal text-ink-3">
              입력값
            </span>
            <input
              aria-label="Step 입력값"
              className="font-mono"
              value={value}
              disabled={!editable || valueIsSecret}
              maxLength={4000}
              onChange={(e) => onChange({ value: e.target.value })}
            />
          </label>
          {valueIsSecret && (
            <p className="font-sans text-[11px] leading-[1.4] font-normal text-ink-3 mt-s1 mr-0 mb-0 ml-[100px]">
              {SENSITIVE_VALUE_NOTICE}
            </p>
          )}
        </>
      )}

      {isNavigate(step) && (
        <label className={ROW_CLASS}>
          <span className="font-sans text-[12px] leading-none font-normal text-ink-3">
            주소
          </span>
          <input
            aria-label="Step 주소"
            className="font-mono"
            value={step.url}
            disabled={!editable}
            maxLength={2000}
            onChange={(e) => onChange({ url: e.target.value })}
          />
        </label>
      )}

      {step.type === "assertion" && (
        <label className={ROW_CLASS}>
          <span className="font-sans text-[12px] leading-none font-normal text-ink-3">
            기대값
          </span>
          <input
            aria-label="검증 기대값"
            className="font-mono"
            value={step.assertion.value ?? ""}
            disabled={!editable}
            maxLength={4000}
            onChange={(e) => onChange({ assertion_value: e.target.value })}
          />
        </label>
      )}

      <label className={ROW_CLASS}>
        <span className="font-sans text-[12px] leading-none font-normal text-ink-3">
          대기 시간
        </span>
 <span className="flex items-center gap-[6px]">
          <input
            aria-label="Step 대기 시간 (ms)"
            type="number"
            min={1}
            max={60000}
            value={step.timeout_ms}
            disabled={!editable}
            className="w-[110px]"
            onChange={(e) => {
              const next = Number(e.target.value);
              if (Number.isFinite(next) && next >= 1 && next <= 60000) {
                onChange({ timeout_ms: next });
              }
            }}
          />
          <span className="font-sans text-[11px] leading-[1.4] font-normal text-ink-3">
            ms
          </span>
        </span>
      </label>

      <label className={ROW_CLASS}>
        <span className="font-sans text-[12px] leading-none font-normal text-ink-3">
          대상 탭
        </span>
        <input
          aria-label="Step 대상 탭"
          type="number"
          min={0}
          value={step.tab}
          disabled={!editable}
          className="w-[110px]"
          onChange={(e) => {
            const next = Number(e.target.value);
            if (Number.isInteger(next) && next >= 0) onChange({ tab: next });
          }}
        />
      </label>
    </div>
  );
}
