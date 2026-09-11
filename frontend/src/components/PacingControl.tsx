/**
 * 실행 속도 선택 (004 US1, FR-102·FR-103·FR-107).
 *
 * **실행 중에도 활성이다.** 속도를 바꾸는 이유가 대개 "지금 너무 빨라서 못 보겠다" 이므로,
 * 실행이 끝난 뒤에만 바꿀 수 있으면 이 기능은 쓸모가 없다. 변경은 진행 중인 Step 을
 * 끊지 않고 다음 Step 경계부터 적용된다 — 서버가 매 경계에서 값을 다시 읽는다.
 *
 * **간격 값을 여기서 계산하지 않는다.** 대응표는 서버가 갖는다. 화면이 "1.5초 쉽니다" 라고
 * 말하는 동안 러너가 0.5초를 쉬는 상태를 만들지 않으려면 값이 한 곳에만 있어야 한다.
 * 필요하면 `pacing_changed` 이벤트가 실어 보낸 `delay_ms` 를 쓴다.
 */
import { PACING_LABEL, PACING_ORDER, type RunPacing } from "../api/client";
import { Segmented } from "../ui/Table";

export interface PacingControlProps {
  value: RunPacing;
  onChange: (next: RunPacing) => void;
  /** 요청이 도는 중. 값은 그대로 보이되 연타를 막는다. */
  busy?: boolean;
  /**
   * 종료된 세션 등 바꿀 수 없는 상태. **숨기지 않고 비활성으로 둔다** — 컨트롤이
   * 사라지면 사용자는 자기가 고른 속도가 무엇이었는지도 확인할 수 없다.
   */
  disabled?: boolean;
  /**
   * 취향 파일에 남기지 못했다. 속도 자체는 바뀌었으므로 실행을 막지 않고, 다음 실행에
   * 유지되지 않는다는 사실만 알린다.
   */
  preferenceSaved?: boolean;
  /**
   * 사람이 직접 조작하는 국면인가 (005 FR-174 · U-23).
   *
   * 녹화·사람 인수 중에는 재생 속도가 **지금 실행에 쓰이지 않는다.** 004 명세는
   * 실행 국면만 말했고(FR-101~FR-110), 지금의 노출은 헤더 컨트롤을 국면 구분 없이
   * 둔 결과다.
   *
   * **감추지 않는다.** 004 FR-109 가 "속도 선택은 실행 간에 유지되고 다음 실행의
   * 기본값" 이므로 녹화 중에 고른 값도 쓰인다 — 감추면 그 정보를 잃는다.
   * 대신 무엇에 쓰이는 값인지 라벨로 밝힌다.
   */
  manipulationPhase?: boolean;
}

export function PacingControl({
  value,
  onChange,
  busy = false,
  disabled = false,
  preferenceSaved = true,
  manipulationPhase = false,
}: PacingControlProps) {
  return (
    <div className="flex items-center gap-s2">
      <span className="font-mono text-[11px] font-semibold leading-none tracking-[.08em] uppercase text-ink-3">{manipulationPhase ? "다음 실행 속도" : "속도"}</span>
      <Segmented role="group" aria-label="실행 속도">
        {PACING_ORDER.map((pacing) => {
          const active = pacing === value;
          return (
            <button
              key={pacing}
              type="button"
              aria-pressed={active}
              data-testid={`pacing-${pacing}`}
              disabled={busy || disabled}
              onClick={() => {
                if (!active) onChange(pacing);
              }}
              className={`px-s3 ${busy || disabled ? "cursor-default" : "cursor-pointer"}`}
            >
              {PACING_LABEL[pacing]}
            </button>
          );
        })}
      </Segmented>
      {!preferenceSaved && (
        <span
          role="status"
          className="font-sans text-[11px] leading-[1.4] font-normal text-ink-3 text-warn max-w-[180px]"
        >
          설정을 저장하지 못해 다음 실행에는 유지되지 않습니다.
        </span>
      )}
    </div>
  );
}
