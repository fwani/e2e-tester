/* eslint-disable */
/**
 * 이 파일은 backend/schema/*.schema.json 에서 자동 생성됐다. 손으로 고치지 마세요.
 * 권위 정의: backend/src/itb/domain/*.py (Pydantic v2)
 * 재생성: cd backend && uv run python -m itb.schema.export && cd ../frontend && npm run gen:types
 */

export type BrowserKind = "chromium";
export type DefaultStartUrl = string;
export type MaxTabs = number;
export type Name = string;
export type NextTestNumber = number;
export type TestIdAttribute = string;

/**
 * 테스트를 담는 최상위 단위. 프로젝트 하나 = 디렉터리 하나.
 */
export interface Project {
  browser: BrowserKind;
  default_start_url: DefaultStartUrl;
  max_tabs: MaxTabs;
  name: Name;
  next_test_number: NextTestNumber;
  test_id_attribute: TestIdAttribute;
}
