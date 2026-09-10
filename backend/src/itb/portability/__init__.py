"""남의 파일 형식과 이 제품 사이의 통로 (기능 014).

이 패키지는 **스프레드시트(.xlsx)** 를 읽고 쓴다. 우리 자산 형식(YAML)은 여기가 아니라
:mod:`itb.storage` 가 맡는다. 둘을 같은 곳에 두면 "정본이 무엇인가"가 코드 배치에서
흐려지고, 그것은 헌법 원칙 V 가 걸린 지점이다.

**워크북은 저장 형식이 아니라 파생 산출물이다.** 내보낸 파일을 고쳐서 다시 넣어도 이미
저장된 테스트의 스텝은 바뀌지 않는다. 가져오기가 만드는 것은 :class:`itb.domain.draft.Draft`
이며, 그것은 테스트가 아니다 — 스텝이 없고 실행할 수 없다.

**이 패키지는 :mod:`itb.authoring` 과 :mod:`itb.llm` 을 임포트할 수 없다.**
``backend/.importlinter`` 의 ``execution-no-llm`` 계약이 막는다. "가져오면서 바로 AI 를
돌린다"는 지름길이 생기면 스프레드시트가 테스트의 두 번째 작성 경로가 되고, 그것은
원칙 I 을 깬다. 주석이 아니라 빌드가 막게 해 둔 이유다.

구성:

- :mod:`~itb.portability.limits` — 이 기능 고유 상한. 제품 공통 상한은 여기서 정의하지 않는다
- :mod:`~itb.portability.columns` — 7개 컬럼의 단일 출처. 내보내기와 가져오기가 함께 쓴다
- :mod:`~itb.portability.sheet_name` — 그룹 이름 ↔ 시트 이름 변환 (순수 함수)
- :mod:`~itb.portability.workbook` — openpyxl 과 닿는 유일한 지점
- :mod:`~itb.portability.exporter` — 프로젝트 → 시트·행
- :mod:`~itb.portability.importer` — 워크북 → 가져오기 계획
"""
