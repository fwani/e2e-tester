/**
 * 비밀 값 관리 (T146). FR-082b·FR-089b·FR-089c. **확정 디자인에 없는 화면**이므로
 * 8화면의 시각 언어를 따른다 (spec 디자인 차이 3).
 *
 * **값을 표시하지 않는다.** 서버에 값을 돌려주는 엔드포인트가 아예 없으므로 표시할 방법도
 * 없다 — 화면의 제약이 아니라 계약의 제약이다 (contracts/rest-api §비밀 값과 키).
 *
 * 입력은 **비밀키를 요구하지 않는다** (FR-089b). 공개키만으로 봉인되므로, 값을 넣는
 * 사람이 복호화 권한을 가질 필요가 없다.
 *
 * 지문이 어긋나면(키 교체) 기존 암호문을 읽을 수 없다. 그 사실을 **먼저** 알린다 —
 * 모르고 실행하면 "값이 없다" 는 실패만 보게 된다 (spec 엣지 케이스).
 */
import { useCallback, useEffect, useState } from "react";
import { ErrorNotice, describeError } from "../components/ErrorNotice";
import { Toast } from "../components/Toast";
import type { ErrorInfo } from "../components/ErrorNotice";

import { secrets, type SecretsResponse } from "../api/client";

import { Button, navLinkClasses } from "../ui/Button";

import { Chip } from "../ui/Chip";
export interface SecretValuesProps {
  /** 테스트 정의가 참조하는 민감 변수 이름들. 아직 값이 없는 것을 보여 주기 위한 것이다. */
  requiredNames?: string[];
  onClose?: () => void;
  onManageKeys?: () => void;
}

export function SecretValues({
  requiredNames = [],
  onClose,
  onManageKeys,
}: SecretValuesProps) {
  const [data, setData] = useState<SecretsResponse | null>(null);
  const [name, setName] = useState("");
  const [value, setValue] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<ErrorInfo | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

  const load = useCallback(() => {
    void secrets
      .list()
      .then(setData)
      .catch((exc: unknown) =>
        setError(describeError(exc)),
      );
  }, []);

  useEffect(load, [load]);

  const submit = () => {
    setBusy(true);
    setError(null);
    setNotice(null);
    void secrets
      .put(name.trim(), value)
      .then(() => {
        // ★ 입력값을 즉시 지운다. 화면에 남겨 둘 이유가 없다.
        setValue("");
        setNotice(`${name.trim()} 을 봉인해 저장했습니다. 값은 표시되지 않습니다.`);
        setName("");
        load();
      })
      .catch((exc: unknown) =>
        setError(describeError(exc)),
      )
      .finally(() => setBusy(false));
  };

  const stored = new Set((data?.names ?? []).map((n) => n.name));
  const missing = requiredNames.filter((n) => !stored.has(n));
  const mismatched = data !== null && !data.fingerprint_matches_key;
  const ready = name.trim() !== "" && value !== "";

  return (
    <main className="max-w-[720px] my-s6 mx-auto py-0 px-s4">
      <div className="flex items-center gap-s2 mb-s4">
        <h1 className="font-sans text-[20px] font-bold leading-[1.3] m-0">비밀 값</h1>
        <span className="flex-1" />
        {onManageKeys && (
          <Button onClick={onManageKeys}>
            키 관리
          </Button>
        )}
        {onClose && (
          <Button onClick={onClose}>
            닫기
          </Button>
        )}
      </div>

      {mismatched && (
        <p
          role="alert"
          className="bg-fail-t border border-fail-line rounded-base text-fail py-s2 px-[10px]"
        >
          공개키가 교체되었습니다. 기존 암호문은 새 키로 읽을 수 없으므로 **모든 값을 다시
          입력**해야 합니다.
        </p>
      )}

      {error !== null && (
        <Toast tone="error" onDismiss={() => setError(null)}>
          <ErrorNotice error={error} />
        </Toast>
      )}

      {notice !== null && (
        <p
          role="status"
          className="bg-warn-t border border-warn-line rounded-base py-s2 px-[10px]"
        >
          {notice}
        </p>
      )}

      {missing.length > 0 && (
        <p className="font-sans text-[13px] leading-[1.4] font-normal text-ink-2">
          아직 값이 없는 변수: <span className="font-mono">{missing.join(", ")}</span>. 값이
          없으면 해당 Step 이 사유와 함께 실패합니다.
        </p>
      )}

      <section
        className="bg-panel border border-hair rounded-base p-[14px] flex flex-col gap-s2"
      >
        <div className="flex items-center gap-s2">
          <strong>보관된 변수</strong>
          <Chip>{data?.names.length ?? 0}</Chip>
        </div>

        {(data?.names.length ?? 0) === 0 ? (
          <p className="font-sans text-[11px] leading-[1.4] font-normal text-ink-3 m-0">
            보관된 값이 없습니다.
          </p>
        ) : (
          <ul className="font-sans text-[13px] leading-[1.4] font-normal m-0 pl-[18px]">
            {data?.names.map((entry) => (
              <li key={entry.name} className="flex items-center gap-s2">
                <span className="font-mono">{entry.name}</span>
                <Chip tone="pass">보관됨</Chip>
                <span className="flex-1" />
                <button
                  className={navLinkClasses()}
                  disabled={busy}
                  onClick={() => {
                    setBusy(true);
                    void secrets
                      .remove(entry.name)
                      .then(load)
                      .catch((exc: unknown) =>
                        setError(describeError(exc)),
                      )
                      .finally(() => setBusy(false));
                  }}
                >
                  삭제
                </button>
              </li>
            ))}
          </ul>
        )}

        <p className="font-sans text-[11px] leading-[1.4] font-normal text-ink-3 m-0">
          값은 어떤 화면에도 표시되지 않습니다. 서버에 값을 돌려주는 경로가 없습니다.
        </p>
      </section>

      <section
        className="bg-panel border border-hair rounded-base bg-sunken-2 p-[14px] mt-s4 flex flex-col gap-s2"
      >
        <strong>값 입력·재입력</strong>
        <label htmlFor="secret-name">변수 이름</label>
        <input
          id="secret-name"
          value={name}
          onChange={(e) => setName(e.target.value.toUpperCase())}
          placeholder="LOGIN_PASSWORD"
          className="font-mono"
        />
        <label htmlFor="secret-value">값</label>
        <input
          id="secret-value"
          type="password"
          value={value}
          onChange={(e) => setValue(e.target.value)}
          autoComplete="off"
        />
        <p className="font-sans text-[11px] leading-[1.4] font-normal text-ink-3 m-0">
          입력한 값은 공개키로 즉시 봉인되어 저장됩니다. 비밀키는 필요하지 않습니다.
          같은 이름으로 다시 넣으면 이전 값을 대체합니다.
        </p>
        <div>
          <button disabled={busy || !ready} onClick={submit}>
            봉인해 저장
          </button>
        </div>
      </section>
    </main>
  );
}
