/**
 * 키 관리 (T145). FR-089a·FR-089e-1. **확정 디자인에 없는 화면**이므로 8화면의 시각
 * 언어를 따른다 (spec 디자인 차이 3).
 *
 * 이 화면이 다루는 것은 **키의 존재와 상태**뿐이다. 키 자체도, 민감 값도 표시하지 않는다.
 *
 * 두 가지를 명확히 알린다.
 *
 * 1. **키 생성은 한 번뿐이다.** 이미 있는 키를 덮어쓰면 기존 암호문을 전부 읽을 수 없다 —
 *    되돌릴 수 없는 손실이므로 서버가 거절하고, 화면도 그 사실을 미리 말한다.
 * 2. **권한이 과도하게 열려 있으면 경고한다** (FR-089e-1). 권한을 임의로 바꾸지는 않는다 —
 *    사용자의 파일 시스템을 제품이 조용히 고치지 않는다.
 */
import { useCallback, useEffect, useState } from "react";

import { ApiError, secrets, type KeyStatus } from "../api/client";

export interface KeyManagementProps {
  onClose?: () => void;
}

export function KeyManagement({ onClose }: KeyManagementProps) {
  const [status, setStatus] = useState<KeyStatus | null>(null);
  const [passphrase, setPassphrase] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

  const load = useCallback(() => {
    void secrets
      .keyStatus()
      .then(setStatus)
      .catch((exc: unknown) =>
        setError(exc instanceof ApiError ? exc.message : String(exc)),
      );
  }, []);

  useEffect(load, [load]);

  const generate = () => {
    setBusy(true);
    setError(null);
    setNotice(null);
    void secrets
      .generateKey(passphrase.trim() === "" ? undefined : passphrase)
      .then((next) => {
        setStatus(next);
        setPassphrase("");
        setNotice(
          "키 쌍을 만들었습니다. 비밀키는 이 장비에만 있으며, 잃어버리면 보관된 민감 " +
            "값을 다시 읽을 수 없습니다.",
        );
      })
      .catch((exc: unknown) =>
        setError(exc instanceof ApiError ? exc.message : String(exc)),
      )
      .finally(() => setBusy(false));
  };

  const hasKeys = status?.private_key_present === true;
  /** 서버의 제약과 같은 값이다 (`GenerateKeyRequest.passphrase`, min_length=8). */
  const tooShort = passphrase !== "" && passphrase.length < 8;

  return (
    <main style={{ maxWidth: 720, margin: "32px auto", padding: "0 16px" }}>
      <div className="row" style={{ gap: 8, marginBottom: 16 }}>
        <h1 style={{ margin: 0, fontFamily: "var(--font-display)" }}>키 관리</h1>
        <span className="spacer" />
        {onClose && (
          <button className="secondary" onClick={onClose}>
            닫기
          </button>
        )}
      </div>

      {error !== null && (
        <p
          role="alert"
          style={{
            padding: "8px 10px",
            background: "var(--fail-tint)",
            color: "var(--fail-dark)",
            border: "2px solid var(--fail)",
          }}
        >
          {error}
        </p>
      )}

      {notice !== null && (
        <p
          role="status"
          style={{
            padding: "8px 10px",
            background: "var(--warn-tint)",
            border: "2px solid var(--warn)",
          }}
        >
          {notice}
        </p>
      )}

      {status !== null && status.permission_warning !== null && (
        <p
          role="alert"
          style={{
            padding: "8px 10px",
            background: "var(--warn-tint)",
            border: "2px solid var(--warn)",
          }}
        >
          ⚠ {status.permission_warning}
        </p>
      )}

      <section
        style={{
          border: "3px solid var(--ink)",
          background: "var(--paper)",
          padding: 14,
          display: "flex",
          flexDirection: "column",
          gap: 10,
        }}
      >
        <div className="row" style={{ gap: 8 }}>
          <strong>키 상태</strong>
          <span className={`badge ${hasKeys ? "pass" : "warn"}`}>
            {hasKeys ? "준비됨" : "없음"}
          </span>
          {status?.passphrase_protected && <span className="badge">암호구 보호</span>}
        </div>

        <dl style={{ margin: 0, display: "grid", gridTemplateColumns: "auto 1fr", gap: 6 }}>
          <dt className="muted">비밀키</dt>
          <dd style={{ margin: 0 }}>{status?.private_key_present ? "있음" : "없음"}</dd>
          <dt className="muted">공개키</dt>
          <dd style={{ margin: 0 }}>{status?.public_key_present ? "있음" : "없음"}</dd>
          <dt className="muted">공개키 지문</dt>
          <dd className="mono" style={{ margin: 0, wordBreak: "break-all" }}>
            {status?.public_key_fingerprint ?? "—"}
          </dd>
        </dl>

        <p className="dim" style={{ margin: 0, fontSize: 11.5 }}>
          키는 프로젝트 밖(<span className="mono">~/.config/itb/keys</span>)에 있습니다.
          테스트 정의에는 민감 값이 들어가지 않으며, 암호문은 프로젝트의 비밀 파일에만
          있습니다.
        </p>
      </section>

      {!hasKeys && (
        <section
          style={{
            border: "3px solid var(--ink)",
            background: "var(--surface-soft)",
            padding: 14,
            marginTop: 16,
            display: "flex",
            flexDirection: "column",
            gap: 10,
          }}
        >
          <strong>키 쌍 만들기</strong>
          <label htmlFor="passphrase">암호구 (선택)</label>
          <input
            id="passphrase"
            type="password"
            value={passphrase}
            onChange={(e) => setPassphrase(e.target.value)}
            placeholder="비워 두면 암호구 없이 저장합니다"
            aria-describedby="passphrase-rule"
          />
          {/*
            DR-029 — 제약을 **제출 전에** 알린다. 이 안내가 없어서 사용자가 짧은
            암호구를 넣고 원인을 알 수 없는 422 를 받았다 (research R3).
          */}
          <p
            id="passphrase-rule"
            style={{ margin: 0, fontSize: 12, color: tooShort ? "#A83A22" : "#6B675C" }}
          >
            {tooShort
              ? `암호구는 8자 이상이어야 합니다. 지금 ${passphrase.length}자입니다.`
              : "암호구를 걸려면 8자 이상 200자 이하로 적으세요."}
          </p>
          <p className="dim" style={{ margin: 0, fontSize: 11.5 }}>
            암호구를 걸면 비밀키 파일이 잠깁니다. 잊으면 보관된 값을 읽을 수 없고, 제품이
            복구해 줄 방법은 없습니다.
          </p>
          <div>
            {/* 제약에 맞지 않으면 제출 자체를 막는다 — 실패를 겪게 할 이유가 없다. */}
            <button disabled={busy || tooShort} onClick={generate}>
              키 쌍 만들기
            </button>
          </div>
        </section>
      )}

      {hasKeys && (
        <p className="muted" style={{ fontSize: 12, marginTop: 16 }}>
          키가 이미 있습니다. 새로 만들면 기존 암호문을 읽을 수 없게 되므로 제품이 덮어쓰지
          않습니다. 정말 교체하려면 키 파일을 직접 지운 뒤 다시 만들고, 모든 민감 값을 다시
          입력해야 합니다.
        </p>
      )}
    </main>
  );
}
