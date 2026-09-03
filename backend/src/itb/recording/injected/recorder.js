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
      send({ kind: "hover", element: describe(el) });
    },
    true,
  );

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
      send({ kind: "click", phase: "click", element: describe(el) });
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

  // 조합이 끝난 입력을 디바운스해서 미리 보낸다. 목적은 값이 아니라 **후보 검증 시점**을
  // 화면 이동보다 앞으로 당기는 것이다. IME 조합 중에는 보내지 않는다.
  const INPUT_DEBOUNCE_MS = 150;
  let composing = false;
  const pending = new WeakMap();

  document.addEventListener("compositionstart", () => { composing = true; }, true);
  document.addEventListener("compositionend", () => { composing = false; }, true);

  document.addEventListener(
    "input",
    (event) => {
      const el = targetOf(event);
      if (!el || composing) return;
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
    },
    true,
  );
})();
