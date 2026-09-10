/* eslint-disable */
/**
 * 이 파일은 backend/schema/*.schema.json 에서 자동 생성됐다. 손으로 고치지 마세요.
 * 권위 정의: backend/src/itb/domain/*.py (Pydantic v2)
 * 재생성: cd backend && uv run python -m itb.schema.export && cd ../frontend && npm run gen:types
 */

export type BrowserKind = "chromium";
export type DefaultStartUrl = string;
export type Name = string;
export type Prefix = string;
export type Groups = TestGroup[];
export type MaxTabs = number;
export type Name1 = string;
export type NextTestNumber = number;
export type TestIdAttribute = string;

/**
 * 테스트를 담는 최상위 단위. 프로젝트 하나 = 디렉터리 하나.
 */
export interface Project {
  browser: BrowserKind;
  default_start_url: DefaultStartUrl;
  groups: Groups;
  max_tabs: MaxTabs;
  name: Name1;
  next_test_number: NextTestNumber;
  test_id_attribute: TestIdAttribute;
}
/**
 * 한 프로젝트 안에서 테스트를 묶는 것 (013 FR-438·FR-444d).
 *
 * **보이는 이름과 식별자 접두어를 따로 갖는다.** 이름은 사람이 읽는 것이고
 * (「사용자관리 테스트」), 접두어는 식별자에 들어가는 짧은 값이다 (`USER`). 이름에서
 * 접두어를 자동으로 뽑지 않는 이유는 이름이 한글일 수 있기 때문이다 — 그대로 쓰면
 * 식별자가 `사용자관리-001` 로 길어지고, 로마자로 바꾸면 사용자가 예측하지 못하는 값이
 * 나온다 (013 clarify).
 *
 * **소속을 테스트에 저장하지 않는다.** 식별자의 접두어가 곧 소속이다 — 둘을 다 저장하면
 * 어긋날 수 있고, 어긋났을 때 어느 쪽이 맞는지 정할 근거가 없다 (013 data-model §3).
 */
export interface TestGroup {
  name: Name;
  prefix: Prefix;
}
