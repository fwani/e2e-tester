"""사람 인수 녹화. FR-071·FR-075 (T124).

AI 가 막힌 그 화면에서 사람이 이어받는다. **화면을 되돌리지 않는다** — AI 가 남긴 상태가
곧 사람이 이어받는 출발점이다. 되돌리면 AI 가 이미 지나온 절차를 사람이 다시 밟아야 하고,
그것은 Takeover 가 해결하려는 문제 그 자체다 (PRD §8).

기록되는 Step 은 `author=human` 이다. **구조는 AI Step 과 완전히 같다** (원칙 I) —
`author` 는 배지 표시용이며 실행 방식을 바꾸지 않는다 (FR-014).

`InlineRecording` 과 다른 점은 삽입 위치다. 일시정지 중 직접 동작 추가는 일시정지 위치에
끼워 넣지만, 인수 녹화는 **목록 끝에 붙인다** — AI 가 하던 일을 이어받는 것이므로 지금까지
기록된 것 다음이 맞다.
"""

from __future__ import annotations

from dataclasses import dataclass

from itb.domain.step import Author
from itb.execution.session import BrowserSession
from itb.recording.recorder import Recorder


@dataclass(slots=True)
class TakeoverRecording:
    """AI 실패 후 사람이 이어받는 녹화 한 구간."""

    session: BrowserSession
    recorder: Recorder

    async def start(self) -> None:
        """인수 녹화를 시작한다.

        실제 창을 앞으로 가져온다 — 사용자는 미러가 아니라 실제 창에서 조작한다
        (clarify 결정 3, FR-023a). 창이 뒤에 있으면 무엇을 해야 할지 알 수 없다.
        """
        self.recorder.start(author=Author.HUMAN, insert_at=None)
        await self.session.bring_tab_to_front(self.session.active_tab_index)

    def stop(self) -> None:
        """인수 녹화를 끝낸다. AI 가 이어받을 수 있는 상태로 돌려 둔다."""
        self.recorder.stop()

    def summary(self) -> str:
        """사람이 무엇을 했는지 한 줄로. 에이전트 재개 지시에 실어 보낸다 (FR-076).

        Step 목록 전체를 넘기지 않는 이유는, 에이전트가 지금 화면을 직접 관찰해 판단해야
        하기 때문이다. 사람이 한 일의 요약은 "이미 처리된 것을 다시 하지 마라" 는 신호이며,
        판단의 근거는 관찰이다.
        """
        recorded = self.recorder.last_step_label
        if recorded is None:
            return "사람이 이어받았지만 기록된 동작은 없습니다."
        return f"사람이 직접 수행했습니다 (마지막 동작: {recorded})."
