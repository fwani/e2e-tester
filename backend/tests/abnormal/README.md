# 이상 경로 검증 (003 라운드)

`specs/003-error-path-hardening` 의 검증이다. 이 디렉터리의 규칙 셋.

## 1. 시나리오 목록은 한 곳뿐이다

권위 목록: `specs/003-error-path-hardening/contracts/abnormal-scenarios.json`

**여기에 복사본을 두지 않는다.** 백엔드 검증(`catalogue.py`)과 화면 검증
(`frontend/tests/abnormal/catalogue.ts`)이 같은 파일을 읽는다. 두 벌이 되면
조합 커버리지가 갈라진다 (research R3).

## 2. 판정은 3축이다

시나리오 하나는 **축 셋을 모두 통과할 때만** 통과다 (`data-model.md` §2.3).

| 축 | 통과 조건 |
|---|---|
| ① 응답의 형태 | 오류 스키마를 만족하고 `category`·`next_action` 이 있으며 내부 경로·스택이 없다. `must_be_rejected` 인데 성공하면 실패(조용한 성공) |
| ② 사용자 관점 | 결과가 화면에 드러나고 무엇이 잘못됐는지와 다음 행동이 존재한다 |
| ③ 상태 보존 | `preserves` 가 가리키는 것이 조작 뒤에도 남아 있다 |

시나리오마다 기대 응답 코드·메시지를 적지 않는다. 구현이 틀리면 기대값도 같이 틀린다.

## 3. 실패 주입은 검증 코드에만 둔다

제품에 "실패 주입 모드" 스위치를 넣지 않는다. AI 대역은 `fakes.py` 에 두고
`itb.llm.client.create_client` 를 대체한다 (헌법 원칙 II).
