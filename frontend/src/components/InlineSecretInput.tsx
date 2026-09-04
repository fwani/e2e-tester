/**
 * Step 편집 안에서 비밀 값을 넣는다. DR-023 ~ DR-027 · SC-106.
 *
 * 이전에는 비밀 값 입력이 별도 화면이었다. 로그인 Step 을 만들다 비밀번호가 필요해지면
 * 하던 작업을 두고 다른 화면으로 갔다가 돌아와야 했다 — 로그인은 가장 흔한 사전
 * Step 이라 그 끊김이 001 SC-005(테스트 생성 시간)에 그대로 얹힌다.
 *
 * **새 엔드포인트를 만들지 않는다.** `PUT /api/secrets/{name}` 이 **공개키만으로**
 * 동작하는 것이 인라인 입력을 가능하게 한다 — 비밀키는 실행 시에만 필요하다
 * (research R5). 그래서 Step 을 편집하는 시점에 필요한 것은 공개키뿐이다.
 *
 * 지키는 것:
 * - 값은 컴포넌트 상태에 남지 않는다. 전송 후 즉시 비운다
 * - Step 에는 `{{변수명}}` 참조만 남는다. 값은 테스트 정의에 들어가지 않는다 (FR-082·FR-084)
 * - 공개키가 없으면 **그 자리에서** 만들 수 있다 (DR-025). 그래서 DR-028 이 선행 조건이다
 */
import { useCallback, useEffect, useState } from "react";

import { ApiError, secrets, type SecretsResponse } from "../api/client";

/** 서버의 변수 이름 규칙과 같다 (`VARIABLE_NAME_PATTERN`). */
const NAME_RULE = /^[A-Z][A-Z0-9_]*$/;

export interface InlineSecretInputProps {
  /** 이미 연결된 변수 이름. `{{NAME}}` 에서 뽑아 넘긴다. */
  currentName?: string | null;
  /** 봉인에 성공하면 Step 에 넣을 참조를 돌려준다. */
  onLinked: (reference: string) => void;
  busy?: boolean;
}

export function InlineSecretInput({
  currentName = null,
  onLinked,
  busy = false,
}: InlineSecretInputProps) {
  const [known, setKnown] = useState<SecretsResponse | null>(null);
  const [hasKey, setHasKey] = useState<boolean | null>(null);
  const [name, setName] = useState(currentName ?? "");
  const [value, setValue] = useState("");
  const [working, setWorking] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

  const refresh = useCallback(() => {
    void secrets
      .list()
      .then(setKnown)
      .catch(() => setKnown(null));
    void secrets
      .keyStatus()
      .then((s) => setHasKey(s.public_key_present))
      .catch(() => setHasKey(false));
  }, []);

  useEffect(refresh, [refresh]);

  const nameOk = NAME_RULE.test(name);
  const ready = nameOk && value !== "" && hasKey === true;

  /** DR-025 — 공개키가 없으면 그 자리에서 만든다. 화면을 떠나지 않는다. */
  const makeKey = () => {
    setWorking(true);
    setError(null);
    void secrets
      .generateKey()
      .then((s) => {
        setHasKey(s.public_key_present);
        setNotice("키 쌍을 만들었습니다. 이어서 값을 넣으세요.");
      })
      .catch((exc: unknown) => setError(exc instanceof ApiError ? exc.message : String(exc)))
      .finally(() => setWorking(false));
  };

  const seal = () => {
    setWorking(true);
    setError(null);
    setNotice(null);
    void secrets
      .put(name, value)
      .then(() => {
        // **값을 상태에 남기지 않는다.** 화면·메모리 어디에도 평문을 두지 않는다.
        setValue("");
        setNotice(`${name} 을 봉인했습니다. Step 에는 참조만 남습니다.`);
        onLinked(`{{${name}}}`);
        refresh();
      })
      .catch((exc: unknown) => setError(exc instanceof ApiError ? exc.message : String(exc)))
      .finally(() => setWorking(false));
  };

  const disabled = busy || working;

  return (
    <div
      style={{
        border: "3px solid #14130F",
        background: "#FFFDF6",
        padding: 12,
        display: "flex",
        flexDirection: "column",
        gap: 8,
      }}
    >
      <div
        style={{
          font: "600 11px/1 'IBM Plex Mono', ui-monospace, monospace",
          letterSpacing: "0.12em",
          color: "#6B675C",
        }}
      >
        비밀 값
      </div>

      {hasKey === false && (
        <div
          role="status"
          style={{ border: "2px solid #14130F", background: "#FFF9D6", padding: "10px 12px" }}
        >
          <div style={{ fontSize: 13, marginBottom: 8 }}>
            공개키가 없어 값을 봉인할 수 없습니다. 여기서 바로 만들 수 있습니다.
          </div>
          <button disabled={disabled} onClick={makeKey}>
            키 쌍 만들기
          </button>
        </div>
      )}

      {/* DR-026 — 이미 등록된 변수 중에서 고를 수도 있다. */}
      {known !== null && known.names.length > 0 && (
        <div>
          <label htmlFor="inline-secret-existing">등록된 변수</label>
          <select
            id="inline-secret-existing"
            value={NAME_RULE.test(name) && known.names.some((n) => n.name === name) ? name : ""}
            onChange={(e) => {
              const picked = e.target.value;
              if (picked === "") return;
              setName(picked);
              onLinked(`{{${picked}}}`);
              setNotice(`${picked} 을 연결했습니다. 값은 이미 봉인돼 있습니다.`);
            }}
          >
            <option value="">직접 입력</option>
            {known.names.map((n) => (
              <option key={n.name} value={n.name}>
                {n.name}
                {n.present ? "" : " (값 없음)"}
              </option>
            ))}
          </select>
        </div>
      )}

      <div>
        <label htmlFor="inline-secret-name">변수 이름</label>
        <input
          id="inline-secret-name"
          value={name}
          onChange={(e) => setName(e.target.value.toUpperCase())}
          placeholder="LOGIN_PASSWORD"
        />
        {name !== "" && !nameOk && (
          <p style={{ color: "#A83A22", fontSize: 12, margin: "4px 0 0" }}>
            대문자로 시작하고 대문자·숫자·밑줄만 쓸 수 있습니다.
          </p>
        )}
      </div>

      <div>
        <label htmlFor="inline-secret-value">값</label>
        <input
          id="inline-secret-value"
          type="password"
          value={value}
          onChange={(e) => setValue(e.target.value)}
          autoComplete="off"
          placeholder="값은 저장 뒤 화면에 남지 않습니다"
        />
      </div>

      {error !== null && (
        <p role="alert" style={{ color: "#A83A22", fontSize: 13, margin: 0 }}>
          {error}
        </p>
      )}
      {notice !== null && (
        <p role="status" style={{ color: "#6B675C", fontSize: 13, margin: 0 }}>
          {notice}
        </p>
      )}

      <p style={{ color: "#9A968A", fontSize: 12, margin: 0 }}>
        값은 공개키로 암호화되어 테스트 정의와 분리된 비밀 파일에 저장됩니다. Step 에는{" "}
        <code>{"{{변수명}}"}</code> 참조만 남습니다.
      </p>

      <button disabled={disabled || !ready} onClick={seal}>
        봉인하고 연결
      </button>
    </div>
  );
}

/** `{{NAME}}` 참조에서 변수 이름을 뽑는다. 참조가 아니면 `null`. */
export function referenceName(value: string): string | null {
  const match = /^\{\{([A-Z][A-Z0-9_]*)\}\}$/.exec(value);
  return match?.[1] ?? null;
}
