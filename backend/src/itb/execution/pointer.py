"""재생 중 **포인터가 어디 있는가** 때문에 생기는 문제 (2026-09-09 사용자 보고).

## 왜 이 모듈이 따로 있는가

사용자 보고: 「step9번으로 클릭한 다음에 메뉴에 마우스가 그대로 있어서 확장된 형태라서 메뉴
뒤에 가려진 원천데이터를 클릭하지 못한다. 측정은 잘되었으나, 재실행시 클릭한 위치에 마우스가
가게되면서 발생한 문제로 보인다.」

Playwright 의 ``click()`` 은 포인터를 요소 위로 옮기고 **그대로 둔다.** 녹화 때는 사람이 곧
마우스를 움직이므로 hover 로 열린 메뉴가 접히지만, 재생 때는 포인터가 머문다. 그리고 그것이
**교착이 된다**: Playwright 는 클릭 전에 히트 검사를 하고 그 검사는 포인터를 옮기기 **전에**
하므로, 「메뉴가 덮고 있다 → 검사 실패 → 재시도 → 포인터는 그대로」가 예산이 끝날 때까지
돈다.

**`step_executor` 안에 두지 않은 이유가 있다.** 그 모듈에는 「실패를 표현하는 유일한 수단이
예외다」라는 규칙이 있고, 검증이 그것을 원문에서 센다
(`test_step_executor_never_returns_silently_on_failure` — `return False` 를 금지한다).
이 모듈의 `is_occluded` 는 **질문에 답하는 함수**이고 그 답이 거짓일 수 있다. 규칙을 느슨하게
하는 대신 성격이 다른 코드를 분리한다 — 규칙은 그 모듈에서 그대로 세게 남는다.
"""

from __future__ import annotations

import contextlib
from typing import Any

from playwright.async_api import Error as PlaywrightError
from playwright.async_api import Page

OCCLUSION_PROBE = """el => {
  const rect = el.getBoundingClientRect();
  if (rect.width === 0 || rect.height === 0) return false;
  const x = rect.left + rect.width / 2;
  const y = rect.top + rect.height / 2;
  if (x < 0 || y < 0 || x > innerWidth || y > innerHeight) return false;
  const hit = document.elementFromPoint(x, y);
  if (hit === null) return true;
  return !(el === hit || el.contains(hit) || hit.contains(el));
}"""
"""클릭 지점이 **다른 요소에 가려졌는가**.

``document.elementFromPoint`` 가 대상도, 대상의 자손도, 대상을 담은 조상도 아닌 것을
돌려주면 그 위에 무언가가 덮여 있다는 뜻이다. **조상을 허용한다** — 라벨이 입력을 감싸는
흔한 구조에서 히트 결과가 라벨이 되는데 그것은 가림이 아니다.

**화면 밖·크기 0 은 가림이 아니다.** Playwright 가 클릭 전에 스크롤해 넣으므로 여기서 판단할
일이 아니다. 가림으로 보고 포인터를 옮겨도 해는 없지만, 이유가 다른 것을 같은 이름으로
부르면 다음 사람이 그 값을 잘못 읽는다.
"""


async def is_occluded(locator: Any) -> bool:
    """클릭 지점이 가려졌는가. **모르면 아니라고 답한다.**

    확인이 실패하는 경우(요소가 방금 사라졌다, 프레임이 옮겨졌다)는 클릭 쪽이 곧 같은 사실을
    더 정확한 문장으로 말한다. 여기서 「가려졌다」고 답하면 포인터를 옮겨 hover 로 유지되는
    메뉴를 접을 수 있다 — 모르는 것을 근거로 화면을 건드리지 않는다.
    """
    with contextlib.suppress(PlaywrightError):
        return bool(await locator.evaluate(OCCLUSION_PROBE))
    return False


async def park(page: Page) -> None:
    """포인터를 대상에서 떼어 놓는다.

    **어디로 옮기는가.** 뷰포트의 오른쪽 아래 끝이다. 화면 메뉴는 위·왼쪽에 몰려 있으므로 그
    반대 끝이 「무언가를 hover 할」 확률이 가장 낮다. ``(0, 0)`` 은 로고나 첫 메뉴가 있는
    자리라 다른 것을 열 수 있다.

    크기를 모르면(창 없는 컨텍스트 등) 아무것도 하지 않는다 — 좌표를 지어내 엉뚱한 곳을
    hover 하는 것보다 낫다.

    **삼키는 것은 브라우저 쪽 실패뿐이다** (`PlaywrightError`). 이 함수는 클릭을 돕는
    보조이므로 포인터를 못 옮긴 것이 클릭 실패 사유를 덮어서는 안 된다. 그렇다고
    ``Exception`` 을 삼키지는 않는다 — 그러면 이 코드 자신의 오류(오타·타입)도 함께 사라진다.
    """
    with contextlib.suppress(PlaywrightError):
        size = page.viewport_size
        if not size:
            return
        await page.mouse.move(max(size["width"] - 1, 0), max(size["height"] - 1, 0))
