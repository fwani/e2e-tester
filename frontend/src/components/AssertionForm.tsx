/**
 * 검증 조건 구성 (T105). FR-013a·FR-013b · 021.
 *
 * 7종이다 (023 이 `value` 를 더했다). 요소 갯수 검증과 체크 상태·읽기 전용은 여전히
 * 범위 외다 (FR-013c · 021) — 목록에 넣어 두고 비활성으로 보여 주지 않는다. 없는 기능을
 * 회색으로 보여 주는 것은 "곧 생긴다"는 약속처럼 읽힌다.
 *
 * **대상 요소는 셀렉터로만 지정한다.** 후보 수집·검증은 서버가 한다 (원칙 IV) — 여기서
 * 후보 묶음을 만들면 녹화가 만드는 것과 다른 형태가 생긴다.
 *
 * **문구를 직접 만들지 않는다.** 종류·비교 방식의 한국어는 `lib/wording` 이 소유한다
 * (021 FR-023) — 폼과 목록이 각자 만들면 같은 검증이 화면마다 다르게 불린다.
 */
import { useState } from "react";

import type { AddAssertionBody, AssertionKind, MatchMode } from "../api/client";
import {
  ASSERTION_KIND_HINT,
  ASSERTION_KIND_LABEL,
  MATCH_MODE_LABEL,
  NEGATED_MATCH_NOTE,
  comparesValue,
  isNegatedMatch,
} from "../lib/wording";
import { Button } from "../ui/Button";
import { Input } from "../ui/Input";
import { Radio } from "../ui/Radio";

const KINDS: AssertionKind[] = [
  "visible",
  "hidden",
  "enabled",
  "disabled",
  "text",
  "value",
  "url",
];
/**
 * 요소에 대한 검증 넷을 앞에, 값을 비교하는 셋을 뒤에 둔다 — 고르는 사람의 순서다.
 *
 * **`value` 를 `text` 바로 아래 둔다** (023). 둘이 가장 헷갈리는 짝이고, 붙여 놓아야
 * 고르는 순간 비교된다 — 입력 칸에 텍스트 검증을 고르는 실수가 이 기능의 출발점이다.
 */

const MATCHES: MatchMode[] = ["equals", "contains", "not_equals", "not_contains"];

/** 대상 요소가 반드시 필요한 종류 (data-model §2). */
const NEEDS_TARGET = new Set<AssertionKind>([
  "visible",
  "hidden",
  "enabled",
  "disabled",
  "value",
]);
/** 비교 값이 반드시 필요한 종류. */
const NEEDS_VALUE = new Set<AssertionKind>(["text", "url", "value"]);
/*
  `value` 가 **두 집합에 함께 드는 첫 종류다** (023 data-model §2). 지금까지 둘은
  겹치지 않았다 — `text` 는 대상이 선택이었고, 대상이 필수인 넷은 값을 비교하지 않았다.
*/

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
  /*
    값 칸을 숨기는 것은 **새 종류 둘뿐이다.** `visible`·`hidden` 은 서버가 표시 이름을
    만들 때 이 값을 읽으므로(`assertion_builder.default_label`) 칸을 없애면 기존 기능을
    잃는다 — 021 data-model §2 가 그 둘의 값을 「열려 있음(호환)」으로 둔 이유다.
  */
  const valueAllowed = kind !== "enabled" && kind !== "disabled";
  const valueRequired = NEEDS_VALUE.has(kind);
  const ready =
    (!targetRequired || selector.trim() !== "") && (!valueRequired || value.trim() !== "");

  const submit = () => {
    onSubmit({
      kind,
      target_selector: targetAllowed && selector.trim() !== "" ? selector.trim() : null,
      // 값을 쓰지 않는 종류에는 값도 부정 비교도 보내지 않는다 — 서버가 거절한다
      // (021 data-model §2). 화면이 거절당할 것을 보내면 사용자는 자기가 무엇을
      // 잘못했는지 모른다.
      value: valueAllowed && value.trim() !== "" ? value.trim() : null,
      match: comparesValue(kind) ? match : "equals",
      label: label.trim() !== "" ? label.trim() : null,
      tab: tab ?? null,
    });
  };

  return (
    <div
      className="bg-panel border border-hair rounded-base p-[14px] flex flex-col gap-[10px]"
    >
      <strong className="font-sans text-[14px] font-semibold leading-none">검증 Step 추가</strong>

      <fieldset className="border-0 p-0 m-0 grid gap-[6px]">
        <legend className="font-sans text-[12px] font-semibold leading-[1.4] text-ink-2 p-0">
          조건
        </legend>
        {KINDS.map((k) => (
          <label key={k} className="flex items-center gap-s2 items-start">
            <Radio
              name="assertion-kind"
              value={k}
              checked={kind === k}
              onChange={() => setKind(k)}
            />
            <span>
              {ASSERTION_KIND_LABEL[k]}
              <br />
              <span className="font-sans text-[12px] leading-[1.4] font-normal text-ink-3">
                {ASSERTION_KIND_HINT[k]}
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
          <Input
            id="assertion-selector"
            value={selector}
            onChange={(e) => setSelector(e.target.value)}
            placeholder="[data-testid=project-row]"
          />
        </div>
      )}

      {/*
        값을 쓰지 않는 종류에서는 이 칸을 **숨긴다** (021). 비워 두면 「적어도 되는가」를
        사용자가 다시 판단해야 하고, 상태 검증은 값을 받으면 거절된다.
      */}
      {valueAllowed && (
        <div>
          <label htmlFor="assertion-value">
            비교 값{valueRequired ? " — 필수" : " (선택)"}
          </label>
          <Input
            id="assertion-value"
            value={value}
            onChange={(e) => setValue(e.target.value)}
            placeholder="{{PROJECT_NAME}}"
          />
          <p className="font-sans text-[12px] leading-[1.4] font-normal text-ink-3 mt-s1 mx-0 mb-0">
            {"{{변수명}}"} 으로 변수를 참조할 수 있습니다 (FR-013b). 민감 변수의 실제 값은
            화면에 표시되지 않습니다.
          </p>
        </div>
      )}

      {comparesValue(kind) && (
        <fieldset className="border-0 p-0 m-0 grid gap-[6px]">
          <legend className="font-sans text-[12px] font-semibold leading-[1.4] text-ink-2 p-0">
            비교 방식
          </legend>
          <div className="flex items-center gap-s3 flex-wrap">
            {MATCHES.map((m) => (
              <label key={m} className="flex items-center gap-[6px]">
                <Radio
                  name="assertion-match"
                  checked={match === m}
                  onChange={() => setMatch(m)}
                />
                {MATCH_MODE_LABEL[m]}
              </label>
            ))}
          </div>
          {/*
            부정 비교에서 제한 시간의 뜻이 달라진다 — 상한이 아니라 관찰 기간이다
            (021 FR-026). 말하지 않으면 왜 이 검증만 오래 걸리는지, 기간 뒤에 나타나는
            것은 왜 잡히지 않는지를 오해한다. 경고가 아니라 조언의 문체로 쓴다.
          */}
          {isNegatedMatch(match) && (
            <p
              data-testid="negated-match-note"
              className="font-sans text-[12px] leading-[1.4] font-normal text-ink-3 mt-s1 mx-0 mb-0"
            >
              {NEGATED_MATCH_NOTE}
            </p>
          )}
        </fieldset>
      )}

      <div>
        <label htmlFor="assertion-label">표시 이름 (선택)</label>
        <Input
          id="assertion-label"
          value={label}
          onChange={(e) => setLabel(e.target.value)}
          placeholder='"TEST" 표시 확인'
        />
      </div>

      <div className="flex items-center gap-s2">
        <Button disabled={busy || !ready} onClick={submit}>
          추가
        </Button>
        {onCancel && (
          <Button onClick={onCancel} disabled={busy}>
            취소
          </Button>
        )}
      </div>
    </div>
  );
}
