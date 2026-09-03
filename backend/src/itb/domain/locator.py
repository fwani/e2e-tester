"""대상 요소 식별 정보. 헌법 원칙 IV (Locator Resilience).

단일 CSS 셀렉터가 아니라 **후보 묶음**을 저장한다 (FR-017). 후보별 상태는 녹화 직후
수행한 기록 시점 검증의 결과이며, 표시 상태는 여기서 파생된다 (FR-019a).
"""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field


class CandidateStatus(StrEnum):
    """기록 시점 검증 결과. research R4 실측으로 ``AMBIGUOUS`` 가 추가됐다."""

    VERIFIED = "verified"
    """count()==1 이고 그 요소가 기록 대상과 동일하다. 사용 가능한 유일한 상태."""

    AMBIGUOUS = "ambiguous"
    """count()>1 — 여러 요소를 매칭한다. 실행 시 어느 것을 잡을지 알 수 없어 사용하지 않는다."""

    UNVERIFIED = "unverified"
    """count()==1 이지만 다른 요소를 가리킨다."""

    NOT_COLLECTED = "not_collected"
    """값을 확보하지 못했거나 count()==0."""


class Candidate(BaseModel):
    """식별 후보 하나."""

    model_config = ConfigDict(extra="forbid", json_schema_serialization_defaults_required=True)

    value: str = Field(min_length=1, max_length=2000)
    status: CandidateStatus

    @property
    def usable(self) -> bool:
        """실행에 쓸 수 있는 후보인가.

        ``AMBIGUOUS`` 를 사용 가능으로 세면 SC-008 측정이 부풀려진다 (FR-019b).
        """
        return self.status is CandidateStatus.VERIFIED


class StableAttr(BaseModel):
    """`[name="value"]` 형태로 쓰는 안정적 속성."""

    model_config = ConfigDict(extra="forbid", json_schema_serialization_defaults_required=True)

    name: str = Field(min_length=1, max_length=100)
    value: str = Field(max_length=2000)
    status: CandidateStatus

    @property
    def usable(self) -> bool:
        return self.status is CandidateStatus.VERIFIED


class TargetLocator(BaseModel):
    """한 요소에 대한 식별 후보 묶음.

    **불변식**: 후보가 하나도 없는 ``TargetLocator`` 는 유효하지 않다.
    최소한 ``css`` 는 항상 수집된다.
    """

    model_config = ConfigDict(extra="forbid", json_schema_serialization_defaults_required=True)

    tag: str | None = Field(default=None, max_length=50)
    """진단용. 우선순위 해석에는 쓰지 않는다."""

    test_id: Candidate | None = None
    role: str | None = Field(default=None, max_length=100)
    accessible_name: str | None = Field(default=None, max_length=2000)
    role_status: CandidateStatus | None = None
    """role + accessible_name 짝에 대한 검증 결과."""

    label: Candidate | None = None
    text: Candidate | None = None
    stable_attr: StableAttr | None = None
    css: Candidate | None = None

    def model_post_init(self, _ctx: object) -> None:
        if not self.any_candidate_present():
            msg = "TargetLocator 는 후보를 최소 1개 가져야 한다 (FR-017)"
            raise ValueError(msg)

    def any_candidate_present(self) -> bool:
        """값이 있는 후보가 하나라도 있는가. 검증 통과 여부는 보지 않는다."""
        return any(
            (
                self.test_id is not None,
                self.role is not None and self.accessible_name is not None,
                self.label is not None,
                self.text is not None,
                self.stable_attr is not None,
                self.css is not None,
            )
        )

    def usable_candidate_count(self) -> int:
        """기록 시점 검증을 통과한 후보 수. SC-008 측정에 쓴다."""
        n = 0
        if self.test_id is not None and self.test_id.usable:
            n += 1
        if (
            self.role is not None
            and self.accessible_name is not None
            and self.role_status is CandidateStatus.VERIFIED
        ):
            n += 1
        for c in (self.label, self.text, self.css):
            if c is not None and c.usable:
                n += 1
        if self.stable_attr is not None and self.stable_attr.usable:
            n += 1
        return n
