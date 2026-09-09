/**
 * 주입 리코더. research R2 (T004 로 실측 확인).
 *
 * BrowserContext.add_init_script 로 주입되므로 모든 새 document·frame·탭에서 실행된다.
 * 그래서 멀티 탭(FR-030)이 별도 코드 없이 따라온다.
 *
 * **입력은 키 단위가 아니라 확정된 값을 잡는다.** `change`/`blur` 로 잡으면 한글 IME 조합
 * 중인 자모가 아니라 조합이 끝난 최종 값이 한 번에 온다. `keydown` 을 쓰면 조합
 * 완료 값을 재구성해야 한다.
 *
 * **실측 보강**: `change` 와 `blur` 가 둘 다 발생한다. 텍스트 입력 한 번이 이벤트 2건을
 * 만들므로 Python 측에서 같은 요소 기준 중복 제거가 필요하다 (FR-025).
 *
 * **`change`·`blur` 만으로는 부족하다 (US2 재실행에서 드러난 문제).** 마지막으로 입력한
 * 필드는 포커스가 떠날 때까지 확정 이벤트를 내지 않는다. 그 포커스 이동이 보통 "다음
 * 버튼 클릭"이므로, 확정 이벤트가 **화면 이동과 동시에** 도착한다. 그 시점에는 요소
 * 후보를 검증할 수 없어(문서가 교체된다) 모든 후보가 `not_collected` 로 남고, 저장된
 * 테스트가 재실행 불가 상태가 된다. 그래서 조합이 끝난 `input` 도 디바운스해서 보낸다 —
 * 값은 나중 확정 이벤트가 덮어쓰고, **후보 검증만 미리 끝내 둔다.**
 *
 * **클릭은 `pointerdown` 에서 잡는다.** `click` 리스너는 앱의 클릭 핸들러와 같은 디스패치
 * 안에서 돌기 때문에, 우리가 후보를 검증하기 전에 `location.href` 가 이미 설정된다.
 * `pointerdown` 은 그보다 앞서므로 검증이 화면 이동을 앞지른다. 키보드 활성화(Enter·Space)는
 * 포인터 이벤트를 내지 않으므로 `click` 도 계속 듣고, 중복은 Python 이 접는다.
 */
(() => {
  if (window.__itbInstalled) return;
  window.__itbInstalled = true;

  const MAX_TEXT = 200;

  const send = (payload) => {
    try {
      if (typeof window.__itbRecord === "function") {
        window.__itbRecord(payload);
      }
    } catch {
      /* 바인딩이 아직 준비되지 않았거나 페이지가 사라지는 중이면 무시한다. */
    }
  };

  const clean = (value) => {
    if (typeof value !== "string") return null;
    const text = value.replace(/\s+/g, " ").trim();
    if (!text || text.length > MAX_TEXT) return null;
    return text;
  };

  /** 태그·타입에서 암시적 ARIA role 을 추정한다. */
  const implicitRole = (el) => {
    const tag = el.tagName.toLowerCase();
    const type = (el.getAttribute("type") || "").toLowerCase();
    if (tag === "a") return el.hasAttribute("href") ? "link" : null;
    if (tag === "button") return "button";
    if (tag === "select") return "combobox";
    if (tag === "textarea") return "textbox";
    if (tag === "h1" || tag === "h2" || tag === "h3" || tag === "h4") return "heading";
    if (tag === "input") {
      if (["button", "submit", "reset", "image"].includes(type)) return "button";
      if (type === "checkbox") return "checkbox";
      if (type === "radio") return "radio";
      if (type === "search") return "searchbox";
      return "textbox";
    }
    if (tag === "nav") return "navigation";
    if (tag === "table") return "table";
    return null;
  };

  /**
   * 접근성 이름을 근사 계산한다.
   *
   * CDP Accessibility.getPartialAXTree 가 더 권위 있지만 클릭마다 왕복이 필요하다.
   * Python 측의 기록 시점 검증이 근사 계산의 오류를 잡아 주므로 근사로 충분하다 (research R4).
   */
  const accessibleName = (el) => {
    const aria = clean(el.getAttribute("aria-label"));
    if (aria) return aria;

    const labelledBy = el.getAttribute("aria-labelledby");
    if (labelledBy) {
      const parts = labelledBy
        .split(/\s+/)
        .map((id) => document.getElementById(id))
        .filter(Boolean)
        .map((node) => node.textContent || "");
      const joined = clean(parts.join(" "));
      if (joined) return joined;
    }

    if (el.labels && el.labels.length > 0) {
      const fromLabel = clean(el.labels[0].textContent);
      if (fromLabel) return fromLabel;
    }

    const own = clean(el.textContent);
    if (own) return own;

    for (const attr of ["alt", "title", "placeholder", "value"]) {
      const v = clean(el.getAttribute(attr));
      if (v) return v;
    }
    return null;
  };

  /** 연결된 <label> 의 텍스트. get_by_label 후보다. */
  const associatedLabel = (el) => {
    if (el.labels && el.labels.length > 0) return clean(el.labels[0].textContent);
    const id = el.getAttribute("id");
    if (id) {
      const l = document.querySelector(`label[for="${CSS.escape(id)}"]`);
      if (l) return clean(l.textContent);
    }
    const parent = el.closest("label");
    if (parent) return clean(parent.textContent);
    return null;
  };

  const cssEscape = (value) =>
    typeof CSS !== "undefined" && CSS.escape ? CSS.escape(value) : value.replace(/"/g, '\\"');

  /** 누적 경로가 그 요소 **하나만** 가리키는가. */
  const matchesOnly = (selector, el) => {
    try {
      const nodes = document.querySelectorAll(selector);
      return nodes.length === 1 && nodes[0] === el;
    } catch {
      return false;
    }
  };

  /**
   * CSS 경로. **최후 후보이며 항상 수집한다** — 다른 후보가 모두 없어도
   * TargetLocator 불변식(후보 최소 1개)을 만족시켜야 한다.
   *
   * **깊이 상한을 두면 안 된다.** 상한에 걸린 경로는 `main > section > div > button` 처럼
   * 문서 어디에나 맞는 **상대 경로**가 되어 여러 요소를 매칭하고, CSS 후보가 `ambiguous`
   * 로 버려진다. 실측에서 같은 구조가 두 번 나오는 화면(카드 두 장, 목록 두 줄)의 버튼이
   * 확보 후보 0개로 기록됐고, 그 Step 은 재실행에서 반드시 "요소를 찾지 못했다" 로 끝났다.
   *
   * 대신 **유일해지는 즉시 멈춘다.** 짧은 경로가 화면 구조 변화에 덜 깨지므로, 조상까지
   * 다 붙인 절대 경로는 유일성을 얻지 못했을 때만 나온다.
   *
   * 한계: shadow DOM 안의 요소는 `document.querySelectorAll` 로 확인되지 않으므로 경로가
   * shadow 경계에서 끊긴 채 `not_collected` 로 기록된다. 그 경로는 `role`·`text` 후보가
   * 담당한다.
   */
  const cssPath = (el) => {
    const parts = [];
    let node = el;
    while (node && node.nodeType === 1) {
      // 태그 이름을 소문자로 바꾸지 않는다. SVG 는 HTML 과 달리 태그 이름의 대소문자를
      // 구별하므로 `clipPath` 를 `clippath` 로 적으면 맞지 않는다.
      const name = node.localName || node.tagName.toLowerCase();
      const id = node.getAttribute("id");
      // 난수처럼 보이는 id 는 안정적이지 않으므로 쓰지 않는다.
      if (id && !/\d{4,}|[0-9a-f]{8,}/i.test(id)) {
        parts.unshift(`${name}#${cssEscape(id)}`);
        break; // id 는 문서에서 유일해야 하므로 더 올라갈 이유가 없다
      }
      let part = name;
      const parent = node.parentElement;
      if (parent) {
        const siblings = Array.from(parent.children).filter((c) => c.localName === name);
        if (siblings.length > 1) {
          part += `:nth-of-type(${siblings.indexOf(node) + 1})`;
        }
      }
      parts.unshift(part);
      if (matchesOnly(parts.join(" > "), el)) break;
      node = parent;
    }
    return parts.join(" > ");
  };

  const COLLECTED_ATTRS = [
    "data-testid",
    "data-test",
    "data-test-id",
    "data-cy",
    "data-qa",
    "data-id",
    "data-name",
    "data-role",
    "name",
    "aria-label",
    "role",
    "type",
  ];

  /**
   * **후보 검증을 페이지 안에서 즉시 한다 (CSS·testId 에 한해).**
   *
   * 문제: 클릭 후보 검증을 Python 이 하면 왕복 사이에 앱이 `location.href` 를 설정해
   * 문서가 교체된다. 그러면 모든 후보가 `not_collected` 로 남아 저장된 Step 이 재실행
   * 불가가 된다 — SC-008 측정이 이것을 잡았다.
   *
   * 여기서 재는 것은 **CSS 선택자와 testId 속성 선택자뿐이다.** 두 후보는
   * `querySelectorAll` 과 Playwright 의 해석이 정확히 같다. `role`·`label`·`text` 는
   * Playwright 가 고유한 매칭 규칙(접근 이름 계산, 텍스트 정규화, 완전 일치)을 쓰므로
   * 여기서 근사하면 **다른 요소를 가리키는 후보를 `verified` 로 적을 수 있다** — 실패보다
   * 나쁘다. 그 셋은 Python 이 Playwright 로 검증한다.
   */
  const statusOf = (selector, el) => {
    if (!selector) return null;
    let nodes;
    try {
      nodes = document.querySelectorAll(selector);
    } catch {
      return "not_collected";
    }
    if (nodes.length === 0) return "not_collected";
    if (nodes.length > 1) return "ambiguous";
    return nodes[0] === el ? "verified" : "unverified";
  };

  const testIdAttribute = () => {
    const configured = window.__itbConfig && window.__itbConfig.testIdAttribute;
    return typeof configured === "string" && configured ? configured : "data-testid";
  };

  /**
   * 후보 검증의 **기준 요소**를 Python 이 다시 찾지 않게 한다.
   *
   * Python 은 기준 요소를 `page.query_selector(css)` 로 다시 잡았다. CSS 후보가 여러
   * 요소를 매칭하면 그 재조회는 **다른 요소**를 돌려주고, 그 잘못된 기준으로 `role`·`text`
   * 후보를 검증하므로 맞는 후보까지 `unverified` 로 버려진다. 실측에서 같은 구조가 두 번
   * 나오는 화면의 버튼이 확보 후보 0개로 기록됐다.
   *
   * 그래서 설명할 때 요소 자체를 토큰과 함께 남기고, Python 은 토큰으로 그 요소의 핸들을
   * 받는다. 오래된 항목은 버린다 — 떼어낸 노드를 계속 붙들면 문서가 회수되지 않는다.
   */
  const REF_LIMIT = 32;
  const refs = new Map();
  let refSeq = 0;

  const register = (el) => {
    const token = `r${(refSeq += 1)}`;
    refs.set(token, el);
    if (refs.size > REF_LIMIT) refs.delete(refs.keys().next().value);
    return token;
  };

  window.__itbResolveRef = (token) => refs.get(token) || null;

  /**
   * 중복 제거의 기준이 되는 요소. **한 번의 조작이 내는 여러 이벤트를 한 묶음으로 묶는다.**
   *
   * `<label>` 을 누르면 브라우저가 연결된 컨트롤에 **클릭을 한 번 더 합성해 보낸다**
   * (label activation). 두 이벤트의 대상이 다르므로 요소별 중복 제거로는 접히지 않고, 한
   * 번의 클릭이 Step 두 개가 된다.
   *
   * 실측(TC-009): `Druid` 체크박스를 한 번 눌렀는데 Step 20(레이블)·21(입력)이 만들어졌고,
   * 재실행은 체크박스를 켰다가 **다시 껐다.** 게다가 실제 `<input class="checkbox-input">`
   * 은 `<button class="accordion-head">` 에 덮여 있어 두 번째 Step 은 10초를 쓰고 실패했다.
   * 정의가 두 배가 되는 문제가 아니라 **뜻이 뒤집히는** 문제다.
   *
   * 그래서 레이블과 컨트롤이 **같은 묶음 이름**을 갖게 한다. 이름은 컨트롤의 경로로 정한다 —
   * 컨트롤 쪽에서는 자기 경로, 레이블 쪽에서는 자기가 조작하는 컨트롤의 경로이므로 양쪽이
   * 같은 문자열을 만든다. 그러면 Python 의 중복 제거가 둘을 접고 **먼저 도착한 쪽**만
   * 남는데, 먼저 도착하는 것은 `pointerdown` 이 실제로 닿은 쪽이다.
   *
   * **먼저 도착한 쪽을 남기는 것이 맞다.** 사용자가 레이블을 눌렀으면 레이블이 보였다는
   * 뜻이고, 컨트롤을 직접 눌렀으면 컨트롤이 보였다는 뜻이다. 어느 쪽을 남길지 규칙으로
   * 정하면 위 실측처럼 **가려진 쪽**을 고를 수 있다.
   */
  const groupAnchor = (el) => {
    const control = el.localName === "label" ? el.control : el;
    if (!control || control.nodeType !== 1) return null;
    const labels = control.labels;
    if (!labels || labels.length === 0) return null;
    return control;
  };

  /** 이 요소 자체가 조작 대상인가. `actionTarget` 이 올라가 찾는 것과 같은 기준이다. */
  const isActionable = (el) => {
    try {
      return el.matches(ACTIONABLE) || el.matches(CLICKABLE);
    } catch {
      return false;
    }
  };

  /** 조작 대상을 **품고 있는** 껍데기인가. 목록·카드처럼 여백이 있는 컨테이너다. */
  const wrapsControls = (el) => {
    try {
      return el.querySelector(ACTIONABLE) !== null;
    } catch {
      return false;
    }
  };

  const describe = (el, options) => {
    const attributes = {};
    for (const attr of COLLECTED_ATTRS) {
      const v = el.getAttribute(attr);
      if (v !== null) attributes[attr] = v;
    }
    const css = cssPath(el);
    const attr = testIdAttribute();
    const testId = el.getAttribute(attr);
    const anchor = groupAnchor(el);
    return {
      // 레이블·컨트롤 쌍을 한 묶음으로 묶는 이름. 없으면 Python 이 `css` 로 떨어진다.
      // 컨트롤 자신에 대해서는 `css` 와 같은 값이 나오므로 기존 동작이 바뀌지 않는다.
      group: anchor === null ? null : anchor === el ? css : cssPath(anchor),
      // **여백을 누른 클릭을 가려내는 두 사실** (`Recorder._record_click` 참고).
      // 조작 대상이 아니면서 조작 대상을 품고 있으면 껍데기의 여백을 누른 것이다.
      actionable: isActionable(el),
      wrapsControls: wrapsControls(el),
      tag: el.tagName.toLowerCase(),
      // `observe_page` 는 요소를 200개까지 훑으므로 등록하지 않는다. 그 목록은 검증
      // 대상이 아니고, 등록하면 상한이 밀려 정작 필요한 동작 대상의 참조가 버려진다.
      ref: options && options.register === false ? null : register(el),
      role: clean(el.getAttribute("role")) || implicitRole(el),
      accessibleName: accessibleName(el),
      label: associatedLabel(el),
      text: clean(el.textContent),
      css,
      attributes,
      // 동작이 일어난 **그 순간**의 검증 결과. 화면이 교체된 뒤에는 다시 잴 수 없다.
      verified: {
        css: statusOf(css, el),
        test_id: testId ? statusOf(`[${attr}="${cssEscape(testId)}"]`, el) : null,
      },
    };
  };

  /**
   * 셀렉터로 요소를 설명한다. **Python 이 호출한다** — Assertion 대상 지정(FR-037)과
   * "다시 집기"(FR-020)가 같은 후보 수집 규칙을 지나게 하는 통로다.
   *
   * 별도 수집 코드를 Python 에 두면 녹화가 만드는 후보와 편집이 만드는 후보가 갈린다.
   * 원칙 IV 의 단일 지점은 우선순위 해석뿐 아니라 **수집 규칙**에도 적용된다.
   */
  window.__itbDescribe = (selector) => {
    try {
      const el = document.querySelector(selector);
      return el ? describe(el) : null;
    } catch {
      return null;
    }
  };

  /**
   * 상호작용 가능한 요소 목록. **AI 에이전트의 `observe_page` 가 쓴다** (research R5).
   *
   * 에이전트에게 CSS 셀렉터를 짜게 하지 않기 위한 장치다. 여기서 요소마다 `css` 를
   * 부여해 돌려주면, 에이전트는 그 참조만 지목하고 후보 수집·검증은 제품이 한다 —
   * 원칙 IV 가 AI 경로에서도 유지되는 이유다.
   *
   * **보이지 않는 요소는 빼지 않고 표시한다.** 목록에서 빼면 에이전트는 그 요소가 없다고
   * 판단해 다른 경로를 찾는데, 실제로는 hover 로 열리는 메뉴 안에 있을 수 있다.
   */
  window.__itbObserve = (limit) => {
    const max = typeof limit === "number" && limit > 0 ? limit : 200;
    const out = [];
    let nodes;
    try {
      nodes = document.querySelectorAll(INTERACTIVE);
    } catch {
      return { url: location.href, title: document.title, elements: [] };
    }
    for (const el of nodes) {
      if (out.length >= max) break;
      let rect;
      try {
        rect = el.getBoundingClientRect();
      } catch {
        rect = { width: 0, height: 0 };
      }
      const described = describe(el, { register: false });
      out.push({
        tag: described.tag,
        role: described.role,
        name: described.accessibleName || described.label || described.text,
        css: described.css,
        visible: rect.width > 0 && rect.height > 0,
        disabled: el.disabled === true,
        type: el.getAttribute("type"),
      });
    }
    return {
      url: location.href,
      title: document.title,
      // 화면 전체 텍스트는 절단해서 준다 — 길이 상한이 없으면 컨텍스트를 다 먹는다.
      text: (document.body ? document.body.innerText : "").slice(0, 4000),
      elements: out,
    };
  };

  /**
   * 조작의 **의미 단위**까지 올라간다.
   *
   * 이벤트의 `target` 은 사람이 실제로 누른 가장 깊은 노드다 — `div > div > button > span`
   * 이면 `span`, 아이콘 버튼이면 `svg` 나 `path`, 링크면 `a` 안의 `span` 이다. 그 노드를
   * 그대로 기록하면 두 가지를 동시에 잃는다.
   *
   * 1. **최우선 후보인 `role`+접근 이름이 사라진다** (FR-018). `span`·`path` 에는 암시적
   *    role 이 없다. 아이콘만 있는 버튼은 텍스트도 없으므로 남는 후보가 CSS 하나뿐이 된다.
   * 2. **그 CSS 가 가장 깨지기 쉬운 형태다.** 껍데기 `div` 를 몇 겹 지나온 위치 경로가
   *    되어, 같은 구조가 화면에 두 번 나오면 모호해지고 아예 버려진다.
   *
   * 둘이 겹치면 **확보 후보가 0개인 Step** 이 기록된다. 녹화 중에는 클릭이 정상으로
   * 보이므로 사용자는 재실행에서 "요소를 찾지 못했다" 를 볼 때까지 알 수 없다.
   *
   * 그래서 조작 대상을 실제 조작 주체까지 올린다. 부모 버튼을 클릭해도 같은 핸들러가
   * 돌므로 재실행 동작은 같다 — 사람이 누른 지점과 동작의 주체가 다를 뿐이다.
   *
   * **올라가는 거리를 제한한다.** 화면 전체를 `[tabindex]` 컨테이너로 감싼 앱에서 상한이
   * 없으면 컨테이너까지 올라가 엉뚱한 요소를 기록한다. `body`·`html` 에는 닿지 않는다.
   */
  const ACTIONABLE = [
    "button",
    "a[href]",
    "input",
    "select",
    "textarea",
    "summary",
    "label",
    '[role="button"]',
    '[role="link"]',
    '[role="menuitem"]',
    '[role="menuitemcheckbox"]',
    '[role="menuitemradio"]',
    '[role="tab"]',
    '[role="checkbox"]',
    '[role="radio"]',
    '[role="switch"]',
    '[role="option"]',
    '[role="treeitem"]',
    '[role="combobox"]',
    '[contenteditable="true"]',
  ].join(",");

  /** 의미가 없는 요소에 핸들러만 달아 버튼처럼 쓰는 구현을 위한 차선책. */
  const CLICKABLE = '[onclick],[tabindex]:not([tabindex="-1"])';
  const MAX_ASCEND = 8;

  const ascend = (el, selector) => {
    let node = el;
    for (let hops = 0; node && node.nodeType === 1 && hops <= MAX_ASCEND; hops += 1) {
      if (node === document.body || node === document.documentElement) return null;
      try {
        if (node.matches(selector)) return node;
      } catch {
        return null;
      }
      node = node.parentElement;
    }
    return null;
  };

  /**
   * 그 지점을 눌렀을 때 **이 요소가 실제로 받는가.** 다른 것이 덮고 있으면 아니다.
   *
   * Playwright 의 `click` 도 같은 판정을 하므로, 여기서 걸러 낸 요소는 재실행에서 반드시
   * 실패한다. 기록 시점에 미리 판정해 두면 그 실패를 만들지 않을 수 있다.
   */
  const isHittable = (el) => {
    try {
      const rect = el.getBoundingClientRect();
      if (rect.width <= 0 || rect.height <= 0) return false;
      const top = document.elementFromPoint(
        rect.left + rect.width / 2,
        rect.top + rect.height / 2,
      );
      return !!top && (top === el || el.contains(top));
    } catch {
      return false;
    }
  };

  /** 체크박스·라디오인가. 네모와 이름이 같은 조작을 뜻하는 종류다. */
  const isToggle = (el) => {
    if (!el || el.localName !== "input") return false;
    const type = (el.getAttribute("type") || "").toLowerCase();
    return type === "checkbox" || type === "radio";
  };

  /**
   * 체크박스·라디오는 **누른 지점이 아니라 조작 가능한 쪽**으로 통일한다.
   *
   * 사람은 네모를 누를 수도 있고 이름을 누를 수도 있는데, 둘은 같은 조작이다. 그런데 눌린
   * 요소를 그대로 기록하면 같은 체크박스가 누른 자리에 따라 다르게 기록된다 — 실측
   * (TC-013)에서 `즐겨찾기` 를 이름으로 누른 Step 12 는 `label` 로, 네모로 누른 Step 16 은
   * `input` 으로 기록됐고, **16 만 재실행에서 실패했다**(실제 `input` 이
   * `<button class="accordion-head">` 에 덮여 있었다).
   *
   * 그래서 짝(`label`·`input`) 중 **그 자리를 실제로 받을 수 있는 쪽**을 고르고, 둘 다
   * 가능하면 `label` 을 쓴다 — 이름을 들고 있어 정의가 읽히고, 사람이 보는 affordance 다.
   *
   * **체크박스·라디오에만 적용한다.** 텍스트 입력은 레이블을 눌러도 입력란이 포커스를 받는
   * 것뿐이고, 값을 넣는 Step 은 입력란을 가리켜야 한다. 그 종류까지 레이블로 바꾸면 정의가
   * 뜻하는 요소가 달라진다.
   */
  const preferredToggle = (el) => {
    const control = el.localName === "label" ? el.control : el;
    if (!isToggle(control)) return null;
    const labels = control.labels;
    const label = labels && labels.length > 0 ? labels[0] : null;
    if (label && isHittable(label)) return label;
    if (isHittable(control)) return control;
    return null; // 둘 다 받을 수 없다 — 눌린 것을 그대로 남기고 검증이 판정하게 둔다
  };

  const actionTarget = (el) => {
    if (!el) return null;
    const acted = ascend(el, ACTIONABLE) || ascend(el, CLICKABLE) || el;
    return preferredToggle(acted) || acted;
  };

  /** Shadow DOM 안의 요소도 잡는다 (T004 로 확인). */
  const targetOf = (event) => {
    const path = typeof event.composedPath === "function" ? event.composedPath() : null;
    const first = path && path.length > 0 ? path[0] : event.target;
    if (!first || first.nodeType !== 1) return null;
    return actionTarget(first);
  };

  /**
   * 마우스가 올라간 시점에 후보 수집을 미리 시작한다 (Step 은 만들지 않는다).
   *
   * 클릭 시점 수집은 화면 이동과 경쟁한다 — 앱의 클릭 핸들러가 `location.href` 를 먼저
   * 설정하면 문서가 교체되어 후보를 검증할 수 없다. 포인터가 요소에 올라간 시점은 그보다
   * 확실히 앞이므로(사람은 수백 ms, 자동 조작도 마우스 이동이 클릭보다 먼저 디스패치된다),
   * 여기서 검증을 끝내 두면 클릭이 늦어도 확보한 후보를 쓸 수 있다.
   */
  const INTERACTIVE = "button,a,input,select,textarea,label,[role],[tabindex],[onclick]";
  const HOVER_THROTTLE_MS = 400;
  const hovered = new WeakMap();

  document.addEventListener(
    "pointerover",
    (event) => {
      const el = targetOf(event);
      if (!el || !el.closest(INTERACTIVE)) return;
      const now = Date.now();
      const last = hovered.get(el);
      if (last !== undefined && now - last < HOVER_THROTTLE_MS) return;
      hovered.set(el, now);
      const described = describe(el);
      // 후보 사전 수집(경합 회피)과, 이 hover 가 화면을 바꿨는지 관측하는 두 목적이다.
      // 노드를 함께 든다 — 변화가 이 요소 주변에서 일어났는지 판정해야 한다.
      hoverCandidate = { node: el, element: described, mutated: false };
      setTimeout(settleHover, HOVER_EFFECT_WINDOW_MS);
      send({ kind: "hover", element: described });
    },
    true,
  );

  /**
   * hover 를 Step 으로 기록하는 기준 (FR-023c).
   *
   * **포인터가 지나간 모든 요소를 기록하지 않는다.** 화면을 훑는 동안 스친 요소가 모두
   * Step 이 되면 정의가 쓸모없이 길어지고, 어느 hover 가 의미 있었는지 사람이 다시
   * 판단해야 한다.
   *
   * 기준은 **그 hover 가 화면을 바꿨는가** 다. 두 신호를 함께 본다.
   *
   * 1. **렌더된 텍스트 길이가 "아무것도 올리지 않은 상태" 와 다른가.** `innerText` 는
   *    렌더되는 텍스트만 포함하므로 `display:none` 이던 메뉴가 열리면 늘어난다.
   *    **CSS `:hover` 로만 열리는 메뉴는 DOM 변화를 만들지 않기 때문에** 이 신호가
   *    필요하다 — MutationObserver 만으로는 잡지 못한다.
   * 2. **DOM 변화** (MutationObserver). JS 로 노드를 넣어 메뉴를 만드는 구현을 잡는다.
   *
   * **기준선을 hover 핸들러 안에서 재면 안 된다.** `:hover` 규칙은 포인터가 들어온
   * 시점에 이미 적용되므로, 핸들러가 도는 시점의 값은 "바뀐 뒤" 값이다. 그래서 기준선은
   * **포인터가 아무 요소에도 올라 있지 않을 때** 따로 갱신한다.
   *
   * **두 신호 모두 그대로 쓰면 속는다 (TC-012 실측).** 자동 감지된 hover 5개가 전부
   * 오탐이었고 하나는 재실행을 실패시켰다. 사람은 클릭하러 가는 길에 여러 요소를 스치는데,
   * 그때마다 다음 두 가지가 겹친다.
   *
   * 1. **DOM 변화가 문서 전체에서 관측됐다.** 앞선 클릭이 목록을 다시 그리는 중이면, 포인터
   *    밑에 있던 무관한 버튼의 hover 가 그 변화의 원인으로 기록된다.
   * 2. **기준선이 낡았다.** 기준선은 포인터가 아무 요소에도 올라 있지 않을 때만 갱신되는데,
   *    화면을 조작하는 동안 포인터는 늘 무언가 위에 있다. 그래서 기준선이 **클릭 이전
   *    화면**에 멈추고, 이후 모든 hover 가 "화면이 바뀌었다" 로 판정된다.
   *
   * 그래서 두 신호를 각각 조인다.
   *
   * - **DOM 변화는 국소적이어야 한다.** hover 의 효과는 그 요소 주변에 나타난다 — 메뉴는
   *   트리거의 형제나 자손이다. 문서 저편의 변화는 그 hover 가 만든 것이 아니다.
   * - **텍스트 신호는 기준선이 클릭보다 나중일 때만 쓴다.** 클릭 뒤에 잰 적이 없는
   *   기준선으로 비교하면 클릭이 만든 변화를 hover 의 것으로 읽는다.
   *
   * 한계 둘. **아이콘만 있는(텍스트 없는) hover 메뉴를 CSS 로만 여는 경우**는 여전히 두
   * 신호에 걸리지 않는다. 그리고 **메뉴를 `body` 끝에 따로 붙이는 구현**(포털)은 변화가
   * 국소적이지 않아 놓친다. 두 경우 모두 일시정지 중 직접 동작 추가(FR-036)로 넣는다 —
   * 놓치는 대가는 그 한 Step 을 손으로 넣는 것이고, 오탐의 대가는 **재실행이 실패하는
   * 정의**다. 실측에서 자동 감지가 필요했던 경우는 한 번도 없었다.
   */
  const HOVER_EFFECT_WINDOW_MS = 300;
  const BASELINE_SETTLE_MS = 60;
  let hoverCandidate = null;
  let baselineTextLength = 0;
  let baselineAt = 0;
  /** 기준선을 잰 시각. 클릭 시각과 비교해 낡은 기준선을 걸러 낸다. */
  let lastClickAt = 0;

  const renderedTextLength = () => {
    try {
      return document.body ? document.body.innerText.length : 0;
    } catch {
      return 0;
    }
  };

  /** 포인터가 아무 요소에도 올라 있지 않은가. `html`·`body` 만 남으면 그렇다. */
  const pointerIsIdle = () => {
    try {
      return document.querySelectorAll(":hover").length <= 2;
    } catch {
      return false;
    }
  };

  const refreshBaseline = () => {
    if (!pointerIsIdle()) return;
    baselineTextLength = renderedTextLength();
    baselineAt = Date.now();
  };

  document.addEventListener(
    "pointerout",
    () => setTimeout(refreshBaseline, BASELINE_SETTLE_MS),
    true,
  );

  const settleHover = () => {
    const candidate = hoverCandidate;
    hoverCandidate = null;
    if (candidate === null) return;
    // 기준선이 마지막 클릭보다 앞서 잰 것이면 텍스트 신호를 쓸 수 없다 — 그 차이가
    // 클릭이 만든 것인지 이 hover 가 만든 것인지 가릴 수 없다.
    const textUsable = baselineAt > lastClickAt;
    const textChanged = textUsable && renderedTextLength() !== baselineTextLength;
    if (candidate.mutated || textChanged) {
      send({ kind: "hover_action", element: candidate.element });
    }
  };

  /** 이 변화가 hover 한 요소 주변에서 일어났는가. hover 의 효과는 국소적이다. */
  const isNearHover = (node) => {
    const host = hoverCandidate && hoverCandidate.node;
    if (!host || !node) return false;
    const scope = host.parentElement || host;
    try {
      return scope.contains(node);
    } catch {
      return false;
    }
  };

  const mutationObserver = new MutationObserver((records) => {
    if (hoverCandidate === null) return;
    for (const record of records) {
      if (isNearHover(record.target)) {
        hoverCandidate.mutated = true;
        return;
      }
    }
  });

  const startObserving = () => {
    if (!document.body) return;
    mutationObserver.observe(document.body, {
      childList: true,
      subtree: true,
      attributes: true,
      attributeFilter: ["class", "style", "hidden", "aria-expanded", "aria-hidden"],
    });
  };
  const initHoverDetection = () => {
    startObserving();
    baselineTextLength = renderedTextLength();
    baselineAt = Date.now();
  };
  if (document.body) initHoverDetection();
  else document.addEventListener("DOMContentLoaded", initHoverDetection, { once: true });

  /** 끌어다 놓기 (FR-023c). 시작 요소와 놓은 요소를 함께 보낸다. */
  let dragSource = null;

  document.addEventListener(
    "dragstart",
    (event) => {
      const el = targetOf(event);
      dragSource = el ? describe(el) : null;
    },
    true,
  );

  document.addEventListener(
    "drop",
    (event) => {
      const el = targetOf(event);
      if (!el || dragSource === null) return;
      send({ kind: "drag", element: dragSource, dropElement: describe(el) });
      dragSource = null;
    },
    true,
  );

  document.addEventListener("dragend", () => { dragSource = null; }, true);

  // 키보드 조작 경로. Enter·Space 로 누르는 버튼은 포인터 이벤트를 내지 않으므로
  // 포커스가 들어온 시점에 같은 사전 수집을 한다.
  document.addEventListener(
    "focusin",
    (event) => {
      const el = targetOf(event);
      if (!el || !el.closest(INTERACTIVE)) return;
      send({ kind: "hover", element: describe(el) });
    },
    true,
  );

  // 클릭: pointerdown 이 먼저다. 화면 이동보다 앞서 후보 검증을 시작하기 위한 것이다.
  document.addEventListener(
    "pointerdown",
    (event) => {
      if (event.button !== undefined && event.button !== 0) return; // 좌클릭만
      const el = targetOf(event);
      if (!el) return;
      hoverCandidate = null; // 클릭이 끼었으면 이후 변화의 원인은 hover 가 아니다
      lastClickAt = Date.now();
      send({ kind: "click", phase: "down", element: describe(el) });
    },
    true,
  );

  // 키보드 활성화 등 포인터 이벤트가 없는 경로를 위한 보조 경로. 중복은 Python 이 접는다.
  document.addEventListener(
    "click",
    (event) => {
      const el = targetOf(event);
      if (!el) return;
      lastClickAt = Date.now();
      send({ kind: "click", phase: "click", element: describe(el) });
    },
    true,
  );

  /**
   * 입력 Step 을 만들 수 있는 태그. **`"value" in el` 로는 부족하다.**
   *
   * `HTMLButtonElement` 도 `value` 를 가지므로, 버튼에서 포커스가 떠날 때(`blur`)
   * 빈 값의 입력 Step 이 만들어진다. 그 Step 은 재실행에서 버튼에 `fill("")` 을 시도해
   * 반드시 실패한다 — US3 종단 테스트가 이것을 잡았다. `type` 속성으로 걸러 낼 수도
   * 없다: `<button>` 은 보통 `type` 을 쓰지 않아 빈 문자열로 읽힌다.
   */
  const FILLABLE_TAGS = ["input", "textarea"];

  const onSettled = (event) => {
    const el = targetOf(event);
    if (!el || !("value" in el)) return;
    const tag = el.tagName.toLowerCase();
    const type = (el.getAttribute("type") || "").toLowerCase();

    if (tag === "select") {
      send({ kind: "select", value: el.value, element: describe(el) });
      return;
    }
    if (!FILLABLE_TAGS.includes(tag)) return;
    if (["checkbox", "radio", "button", "submit", "reset", "file"].includes(type)) {
      // 체크박스·라디오는 click 으로 이미 잡힌다. 파일 입력은 별도 처리한다.
      if (type === "file") {
        send({ kind: "file_input", element: describe(el) });
      }
      return;
    }
    send({
      kind: "fill",
      value: el.value,
      // 비밀번호 유형은 시스템이 자동으로 민감 판정한다 (FR-082a).
      // 값은 Python 측에서 변수 참조로 치환된 뒤에야 이벤트로 나간다 (FR-083, T157).
      sensitive: type === "password",
      element: describe(el),
    });
  };

  document.addEventListener("change", onSettled, true);
  document.addEventListener("blur", onSettled, true);

  // 조합이 끝난 입력을 디바운스해서 미리 보낸다. 목적은 값이 아니라 **후보 검증 시점**을
  // 화면 이동보다 앞으로 당기는 것이다. IME 조합 중에는 보내지 않는다.
  const INPUT_DEBOUNCE_MS = 150;
  let composing = false;
  const pending = new WeakMap();

  /** 입력 하나에 대해 디바운스를 건다. `input` 과 `compositionend` 가 함께 쓴다. */
  const scheduleSettle = (event, el) => {
    const timer = pending.get(el);
    if (timer) clearTimeout(timer);
    pending.set(
      el,
      setTimeout(() => {
        pending.delete(el);
        if (composing) return;
        onSettled(event);
      }, INPUT_DEBOUNCE_MS),
    );
  };

  document.addEventListener("compositionstart", () => { composing = true; }, true);

  /*
    조합이 끝나면 **디바운스를 건다** (010 T048 · FR-328).

    이전에는 `composing` 을 내리기만 했다. 창에서 운영체제 IME 로 입력할 때는 그것으로
    충분하다 — 브라우저가 `compositionend` 뒤에 `input` 을 한 번 더 내보내고, 위의 `input`
    처리가 디바운스를 건다.

    **미러 경로는 그 `input` 이 오지 않는다.** 조합 확정은 CDP `Input.insertText` 로
    일어나고, 실측 결과 그 뒤에 `input` 이 발생하지 않았다 (010 T048 실측:
    compositionstart → compositionupdate → input(isComposing:true) ×3 → compositionend,
    끝). 조합 중의 `input` 은 전부 `composing` 때문에 건너뛰었으므로 걸린 디바운스도 없다.

    그 결과가 둘이었다.

    1. 입력만 하고 다른 곳을 누르지 않은 채 녹화를 멈추면 그 입력이 Step 으로 남지
       않는다 — FR-328 이 금지하는 상태다.
    2. 같은 입력이 창 경로와 미러 경로에서 다른 시점에 Step 이 된다 — 원칙 I 이
       요구하는 동등성(FR-324)이 시점에서 깨진다.

    여기서 디바운스를 거는 것으로 두 경로가 같아진다. 창 경로에서는 뒤따르는 `input` 이
    같은 타이머를 다시 걸 뿐이므로 동작이 바뀌지 않는다.
  */
  document.addEventListener(
    "compositionend",
    (event) => {
      composing = false;
      const el = targetOf(event);
      if (el) scheduleSettle(event, el);
    },
    true,
  );

  document.addEventListener(
    "input",
    (event) => {
      const el = targetOf(event);
      if (!el || composing) return;
      scheduleSettle(event, el);
    },
    true,
  );
})();
