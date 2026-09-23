/* eslint-disable */
/**
 * 이 파일은 backend/schema/*.schema.json 에서 자동 생성됐다. 손으로 고치지 마세요.
 * 권위 정의: backend/src/itb/domain/*.py (Pydantic v2)
 * 재생성: cd backend && uv run python -m itb.schema.export && cd ../frontend && npm run gen:types
 */

export type BundleVersion = number;
export type CreatedAt = string;
export type Generator = string;
export type BrowserKind = "chromium";
export type DefaultStartUrl = string;
export type Name = string;
export type Prefix = string;
/**
 * @maxItems 100
 */
export type Groups = TestGroup[];
export type MaxTabs = number;
export type Name1 = string;
export type TestIdAttribute = string;
export type Declared = boolean;
export type Name2 = string;
export type Sensitive = boolean;
/**
 * @minItems 1
 */
export type Usages = [ValueUsage, ...ValueUsage[]];
export type Field = string;
export type StepId = string;
export type StepLabel = string | null;
export type TestId = string;
export type RequiredValues = RequiredValue[];
/**
 * @minItems 1
 * @maxItems 2000
 */
export type Tests = [Test, ...Test[]];
export type Actor = string | null;
export type AiInstruction = string | null;
/**
 * 작성 방식. **테스트를 시작한 방식**으로 결정하며 이후 바뀌지 않는다 (FR-002a).
 */
export type AuthoringMode = "record" | "ai";
export type BrowserKind1 = "chromium";
export type CreatedAt1 = string;
export type Description = string | null;
export type DslVersion = number;
export type Id = string;
export type ImportedAt = string;
export type OriginalId = string;
export type SourceFile = string;
export type Name3 = string;
export type StartUrl = string;
/**
 * @minItems 1
 */
export type Steps = [
  ClickStep | FillStep | SelectStep | NavigateStep | AssertionStep | CloseTabStep | HoverStep | DragStep | UploadStep,
  ...(
    ClickStep | FillStep | SelectStep | NavigateStep | AssertionStep | CloseTabStep | HoverStep | DragStep | UploadStep
  )[]
];
export type Author = "human" | "ai";
export type FrameUrl = string | null;
export type Id1 = string;
export type Label = string;
export type Tab = number;
export type AccessibleName = string | null;
/**
 * 기록 시점 검증 결과. research R4 실측으로 ``AMBIGUOUS`` 가 추가됐다.
 */
export type CandidateStatus = "verified" | "ambiguous" | "unverified" | "not_collected";
export type Value = string;
export type Role = string | null;
export type Name4 = string;
export type Value1 = string;
export type Tag = string | null;
export type TimeoutMs = number;
export type Type = "click";
export type Author1 = "human" | "ai";
export type FrameUrl1 = string | null;
export type Id2 = string;
export type Label1 = string;
export type Tab1 = number;
export type TimeoutMs1 = number;
export type Type1 = "fill";
export type Value2 = string;
export type Author2 = "human" | "ai";
export type FrameUrl2 = string | null;
export type Id3 = string;
export type Label2 = string;
export type Tab2 = number;
export type TimeoutMs2 = number;
export type Type2 = "select";
export type Value3 = string;
export type Author3 = "human" | "ai";
export type FrameUrl3 = string | null;
export type Id4 = string;
export type Label3 = string;
export type Tab3 = number;
export type TimeoutMs3 = number;
export type Type3 = "navigate";
export type Url = string;
export type AssertionKind = "visible" | "hidden" | "text" | "url";
export type MatchMode = "equals" | "contains";
export type Value4 = string | null;
export type Author4 = "human" | "ai";
export type FrameUrl4 = string | null;
export type Id5 = string;
export type Label4 = string;
export type Tab4 = number;
export type TimeoutMs4 = number;
export type Type4 = "assertion";
export type Author5 = "human" | "ai";
export type FrameUrl5 = string | null;
export type Id6 = string;
export type Label5 = string;
export type Tab5 = number;
export type TimeoutMs5 = number;
export type Type5 = "close_tab";
export type Author6 = "human" | "ai";
export type FrameUrl6 = string | null;
export type Id7 = string;
export type Label6 = string;
export type Tab6 = number;
export type TimeoutMs6 = number;
export type Type6 = "hover";
export type Author7 = "human" | "ai";
export type FrameUrl7 = string | null;
export type Id8 = string;
export type Label7 = string;
export type Tab7 = number;
export type TimeoutMs7 = number;
export type Type7 = "drag";
export type Author8 = "human" | "ai";
export type FileName = string;
export type FrameUrl8 = string | null;
export type Id9 = string;
export type Label8 = string;
export type Tab8 = number;
export type TimeoutMs8 = number;
export type Type8 = "upload";
export type UpdatedAt = string;
export type Name5 = string;
export type Sensitive1 = boolean;
export type Value5 = string | null;
export type Variables = Variable[];

/**
 * 전달 가능한 파일 하나의 내용 전체.
 */
export interface ShareBundle {
  bundle_version: BundleVersion;
  created_at: CreatedAt;
  generator: Generator;
  project: BundleProject;
  required_values: RequiredValues;
  tests: Tests;
}
/**
 * 묶음이 나르는 프로젝트 설정 (data-model §2.2).
 *
 * :class:`itb.domain.test_case.Project` 에서 ``next_test_number`` 를 뺀 것이다. 그 필드는
 * 이미 쓰이지 않는 하위 호환 잔재이며(도메인 주석), 묶음에 실으면 새 형식이 옛 잔재를
 * 물려받는다.
 */
export interface BundleProject {
  browser: BrowserKind;
  default_start_url: DefaultStartUrl;
  groups: Groups;
  max_tabs: MaxTabs;
  name: Name1;
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
/**
 * 받는 사람이 **채워야 실행되는 것** 하나 (FR-040 · data-model §2.3).
 *
 * 민감한 것과 그렇지 않은 것을 한 모델에 둔다. 받는 사람에게는 둘 다 "비어 있어서 채워야
 * 하는 것" 이고, 다른 것은 저장 위치뿐이다 — 민감한 것은 봉인 저장소로, 그렇지 않은 것은
 * 테스트 정의로 간다 (FR-048).
 */
export interface RequiredValue {
  declared: Declared;
  name: Name2;
  sensitive: Sensitive;
  usages: Usages;
}
/**
 * 어떤 변수가 **어디서** 쓰이는지 (FR-040).
 *
 * 이름만 보여 주면 받는 사람은 무엇을 넣을지 모른다. 「TC-001 의 '비밀번호 입력' 스텝」
 * 까지 보여야 자기 계정의 어떤 값인지 판단할 수 있다.
 */
export interface ValueUsage {
  field: Field;
  step_id: StepId;
  step_label: StepLabel;
  test_id: TestId;
}
/**
 * 하나의 테스트 시나리오. `tests/` 아래 YAML 파일 하나에 대응한다.
 */
export interface Test {
  actor: Actor;
  ai_instruction: AiInstruction;
  authoring_mode: AuthoringMode;
  browser: BrowserKind1;
  created_at: CreatedAt1;
  description: Description;
  dsl_version: DslVersion;
  id: Id;
  imported_from: ImportProvenance | null;
  name: Name3;
  start_url: StartUrl;
  steps: Steps;
  updated_at: UpdatedAt;
  variables: Variables;
}
/**
 * 이 테스트가 공유 묶음에서 왔다는 표시 (019 FR-028).
 *
 * **실행에 관여하지 않는다.** 헌법 원칙 I 은 provenance 를 메타데이터로 기록하는 것을
 * 명시적으로 허용하되, 그것이 Step 의 실행 방식을 바꾸지 못하게 한다. 이 모델은 그
 * 경계 안에 있다 — 러너도 생성기도 이 값을 읽지 않는다.
 *
 * **묶음에 실을 때는 비운다** (019 R9). A→B→C 로 전달될 때 B 의 가져오기 기록이 C 에게
 * 갈 이유가 없고, 파일 이름이 사내 경로를 흘릴 수 있다.
 *
 * 사이드카 파일로 빼지 않는 이유는 **묶음이 사라진 뒤에도 알아야** 하기 때문이다.
 * 반년 뒤 "이 테스트 어디서 왔지" 의 답은 테스트 파일 안에 있어야 한다.
 */
export interface ImportProvenance {
  imported_at: ImportedAt;
  original_id: OriginalId;
  source_file: SourceFile;
}
export interface ClickStep {
  author: Author;
  frame_url: FrameUrl;
  id: Id1;
  label: Label;
  tab: Tab;
  target: TargetLocator;
  timeout_ms: TimeoutMs;
  type: Type;
}
/**
 * 한 요소에 대한 식별 후보 묶음.
 *
 * **불변식**: 후보가 하나도 없는 ``TargetLocator`` 는 유효하지 않다.
 * 최소한 ``css`` 는 항상 수집된다.
 */
export interface TargetLocator {
  accessible_name: AccessibleName;
  css: Candidate | null;
  label: Candidate | null;
  role: Role;
  role_status: CandidateStatus | null;
  stable_attr: StableAttr | null;
  tag: Tag;
  test_id: Candidate | null;
  text: Candidate | null;
}
/**
 * 식별 후보 하나.
 */
export interface Candidate {
  status: CandidateStatus;
  value: Value;
}
/**
 * `[name="value"]` 형태로 쓰는 안정적 속성.
 */
export interface StableAttr {
  name: Name4;
  status: CandidateStatus;
  value: Value1;
}
export interface FillStep {
  author: Author1;
  frame_url: FrameUrl1;
  id: Id2;
  label: Label1;
  tab: Tab1;
  target: TargetLocator;
  timeout_ms: TimeoutMs1;
  type: Type1;
  value: Value2;
}
export interface SelectStep {
  author: Author2;
  frame_url: FrameUrl2;
  id: Id3;
  label: Label2;
  tab: Tab2;
  target: TargetLocator;
  timeout_ms: TimeoutMs2;
  type: Type2;
  value: Value3;
}
export interface NavigateStep {
  author: Author3;
  frame_url: FrameUrl3;
  id: Id4;
  label: Label3;
  tab: Tab3;
  timeout_ms: TimeoutMs3;
  type: Type3;
  url: Url;
}
export interface AssertionStep {
  assertion: Assertion;
  author: Author4;
  frame_url: FrameUrl4;
  id: Id5;
  label: Label4;
  tab: Tab4;
  timeout_ms: TimeoutMs4;
  type: Type4;
}
/**
 * 검증 Step 의 조건.
 */
export interface Assertion {
  kind: AssertionKind;
  match: MatchMode;
  target: TargetLocator | null;
  value: Value4;
}
/**
 * 탭 닫기 (FR-030c). 대상은 공통 ``tab`` 필드가 가리킨다.
 */
export interface CloseTabStep {
  author: Author5;
  frame_url: FrameUrl5;
  id: Id6;
  label: Label5;
  tab: Tab5;
  timeout_ms: TimeoutMs5;
  type: Type5;
}
/**
 * 마우스를 올리는 동작 (FR-023c).
 *
 * **화면을 바꾼 hover 만 기록한다.** 포인터가 지나간 모든 요소를 Step 으로 만들면 정의가
 * 쓸모없이 길어지고, 어느 hover 가 의미 있었는지 사람이 다시 판단해야 한다. 리코더는
 * hover 직후 문서 변화가 관측된 경우만 이 Step 을 만든다 (contracts/step-dsl.md).
 */
export interface HoverStep {
  author: Author6;
  frame_url: FrameUrl6;
  id: Id7;
  label: Label6;
  tab: Tab6;
  target: TargetLocator;
  timeout_ms: TimeoutMs6;
  type: Type6;
}
/**
 * 끌어다 놓는 동작 (FR-023c).
 *
 * ``target`` 이 끄는 대상이고 ``drop_target`` 이 놓는 위치다. 다른 Step 과 마찬가지로
 * ``target`` 이 주된 대상이므로 `target_of` 가 그대로 동작한다.
 */
export interface DragStep {
  author: Author7;
  drop_target: TargetLocator;
  frame_url: FrameUrl7;
  id: Id8;
  label: Label7;
  tab: Tab7;
  target: TargetLocator;
  timeout_ms: TimeoutMs7;
  type: Type7;
}
/**
 * 파일을 올리는 동작 (2026-09-09 사용자 보고).
 *
 * ## 무엇을 기록하는가 — **파일 이름 하나다**
 *
 * 사용자가 요구한 것은 확장자다: 「파일업로드 녹화의 경우, 파일의 확장자 기록되 되어야함.
 * 실제 서비스에서는 확장자를 보는경우가 있기 때문」.
 *
 * 그래서 이 Step 은 ``file_name`` 을 갖고, **확장자는 그 이름의 일부다.** 확장자를 별도
 * 필드로 두지 않는 이유는 진실이 둘이 되기 때문이다 — 이름이 ``보고서.xlsx`` 인데
 * 확장자 필드가 ``csv`` 인 Step 이 만들어질 수 있고, 그때 어느 쪽이 맞는지 아무도 모른다.
 * 확장자가 필요한 곳은 `extension_of` 로 꺼낸다.
 *
 * **파일 내용은 기록하지 않는다.** 녹화 시점에 브라우저가 주는 것은 이름뿐이고
 * (``File.name``), 내용을 정의 파일에 담으면 테스트가 옮겨 다닐 수 없게 된다. 재실행은
 * 같은 이름의 빈 파일을 만들어 올린다 — 확장자를 보는 검증은 통과하고, 내용을 파싱하는
 * 검증은 통과하지 못한다. 그 한계는 실행기 쪽에 적어 두었다.
 */
export interface UploadStep {
  author: Author8;
  file_name: FileName;
  frame_url: FrameUrl8;
  id: Id9;
  label: Label8;
  tab: Tab8;
  target: TargetLocator;
  timeout_ms: TimeoutMs8;
  type: Type8;
}
/**
 * 테스트 안에서 값을 대신하는 이름.
 */
export interface Variable {
  name: Name5;
  sensitive: Sensitive1;
  value: Value5;
}
