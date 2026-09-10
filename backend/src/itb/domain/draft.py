"""테스트 초안 — 아직 녹화되지 않은 테스트의 의도 (기능 014).

**초안은 테스트가 아니다.** 이것이 이 모듈의 존재 이유이자 가장 중요한 사실이다.

스프레드시트의 한 행은 "무엇을 할지"를 말하지만 "어떻게 할지"는 말하지 못한다. 화면의 어느
요소를 누를지는 표의 글로 지목할 수 없고, :class:`itb.domain.locator.TargetLocator` 의 후보
묶음은 녹화가 실제 DOM 에서 수집해야만 나온다. 그래서 가져오기는 :class:`itb.domain.test_case.Test`
를 만들지 않고 :class:`Draft` 를 만든다.

:class:`Draft` 에 ``steps`` 필드가 **없다**는 점을 눈여겨봐야 한다. 두면 "스텝 0개짜리 테스트"가
되고, 그 순간 ``Test.steps`` 의 ``min_length=1`` 을 우회하는 두 번째 테스트 표현이 생긴다.
헌법 원칙 I 은 테스트의 표현이 하나뿐일 것을 요구하므로, 초안은 테스트와 **다른 모양**이어야
한다. 비슷한 모양이면 언젠가 섞인다.

초안의 일생:

.. code-block:: text

    (스프레드시트 행) ──가져오기 확정──▶ Draft ──사용자 삭제──▶ (없음)
                                          │
                                          │ POST /api/sessions {mode:"ai", draft_id}
                                          ▼
                                     AI 작성 세션 ──버림──▶ Draft 그대로
                                          │
                                          │ 저장
                                          ▼
                                        Test  (+ Draft 파일 삭제)

초안은 **번호를 예약하지 않는다.** :attr:`Draft.desired_test_id` 는 희망일 뿐이고 실제 부여는
저장 시점에 일어난다 (FR-032). 예약하지 않기로 한 덕분에 「번호 정리」·새 테스트 만들기와
아무 상호작용이 없다.
"""

from __future__ import annotations

import re
from datetime import UTC, datetime
from typing import Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

from itb.domain.test_case import (
    GROUP_PREFIX_PATTERN,
    MAX_INSTRUCTION_CHARS,
    RESERVED_PREFIX,
    TEST_ID_PATTERN,
)

DRAFT_ID_PATTERN = r"^D-\d{4}$"
"""초안 식별자 = ``D-`` + 네 자리.

**테스트 식별자와 다른 공간이다.** 초안이 `TC-005` 같은 이름을 쓰면 같은 이름의 테스트와
헷갈리고, 목록에서 둘을 가르는 것이 사람의 주의력뿐이게 된다. `D-` 접두어는 파일 이름만
봐도 초안임을 말해 준다.

:data:`~itb.domain.test_case.GROUP_PREFIX_PATTERN` 과 겹치지 않는다 — 그쪽은 대문자 뒤에
대문자·숫자만 오므로 `D-0001` 의 하이픈이 통과하지 못한다.
"""

MAX_DRAFT_NUMBER = 9999
"""초안 수 상한.

테스트 번호 상한(:data:`~itb.domain.test_case.MAX_TEST_NUMBER`)과 **별개다**. 초안은 번호를
예약하지 않으므로 둘이 같은 공간을 다투지 않는다. 실제로 만들 수 있는 초안 수는 프로젝트의
남은 테스트 번호가 따로 제한한다 (FR-036b).
"""

_DRAFT_ID_RE = re.compile(DRAFT_ID_PATTERN)


class DraftSource(BaseModel):
    """이 초안이 어느 파일의 어느 시트 몇 행에서 왔는가.

    사용자가 원본 설계서를 되짚을 수 있어야 한다. 초안이 스무 건 쌓였을 때 "이건 어디서
    온 거지"에 답하지 못하면 목록은 정체 모를 할 일 더미가 된다.
    """

    model_config = ConfigDict(extra="forbid", json_schema_serialization_defaults_required=True)

    file_name: str = Field(min_length=1, max_length=200)
    sheet_name: str = Field(min_length=1, max_length=31)
    """엑셀 시트 이름 상한이 31자다."""

    row: int = Field(ge=2)
    """1행은 머리글이므로 데이터는 2행부터다."""


class Draft(BaseModel):
    """스프레드시트 행 하나에서 온, 아직 스텝이 없는 테스트의 의도.

    ``drafts/<draft_id>-<slug>.yaml`` 파일 하나에 대응한다. `tests/` 와 디렉터리를 나눈 것은
    벽을 정규식이 아니라 파일시스템이 되게 하려는 것이다 (014 research R7).
    """

    model_config = ConfigDict(extra="forbid", json_schema_serialization_defaults_required=True)

    draft_id: str = Field(pattern=DRAFT_ID_PATTERN)

    name: str = Field(min_length=1, max_length=200)
    """대상기능(제목). **비어 있을 수 없다** — 제목 없는 행은 애초에 초안이 되지 않는다
    (FR-018). 이것이 `Test.name` 이 된다."""

    description: str | None = Field(default=None, max_length=2000)
    """테스트항목. `Test.description` 이 된다."""

    actor: str | None = Field(default=None, max_length=100)
    """수행자 역할. 자유 텍스트이며 자격 증명이 아니다 (FR-026a). `Test.actor` 가 된다."""

    procedure: str | None = Field(default=None, max_length=2000)
    """수행 절차. 사람이 쓴 자연어이며 **파싱하지 않는다** — 정해진 문법이 없다고 본다.
    그대로 AI 지시문에 넘어가고, 스텝은 녹화가 만든다."""

    expectation: str | None = Field(default=None, max_length=2000)
    """기대 결과. `procedure` 와 같은 성격이다."""

    desired_test_id: str | None = Field(default=None, pattern=TEST_ID_PATTERN)
    """원본 행이 적고 있던 TC ID. **희망일 뿐 예약이 아니다** (FR-032).

    저장 시점에 이 번호가 비어 있으면 그것을 받고, 이미 쓰였으면 빈 번호를 받은 뒤
    그 사실을 사용자에게 알린다. 조용히 다른 번호를 주지 않는다.
    """

    group_prefix: str = Field(default=RESERVED_PREFIX, pattern=GROUP_PREFIX_PATTERN)
    """소속 그룹의 접두어. :data:`~itb.domain.test_case.RESERVED_PREFIX` 면 그룹 없음이다.

    접두어가 곧 소속이라는 013 의 결정을 그대로 따른다.
    """

    source: DraftSource
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    @model_validator(mode="after")
    def _check_shape(self) -> Self:
        if self.desired_test_id is not None:
            wanted_prefix = self.desired_test_id.split("-", 1)[0]
            if wanted_prefix != self.group_prefix:
                msg = (
                    f"희망 식별자의 접두어({wanted_prefix})가 소속 그룹"
                    f"({self.group_prefix})과 다르다"
                )
                raise ValueError(msg)

        # 지시문이 상한을 넘는 초안은 만들지 않는다. 만들어 두면 녹화를 시작하는
        # 순간에야 막히고, 그때는 사용자가 이미 이 초안을 하겠다고 마음먹은 뒤다.
        composed = len(compose_instruction(self))
        if composed > MAX_INSTRUCTION_CHARS:
            msg = (
                f"초안에서 만든 지시문이 {composed}자로 상한"
                f"({MAX_INSTRUCTION_CHARS}자)을 넘는다"
            )
            raise ValueError(msg)
        return self


def draft_number(draft_id: str) -> int:
    """``D-0007`` → ``7``. 형식이 아니면 :class:`ValueError`."""
    if not _DRAFT_ID_RE.match(draft_id):
        msg = f"초안 식별자 형식이 아니다: {draft_id}"
        raise ValueError(msg)
    return int(draft_id[2:])


def format_draft_id(number: int) -> str:
    """``7`` → ``D-0007``. 상한을 넘으면 :class:`ValueError`."""
    if not 1 <= number <= MAX_DRAFT_NUMBER:
        msg = f"초안 번호가 범위를 벗어났다: {number} (1~{MAX_DRAFT_NUMBER})"
        raise ValueError(msg)
    return f"D-{number:04d}"


def compose_instruction(draft: Draft) -> str:
    """초안에서 AI 작성 지시문을 짓는다 (FR-031).

    사용자는 이 결과를 지시문 칸에서 미리 보고 고칠 수 있다. 서버가 짓는 이유는, 초안의
    어떤 칸이 지시문의 어느 자리에 들어가는지가 제품의 판단이지 화면의 판단이 아니기
    때문이다 — 화면이 지으면 화면마다 달라진다.

    **빈 항목은 줄째로 뺀다.** `수행자: None` 같은 줄이 지시문에 들어가면 모델이 그것을
    지시로 읽는다.

    길이 상한은 구조로 보장된다 — 필드 상한의 합(200+2000+100+2000+2000 = 6,300)에 머리말을
    더해도 :data:`~itb.domain.test_case.MAX_INSTRUCTION_CHARS` 안에 든다.
    :meth:`Draft._check_shape` 가 그 사실을 실제 값으로 다시 확인한다.
    """
    parts: list[str] = [f"제목: {draft.name}"]

    if draft.description:
        parts.append(f"설명: {draft.description}")
    if draft.actor:
        parts.append(f"수행자: {draft.actor} 역할로 수행한다.")
    if draft.procedure:
        parts.append(f"수행 절차:\n{draft.procedure}")
    if draft.expectation:
        parts.append(f"기대 결과:\n{draft.expectation}")

    return "\n\n".join(parts)
