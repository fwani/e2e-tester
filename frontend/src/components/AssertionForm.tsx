/**
 * 검증 조건 구성 (T105). FR-013a·FR-013b.
 *
 * 4종만 있다. 요소 갯수·입력값 검증은 범위 외다 (FR-013c) — 목록에 넣어 두고 비활성으로
 * 보여 주지 않는다. 없는 기능을 회색으로 보여 주는 것은 "곧 생긴다"는 약속처럼 읽힌다.
 *
 * **대상 요소는 셀렉터로만 지정한다.** 후보 수집·검증은 서버가 한다 (원칙 IV) — 여기서
 * 후보 묶음을 만들면 녹화가 만드는 것과 다른 형태가 생긴다.
 */
import { useState } from "react";

import type { AddAssertionBody, AssertionKind, MatchMode } from "../api/client";

const KINDS: { kind: AssertionKind; label: string; hint: string }[] = [
  { kind: "visible", label: "요소가 보인다", hint: "대기 시간 안에 나타나고 보이면 통과" },
  {
    kind: "hidden",
    label: "요소가 없거나 보이지 않는다",
    hint: "처음부터 없던 경우와 사라진 경우 모두 통과",
  },
  { kind: "text", label: "텍스트 일치·포함", hint: "대상을 비우면 화면 전체가 대상" },
  { kind: "url", label: "주소 일치·포함", hint: "요소를 찾지 않는다" },
];

/** 대상 요소가 반드시 필요한 종류 (data-model §5). */
const NEEDS_TARGET = new Set<AssertionKind>(["visible", "hidden"]);
/** 비교 값이 반드시 필요한 종류. */
const NEEDS_VALUE = new Set<AssertionKind>(["text", "url"]);

export interface AssertionFormProps {
  onSubmit: (body: AddAssertionBody) => void;
  onCancel?: () => void;
  busy?: boolean;
  /** 기본 대상 탭. 지금 미러가 보고 있는 탭이다. */
  tab?: number;
}

export function AssertionForm({ onSubmit, onCancel, busy = false, tab }: AssertionFormProps) {
  const [kind, setKind] = useState<AssertionKind>("visible");
  const [selector, setSelector] = useState("");
  const [value, setValue] = useState("");
  const [match, setMatch] = useState<MatchMode>("equals");
  const [label, setLabel] = useState("");

  const targetAllowed = kind !== "url";
  const targetRequired = NEEDS_TARGET.has(kind);
  const valueRequired = NEEDS_VALUE.has(kind);
  const ready =
    (!targetRequired || selector.trim() !== "") && (!valueRequired || value.trim() !== "");

  const submit = () => {
    onSubmit({
      kind,
      target_selector: targetAllowed && selector.trim() !== "" ? selector.trim() : null,
      value: value.trim() !== "" ? value.trim() : null,
      match,
      label: label.trim() !== "" ? label.trim() : null,
      tab: tab ?? null,
    });
  };

  return (
    <div
      className="bg-panel border border-hair rounded-base p-[14px] flex flex-col gap-[10px]"
    >
      <strong className="font-sans text-[13px] font-semibold leading-none">검증 Step 추가</strong>

      <fieldset className="border-0 p-0 m-0 grid gap-[6px]">
        <legend className="font-mono text-[11px] font-semibold leading-none tracking-[.08em] uppercase text-ink-3 p-0">
          조건
        </legend>
        {KINDS.map((k) => (
          <label key={k.kind} className="flex items-center gap-s2 items-start">
            <input
              type="radio"
              name="assertion-kind"
              value={k.kind}
              checked={kind === k.kind}
              onChange={() => setKind(k.kind)}
            />
            <span>
              {k.label}
              <br />
              <span className="font-sans text-[11px] leading-[1.4] text-ink-3">
                {k.hint}
              </span>
            </span>
          </label>
        ))}
      </fieldset>

      {targetAllowed && (
        <div>
          <label htmlFor="assertion-selector">
            대상 요소 (CSS 셀렉터){targetRequired ? " — 필수" : " — 생략하면 화면 전체"}
          </label>
          <input
            id="assertion-selector"
            value={selector}
            onChange={(e) => setSelector(e.target.value)}
            placeholder="[data-testid=project-row]"
          />
        </div>
      )}

      <div>
        <label htmlFor="assertion-value">
          비교 값{valueRequired ? " — 필수" : " (선택)"}
        </label>
        <input
          id="assertion-value"
          value={value}
          onChange={(e) => setValue(e.target.value)}
          placeholder="{{PROJECT_NAME}}"
        />
        <p className="font-sans text-[11px] leading-[1.4] text-ink-3 mt-s1 mx-0 mb-0">
          {"{{변수명}}"} 으로 변수를 참조할 수 있습니다 (FR-013b). 민감 변수의 실제 값은
          화면에 표시되지 않습니다.
        </p>
      </div>

      {(kind === "text" || kind === "url") && (
        <div className="flex items-center gap-s2 gap-s3">
          <label className="flex items-center gap-s2 gap-[6px]">
            <input
              type="radio"
              name="assertion-match"
              checked={match === "equals"}
              onChange={() => setMatch("equals")}
            />
            일치
          </label>
          <label className="flex items-center gap-s2 gap-[6px]">
            <input
              type="radio"
              name="assertion-match"
              checked={match === "contains"}
              onChange={() => setMatch("contains")}
            />
            포함
          </label>
        </div>
      )}

      <div>
        <label htmlFor="assertion-label">표시 이름 (선택)</label>
        <input
          id="assertion-label"
          value={label}
          onChange={(e) => setLabel(e.target.value)}
          placeholder='"TEST" 표시 확인'
        />
      </div>

      <div className="flex items-center gap-s2">
        <button disabled={busy || !ready} onClick={submit}>
          추가
        </button>
        {onCancel && (
          <button className="secondary" onClick={onCancel} disabled={busy}>
            취소
          </button>
        )}
      </div>
    </div>
  );
}
