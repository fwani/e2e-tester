"""019 T036 (C2) — 왕복 무결성.

**헌법 품질 게이트 2 가 이 기능에 직접 걸린다.** 이 기능이 새 왕복을 만들었다 —
`store → export bundle → import → store`. 잃는 것이 있으면 여기서 드러나야 한다.

가장 중요한 단언은 **로케이터 후보가 전부 살아남는다**는 것이다 (헌법 원칙 IV). 축약하면
받은 쪽의 복원력이 보낸 쪽보다 낮아지고, 그것은 「같은 테스트」가 아니다.
"""

from __future__ import annotations

from fastapi.testclient import TestClient
from sharing_support import (
    COMMIT,
    PLAN,
    check,
    click,
    export_bundle,
    fill,
    make_secret_test,
    make_test,
    navigate,
    repo_of,
    write_tests,
)

from itb.domain.locator import Candidate, CandidateStatus, TargetLocator
from itb.domain.step import ClickStep
from itb.domain.test_case import TestGroup


def _rich_test(test_id: str = "TC-001"):
    """후보를 여러 개 가진 스텝 — 축약이 일어나면 드러난다."""
    target = TargetLocator(
        tag="button",
        test_id=Candidate(value="login-submit", status=CandidateStatus.VERIFIED),
        role="button",
        accessible_name="로그인",
        role_status=CandidateStatus.VERIFIED,
        text=Candidate(value="로그인", status=CandidateStatus.AMBIGUOUS),
        css=Candidate(value="button#login", status=CandidateStatus.VERIFIED),
    )
    return make_test(
        test_id,
        "로그인 확인",
        steps=[
            fill(1, "아이디 입력", "platform-user"),
            ClickStep(id="step-02", label="로그인", target=target),
            navigate(3, "대시보드로", "https://example.internal/dashboard"),
            check(4, "환영 문구", "환영합니다"),
        ],
    )


def _roundtrip(client: TestClient, name: str = "team.itbshare.yaml") -> dict:
    data = export_bundle(client)
    plan = client.post(
        f"{PLAN}?target=new",
        files={"file": (name, data, "application/yaml")},
    )
    assert plan.status_code == 201, plan.text
    report = client.post(COMMIT, json={"plan_id": plan.json()["plan_id"]})
    assert report.status_code == 201, report.text
    return report.json()


class RoundTripTests:
    def test_스텝이_로케이터_후보까지_그대로다(self, project_client: TestClient) -> None:
        """헌법 원칙 IV — 축약하면 받은 쪽이 보낸 쪽보다 약해진다."""
        original = _rich_test()
        write_tests(project_client, original)

        _roundtrip(project_client)

        restored = repo_of(project_client).read_test("TC-001")
        assert [s.model_dump(mode="json") for s in restored.steps] == [
            s.model_dump(mode="json") for s in original.steps
        ]

    def test_프로젝트_설정이_따라온다(self, project_client: TestClient) -> None:
        write_tests(project_client, make_test("TC-001", "로그인"))
        before = repo_of(project_client).read_project()

        _roundtrip(project_client)

        after = repo_of(project_client).read_project()
        assert after.default_start_url == before.default_start_url
        assert after.test_id_attribute == before.test_id_attribute
        assert after.browser == before.browser

    def test_그룹_구성이_따라온다(self, project_client: TestClient) -> None:
        project_client.post("/api/groups", json={"prefix": "USER", "name": "사용자관리"})
        write_tests(project_client, make_test("USER-001", "회원 가입"))

        _roundtrip(project_client)

        groups = repo_of(project_client).read_project().groups
        assert TestGroup(prefix="USER", name="사용자관리") in groups

    def test_민감_변수는_이름만_따라오고_값은_비어_있다(self, keyed_client: TestClient) -> None:
        """값을 옮기지 않고 요구를 옮긴다 — 이 기능의 중심이다."""
        from sharing_support import seal_secret

        write_tests(keyed_client, make_secret_test())
        seal_secret(keyed_client, "SECRET_LOGIN_PW")

        report = _roundtrip(keyed_client)

        restored = repo_of(keyed_client).read_test("TC-001")
        (var,) = [v for v in restored.variables if v.name == "SECRET_LOGIN_PW"]
        assert var.sensitive is True
        assert var.value is None
        # 새 프로젝트에는 암호문이 없다 — 받은 사람이 채워야 한다.
        assert repo_of(keyed_client).paths.secrets_file.exists() is False
        assert [v["name"] for v in report["required_values"]] == ["SECRET_LOGIN_PW"]

    def test_여러_건과_여러_그룹이_함께_돈다(self, project_client: TestClient) -> None:
        project_client.post("/api/groups", json={"prefix": "USER", "name": "사용자관리"})
        project_client.post("/api/groups", json={"prefix": "DATA", "name": "데이터"})
        write_tests(
            project_client,
            make_test("TC-001", "가"),
            make_test("USER-001", "나"),
            make_test("USER-002", "다"),
            make_test("DATA-001", "라"),
        )

        _roundtrip(project_client)

        tests, problems = repo_of(project_client).list_tests()
        assert problems == []
        assert {t.id for t in tests} == {"TC-001", "USER-001", "USER-002", "DATA-001"}

    def test_가져온_것을_다시_내보내면_출처가_따라가지_않는다(
        self, project_client: TestClient
    ) -> None:
        """A→B→C 로 전달될 때 B 의 기록이 C 에게 갈 이유가 없다 (research R9)."""
        write_tests(project_client, make_test("TC-001", "로그인"))
        _roundtrip(project_client, name="첫-묶음.itbshare.yaml")

        assert repo_of(project_client).read_test("TC-001").imported_from is not None

        second = export_bundle(project_client)
        assert b"\xec\xb2\xab-\xeb\xac\xb6\xec\x9d\x8c" not in second  # "첫-묶음"
        assert "imported_from: null" in second.decode("utf-8")

    def test_클릭_전용_테스트도_손실이_없다(self, project_client: TestClient) -> None:
        write_tests(
            project_client,
            make_test("TC-001", "클릭만", steps=[click(1, "가"), click(2, "나")]),
        )
        original = repo_of(project_client).read_test("TC-001")

        _roundtrip(project_client)

        restored = repo_of(project_client).read_test("TC-001")
        assert restored.model_dump(mode="json", exclude={"imported_from", "updated_at"}) == (
            original.model_dump(mode="json", exclude={"imported_from", "updated_at"})
        )
