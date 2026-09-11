/**
 * `STARTING` 상태 표시 (T150). data-model §8, spec 디자인 차이 3.
 *
 * 브라우저가 뜨는 데 1~2초가 걸린다 (research R8 의 "세션 시작 준비 < 2s"). 그 사이
 * 화면이 비어 있으면 사용자는 아무 일도 일어나지 않았다고 생각하고 다시 누른다.
 *
 * **취소를 제공하지 않는다.** 시작 중인 브라우저를 중간에 끊으면 정리되지 않은 프로세스가
 * 남을 수 있고, 어차피 2초 안에 끝난다. 대신 오래 걸리면 그 사실을 알린다.
 */
import { useEffect, useState } from "react";

import { Chip } from "../ui/Chip";

/** 브라우저가 이 시간 안에 뜨지 않으면 무언가 잘못된 것이다 (research R8 목표는 2초). */
const SLOW_THRESHOLD_MS = 5000;

export interface StartingIndicatorProps {
  /** 시작한 시각. 오래 걸리는지 판단하는 기준이다. */
  startedAt?: number;
  message?: string;
}

export function StartingIndicator({
  startedAt = Date.now(),
  message = "브라우저를 실행하는 중입니다…",
}: StartingIndicatorProps) {
  const [slow, setSlow] = useState(false);

  useEffect(() => {
    const remaining = Math.max(0, SLOW_THRESHOLD_MS - (Date.now() - startedAt));
    const timer = setTimeout(() => setSlow(true), remaining);
    return () => clearTimeout(timer);
  }, [startedAt]);

  return (
    <div
      role="status"
      className="flex flex-col items-center justify-center gap-s2 p-s6"
    >
      <Chip>STARTING</Chip>
      <p className="m-0 font-sans text-[13px] leading-[1.4] font-normal text-ink-2">
        {message}
      </p>
      {slow && (
        <p className="m-0 text-center font-sans text-[11px] leading-[1.4] font-normal text-ink-3">
          평소보다 오래 걸리고 있습니다. 브라우저가 설치되어 있는지, 다른 창이 자원을 쓰고
          있지 않은지 확인하세요.
        </p>
      )}
    </div>
  );
}
