/**
 * 주입 리코더. research R2 (T004 로 실측 확인).
 *
 * BrowserContext.add_init_script 로 주입되므로 모든 새 document·frame·탭에서 실행된다.
 * 그래서 멀티 탭(FR-030)이 별도 코드 없이 따라온다.
 *
 * **입력은 키 단위가 아니라 확정된 값을 잡는다.** `change`/`blur` 로 잡으면 한글 IME 조합
 * 중인 자모가 아니라 조합이 끝난 최종 값이 한 번에 온다. `keydown`/`input` 을 쓰면 조합
 * 완료 값을 재구성해야 한다.
 *
 * **실측 보강**: `change` 와 `blur` 가 둘 다 발생한다. 텍스트 입력 한 번이 이벤트 2건을
 * 만들므로 Python 측에서 같은 요소 기준 중복 제거가 필요하다 (FR-025).
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

  /**
   * CSS 경로. **최후 후보이며 항상 수집한다** — 다른 후보가 모두 없어도
   * TargetLocator 불변식(후보 최소 1개)을 만족시켜야 한다.
   */
  const cssPath = (el) => {
    const parts = [];
    let node = el;
    let depth = 0;
    while (node && node.nodeType === 1 && depth < 6) {
      let part = node.tagName.toLowerCase();
      const id = node.getAttribute("id");
      // 난수처럼 보이는 id 는 안정적이지 않으므로 쓰지 않는다.
      if (id && !/\d{4,}|[0-9a-f]{8,}/i.test(id)) {
        parts.unshift(`${part}#${CSS.escape(id)}`);
        break;
      }
      const parent = node.parentElement;
      if (parent) {
        const siblings = Array.from(parent.children).filter(
          (c) => c.tagName === node.tagName,
        );
        if (siblings.length > 1) {
          part += `:nth-of-type(${siblings.indexOf(node) + 1})`;
        }
      }
      parts.unshift(part);
      node = parent;
      depth += 1;
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

  const describe = (el) => {
    const attributes = {};
    for (const attr of COLLECTED_ATTRS) {
      const v = el.getAttribute(attr);
      if (v !== null) attributes[attr] = v;
    }
    return {
      tag: el.tagName.toLowerCase(),
      role: clean(el.getAttribute("role")) || implicitRole(el),
      accessibleName: accessibleName(el),
      label: associatedLabel(el),
      text: clean(el.textContent),
      css: cssPath(el),
      attributes,
    };
  };

  /** Shadow DOM 안의 요소도 잡는다 (T004 로 확인). */
  const targetOf = (event) => {
    const path = typeof event.composedPath === "function" ? event.composedPath() : null;
    const first = path && path.length > 0 ? path[0] : event.target;
    return first && first.nodeType === 1 ? first : null;
  };

  document.addEventListener(
    "click",
    (event) => {
      const el = targetOf(event);
      if (!el) return;
      send({ kind: "click", element: describe(el) });
    },
    true,
  );

  const onSettled = (event) => {
    const el = targetOf(event);
    if (!el || !("value" in el)) return;
    const tag = el.tagName.toLowerCase();
    const type = (el.getAttribute("type") || "").toLowerCase();

    if (tag === "select") {
      send({ kind: "select", value: el.value, element: describe(el) });
      return;
    }
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
})();
