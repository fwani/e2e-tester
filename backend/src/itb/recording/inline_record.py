"""일시정지 중 직접 동작 추가. FR-036·FR-023a (T099).

일시정지 상태에서 사용자가 실제 브라우저 창을 조작하면, 그 조작이 **일시정지 위치에**
Step 으로 삽입된다. 목록 끝이 아니라 지금 멈춰 있는 그 지점이다 — 사용자가 보고 있는
화면이 그 지점의 화면이므로, 끝에 붙이면 정의와 화면이 어긋난다.

**여기서 브라우저 상태를 되돌리지 않는다.** 하는 일은 두 가지뿐이다.

1. 리코더를 삽입 위치와 함께 켠다
2. 실제 창과 대상 탭을 앞으로 가져온다 (FR-023a·FR-030e)

2번이 필요한 이유는 제품이 입력 경로에서 빠져 있기 때문이다 (clarify 결정 3). 사용자는
미러가 아니라 실제 창에서 조작하므로, 그 창이 뒤에 있으면 무엇을 해야 할지 알 수 없다.
"""

from __future__ import annotations

from dataclasses import dataclass

from itb.domain.step import Author
from itb.execution.session import BrowserSession
from itb.recording.recorder import Recorder


@dataclass(slots=True)
class InlineRecording:
    """일시정지 중 녹화 한 구간.

    리코더를 새로 만들지 않는다 — 세션의 리코더를 그대로 쓴다. 컨텍스트 단위로 등록한
    주입 스크립트와 바인딩을 재사용해야 하고(research R2), 새로 만들면 Step 번호가
    처음부터 다시 매겨져 기존 Step 과 충돌한다.
    """

    session: BrowserSession
    recorder: Recorder

    async def start(self, insert_at: int, author: Author = Author.HUMAN) -> None:
        """직접 동작 추가를 시작한다.

        `insert_at` 은 일시정지 위치다. 리코더가 Step 하나를 넣을 때마다 스스로 1 늘려
        여러 동작이 순서대로 삽입된다 (`Recorder._emit`).
        """
        self.recorder.seed_step_seq(insert_at)
        self.recorder.start(author=author, insert_at=insert_at)
        await self.bring_to_front()

    async def bring_to_front(self) -> None:
        """실제 창·대상 탭을 앞으로 가져온다 (FR-023a).

        조작할 창을 찾지 못하는 것은 흔한 사고이므로, 사용자가 다시 요청할 수 있도록
        별도 메서드로 둔다 (spec 엣지 케이스).
        """
        await self.session.bring_tab_to_front(self.session.active_tab_index)

    def stop(self) -> None:
        """직접 동작 추가를 끝낸다. 삽입 위치를 지워 다음 녹화가 끝에 붙게 한다."""
        self.recorder.stop()
        self.recorder.insert_at = None
