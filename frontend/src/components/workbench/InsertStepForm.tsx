/**
 * 「이 앞에 추가」 — 손으로 넣을 Step 을 고르고 값을 적는 자리 (009 FR-285·FR-287).
 *
 * ## 왜 한 자리에 둘을 함께 그리는가
 *
 * 넣을 수 있는 종류(넷)와 **넣을 수 없는 종류(다섯)를 같은 자리에 함께** 그린다. 뒤쪽은
 * 비활성이며 왜 못 만드는지와 어디로 가면 만들 수 있는지를 말한다.
 *
 * 감추면 사용자는 그 종류가 이 제품에 없는 것으로 안다. 지금 편집 화면에서 클릭 Step 을
 * 추가할 방법이 없어 보이는 것이 정확히 그 상태였다 (009 관찰 M-01). FR-234 가 요구하는
 * 것은 「쓸 수 없으면 감추지 말고 이유를 붙인다」이며, 여기가 그 규칙이 가장 크게 작동하는
 * 자리다 — 원칙 IV 는 완화할 수 없으므로 이 다섯은 **영원히** 비활성이다. 그렇기에 더욱
 * 갈 길(브라우저를 열어 그 자리에서 멈추기)이 보여야 한다.
 *
 * ## 값 규칙
 *
 * 종류마다 필요한 값이 다르다. **필요한 것만 그린다** — 빈 칸을 남겨 두면 사용자는 그것도
 * 채워야 하는지 확인하느라 멈춘다.
 *
 *   주소로 이동      주소
 *   탭 닫기          (없음 — 대상은 탭 번호이며 공통 값이다)
 *   주소 검증        주소 · 일치 방식
 *   화면 텍스트 검증  기대 텍스트 · 일치 방식
 */
import { useState } from "react";

import type { InsertableKind, ManualStepSpec, MatchMode } from "../../api/client";
import {
  BROWSER_ONLY_KIND_LABEL,
  BROWSER_ONLY_KIND_REASON,
  INSERTABLE_KIND_LABEL,
  manualStepLabel,
} from "../../lib/wording";
import type { CapabilityState } from "../../lib/capabilities";

import { Button } from "../../ui/Button";

/** 넣을 수 있는 종류의 순서. 자주 쓰는 것부터다. */
const KINDS: InsertableKind[] = ["navigate", "assert_url", "assert_text", "close_tab"];

/** 요소를 지목해야 하는 종류. 자리를 남기고 비활성으로 그린다 (FR-287). */
const BROWSER_ONLY = ["click", "fill", "select", "hover", "drag"];

export interface InsertStepFormProps {
  /** 넣을 자리 — 사람이 읽는 번호. 「Step 04 앞에 넣습니다」로 쓴다 */
  atLabel: string;
  busy: boolean;
  /** 직접 입력이 가능한가. 비활성이면 이유를 그 자리에 적는다 */
  capability: CapabilityState;
  /** 브라우저를 열어 그 자리에서 멈추는 조작. 요소가 필요한 종류의 갈 길이다 */
  browserCapability: CapabilityState;
  onSubmit: (spec: ManualStepSpec) => void;
  onOpenBrowser: () => void;
  onCancel: () => void;
}

export function InsertStepForm({
  atLabel,
  busy,
  capability,
  browserCapability,
  onSubmit,
  onOpenBrowser,
  onCancel,
}: InsertStepFormProps) {
  const [kind, setKind] = useState<InsertableKind>("navigate");
  const [url, setUrl] = useState("");
  const [text, setText] = useState("");
  const [tab, setTab] = useState(0);
  const [match, setMatch] = useState<MatchMode>("equals");

  const usable = capability.kind === "enabled";
  const spec = buildSpec(kind, { url, text, tab, match });
  const ready = spec !== null;

  return (
    <div className="bg-panel border border-hair rounded-base p-s3 flex flex-col gap-[10px]">
      <div className="flex items-center gap-s2">
        <strong className="font-mono text-[11px] font-semibold leading-none tracking-[.08em] uppercase text-ink-3">{atLabel} 앞에 추가</strong>
        <div className="flex-1" />
        <Button size="sm" onClick={onCancel} aria-label="추가 닫기">
          닫기
        </Button>
      </div>

      {!usable && capability.kind === "disabled" && (
        <div className="font-sans text-[11px] leading-[1.4] text-ink-3" role="status">
          {capability.reason}
        </div>
      )}

      {/* 종류 — 넣을 수 있는 넷 */}
      <div role="radiogroup" aria-label="넣을 Step 종류" className="flex flex-wrap gap-[6px]">
        {KINDS.map((k) => (
          <Button
            key={k}
            role="radio"
            aria-checked={kind === k}
            disabled={!usable}
            size="sm"
            variant={kind === k ? "primary" : "default"}
            onClick={() => setKind(k)}
          >
            {INSERTABLE_KIND_LABEL[k]}
          </Button>
        ))}
      </div>

      {/* 종류마다 필요한 값만 그린다 */}
      {(kind === "navigate" || kind === "assert_url") && (
        <label className="flex flex-col gap-s1">
          <span className="font-mono text-[11px] font-semibold leading-none tracking-[.08em] uppercase text-ink-3">주소</span>
          <input
            aria-label="주소"
            className="font-mono"
            value={url}
            disabled={!usable}
            maxLength={2000}
            placeholder="https://example.test/orders"
            onChange={(e) => setUrl(e.target.value)}
          />
        </label>
      )}

      {kind === "assert_text" && (
        <label className="flex flex-col gap-s1">
          <span className="font-mono text-[11px] font-semibold leading-none tracking-[.08em] uppercase text-ink-3">기대 텍스트</span>
          <input
            aria-label="기대 텍스트"
            value={text}
            disabled={!usable}
            maxLength={4000}
            placeholder="주문이 완료되었습니다"
            onChange={(e) => setText(e.target.value)}
          />
        </label>
      )}

      {kind === "close_tab" && (
        <label className="flex flex-col gap-s1">
          <span className="font-mono text-[11px] font-semibold leading-none tracking-[.08em] uppercase text-ink-3">탭 번호</span>
          <input
            aria-label="탭 번호" className="font-mono w-[96px]"
            type="number"
            min={0}
            value={tab}
            disabled={!usable}
            onChange={(e) => setTab(Math.max(0, Number(e.target.value) || 0))}
          />
        </label>
      )}

      {(kind === "assert_url" || kind === "assert_text") && (
        <div role="radiogroup" aria-label="일치 방식" className="flex gap-[6px]">
          {(["equals", "contains"] as MatchMode[]).map((m) => (
            <Button
              key={m}
              role="radio"
              aria-checked={match === m}
              disabled={!usable}
              size="sm"
              variant={match === m ? "primary" : "default"}
              onClick={() => setMatch(m)}
            >
              {m === "equals" ? "정확히 일치" : "포함"}
            </Button>
          ))}
        </div>
      )}

      {/* 무엇이 들어가는지 미리 보여준다 — 목록에 어떤 이름으로 뜰지가 여기서 정해진다 */}
      {ready && (
        <div className="font-sans text-[11px] leading-[1.4] text-ink-3" aria-label="넣을 Step 미리보기">
          {manualStepLabel(spec)}
        </div>
      )}

      <div className="flex justify-end gap-s2">
        <Button
          variant="primary"
          disabled={busy || !usable || !ready}
          onClick={() => { /*
              **표시 이름을 여기서 붙여 보낸다** (research R6 의 화면 쪽 결정).

              서버에도 같은 규칙이 있지만 그것은 `label` 없이 온 요청을 위한 것이다. 화면이
              미리보기에 쓴 이름과 정의 파일에 저장되는 이름이 **같아야** 하므로, 미리보기에
              쓴 그 문자열을 그대로 보낸다 — 각자 만들면 저장 순간 이름이 바뀐 것으로 보인다.
            */
            if (spec !== null) onSubmit({ ...spec, label: manualStepLabel(spec) });
          }} >
          넣기
        </Button>
      </div>

      {/* ─── 요소를 지목해야 하는 종류 — 감추지 않는다 (FR-287) ──────────────── */}
      <div className="border-t border-hair pt-[10px] flex flex-col gap-[6px]">
        <div className="flex flex-wrap gap-[6px]">
          {BROWSER_ONLY.map((k) => (
            <Button
              key={k}
              size="sm" variant="off"
              disabled
              aria-disabled="true"
              title={BROWSER_ONLY_KIND_REASON} >
              {BROWSER_ONLY_KIND_LABEL[k]}
            </Button>
          ))}
        </div>
        <div className="font-sans text-[11px] leading-[1.4] text-ink-3" role="status">
          {BROWSER_ONLY_KIND_REASON}
        </div>
        {/* 갈 길을 같은 자리에 둔다 — 없는 방법을 가리키지 않는다 (006 E-03) */}
        <Button
          size="sm"
          disabled={browserCapability.kind !== "enabled"}
          onClick={onOpenBrowser} >
          브라우저 열어 이 자리에서 멈추기
        </Button>
        {browserCapability.kind === "disabled" && (
          <div className="font-sans text-[11px] leading-[1.4] text-ink-3">{browserCapability.reason}</div>
        )}
      </div>
    </div>
  );
}

/** 입력이 채워졌으면 서술을 만든다. 비었으면 `null` — 「넣기」가 잠긴다. */
function buildSpec(
  kind: InsertableKind,
  v: { url: string; text: string; tab: number; match: MatchMode },
): ManualStepSpec | null {
  switch (kind) {
    case "navigate":
      return v.url.trim() === "" ? null : { kind, url: v.url.trim() };
    case "close_tab":
      return { kind, tab: v.tab };
    case "assert_url":
      return v.url.trim() === "" ? null : { kind, url: v.url.trim(), match: v.match };
    case "assert_text":
      return v.text.trim() === "" ? null : { kind, value: v.text.trim(), match: v.match };
  }
}
