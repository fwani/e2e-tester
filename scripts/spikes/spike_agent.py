"""T008 — Anthropic SDK 표면 확인 (research R5).

자격 증명이 없는 환경에서도 확인 가능한 것만 본다. API 호출은 하지 않는다.

확인 항목:
1. beta_async_tool / beta_tool 데코레이터 존재
2. client.beta.messages.tool_runner 존재와 시그니처
3. tool_runner 가 fallbacks / betas / output_config 를 받는지 (거부 폴백, effort)
4. httpx2 기반인지 (anthropic 1.x)

★ 미확인으로 남는 것: 장기 실행 중 취소 반응, fallbacks="default" 의 실제 동작.
  자격 증명이 필요하므로 Phase 6 에서 확인한다.
"""

from __future__ import annotations

import inspect

import anthropic


def main() -> int:
    print(f"  anthropic {anthropic.__version__ if hasattr(anthropic,'__version__') else '(버전 불명)'}")

    # 1. 데코레이터
    have = {n: hasattr(anthropic, n) for n in
            ("beta_tool", "beta_async_tool", "AsyncAnthropic", "Anthropic")}
    print(f"  1. SDK 심볼: {have}")
    if not have["beta_async_tool"]:
        print("     ✗ beta_async_tool 이 없다. 수동 루프로 전환해야 한다")
        return 1

    # 2·3. tool_runner 시그니처
    client = anthropic.AsyncAnthropic(api_key="not-a-real-key-surface-check-only")
    runner_fn = client.beta.messages.tool_runner
    sig = inspect.signature(runner_fn)
    params = set(sig.parameters)
    interesting = {p: (p in params) for p in
                   ("model", "max_tokens", "tools", "messages",
                    "output_config", "betas", "fallbacks", "system")}
    print(f"  2. tool_runner 파라미터: {interesting}")

    missing = [k for k, v in interesting.items() if not v]
    if missing:
        print(f"     주의: {missing} 를 직접 받지 않는다 → extra_body 또는 수동 루프 필요 여부 확인")

    # 4. httpx2 기반 확인
    try:
        import httpx2  # noqa: F401
        print("  4. httpx2 설치됨 (anthropic 1.x 전제와 일치)")
    except ImportError:
        print("  4. httpx2 없음 — HTTP 객체를 직접 다룰 때 주의")

    print("\n  ★ 미확인 (자격 증명 필요, Phase 6 에서 확인):")
    print("     - tool_runner async 반복 중 취소(사용자 일시정지) 반응")
    print("     - fallbacks='default' 가 tool_runner 경로에서 동작하는지")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
