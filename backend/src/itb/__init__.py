"""Interactive AI Test Builder.

패키지 경계가 헌법 원칙 II(Deterministic Replay)를 표현한다.

    domain      순수. 아무것도 임포트하지 않는다
    locator     domain 만 임포트
    execution   ─┐
    storage      │ itb.llm / itb.authoring / anthropic 을 임포트할 수 없다
    generator    │ (.importlinter 의 execution-no-llm 계약이 CI 에서 강제)
    recording   ─┘
    authoring   llm 임포트 허용 (작성 단계 전용)
    llm         Anthropic SDK 와의 유일한 접점
"""

__version__ = "0.1.0"
