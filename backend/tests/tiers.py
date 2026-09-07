"""테스트 계층 분류의 단일 출처.

`conftest.py` 가 아니라 별도 모듈에 둔다. `tests/` 는 패키지가 아니어서 pytest 가
conftest 를 최상위 `conftest` 로 임포트하는데, 검증 쪽에서 `tests.conftest` 로 다시
임포트하면 같은 파일이 두 개의 모듈 객체가 된다. 상수 하나를 읽으려고 그 혼선을
만들 이유가 없다.
"""

from __future__ import annotations

HEAVY_FIXTURES = frozenset(
    {
        # 대상 웹 앱을 띄운다. `project_client`·`keyed_client` 가 이것을 거친다.
        "fixture_app",
        # 제품 서버(uvicorn)와 제품 화면(vite dev server)을 **프로세스로** 띄운다.
        # `fixture_app` 을 거치지 않으므로 따로 적어야 한다.
        "product_ui",
        # 제품 화면을 조작할 브라우저.
        "ui_browser",
        "ui_context",
    }
)
"""실제 스택을 요구하는 픽스처. 이 중 하나라도 쓰면 `browser` 로 분류한다.

"무엇이 무거운가" 를 코드에서 자동으로 알아낼 수는 없다 — 픽스처가 프로세스를 띄우는지는
본문을 읽어야 안다. 그래서 목록을 두고, 목록이 낡으면 드러나게 한다
(`tests/unit/test_test_tiers.py`).
"""


TIMING_MODULES = frozenset(
    {
        # 녹화 반영 지연·Step 실행 오버헤드·세션 준비 시간 (SC-003·SC-004·SC-016)
        "tests/integration/test_performance.py",
        # 중지·속도 변경이 **얼마나 빨리** 반영되는가 (INTERRUPT_LIMIT_S)
        "tests/integration/test_pacing_interrupt.py",
        # 늦게 나타나는 요소를 기다리는 시간과 즉시 있는 요소의 비용
        "tests/integration/test_lazy_loading.py",
        # 구독 후 첫 프레임까지의 초 (SC-218)
        "tests/integration/test_mirror_late_subscribe.py",
        # 속도 설정이 실제로 재우는지 — 벽시계로 잰다
        "tests/unit/test_runner_pacing.py",
    }
)
"""**경과 시간을 단언하는** 검증이 든 모듈. 저장소 루트 기준 경로다.

이 검증들은 제품이 얼마나 빠른지를 잰다. 프로세스 8개가 CPU 를 나눠 쓰면 재는 값이
제품의 성질이 아니라 **그 순간의 부하**가 된다. 실측: 8분할에서 녹화 반영 지연이
p95 737ms 로 나왔고 목표는 200ms 다 — 제품은 그대로인데 검증이 실패한다.

그래서 이 계층만 순차로 돈다. 나머지는 병렬로 돈다.

**건너뛰는 것이 아니다.** 순차로 **반드시 돈다** — `scripts/test-backend.sh` 가 두
계층을 모두 돌고, 어느 한쪽이 실패하면 전체가 실패한다. 병렬 실행에서 이 계층이
선택되면 `tests/conftest.py` 의 `_timing_needs_one_process` 가 사유와 함께 실패한다
(조용히 통과하지 않는다).
"""
