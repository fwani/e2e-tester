"""면별 실행 수단. 임포트하는 것만으로 레지스트리에 등록된다.

`tests.abnormal.catalogue.DRIVERS` 를 읽는 쪽은 이 패키지를 먼저 임포트해야 한다.
그러지 않으면 레지스트리가 비어 있어 "수단이 없다"는 판정이 무의미해진다.
"""

from __future__ import annotations

from tests.abnormal.drivers import api_drivers, boundary_drivers, ui_drivers  # noqa: F401
