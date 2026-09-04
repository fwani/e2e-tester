/**
 * 키 관리 (T145). FR-089a·FR-089e-1·DR-031. **확정 디자인에 없는 화면**이므로 8화면의
 * 시각 언어를 따른다 (spec 디자인 차이 3).
 *
 * 이 화면이 다루는 것은 **키의 존재와 상태**뿐이다. 키 자체도, 민감 값도 표시하지 않는다.
 *
 * 세 가지를 명확히 알린다.
 *
 * 1. **생성은 덮어쓰지 않는다.** 이미 있는 키를 덮어쓰면 기존 암호문을 전부 읽을 수 없다 —
 *    그래서 교체는 별도의 위험 구역에서 확인 문구를 받고 진행한다.
 * 2. **권한이 과도하게 열려 있으면 경고한다** (FR-089e-1). 권한을 임의로 바꾸지는 않는다 —
 *    사용자의 파일 시스템을 제품이 조용히 고치지 않는다.
 * 3. **암호구로 잠긴 키는 실행 시 열 방법이 필요하다.** 봉인은 공개키만으로 되지만 재실행은
 *    비밀키를 연다. 잠긴 상태를 그냥 두면 "복호화할 수 없다" 로만 끝나므로, 여기서 미리
 *    환경 변수 공급 방법을 알린다.
 */
import { useCallback, useEffect, useState } from "react";
import { ErrorNotice, describeError } from "../components/ErrorNotice";
import type { ErrorInfo } from "../components/ErrorNotice";

import { DESTROY_CONFIRM, secrets, type KeyStatus } from "../api/client";

const PASSPHRASE_ENV = "ITB_KEY_PASSPHRASE";

export interface KeyManagementProps {
  onClose?: () => void;
}

export function KeyManagement({ onClose }: KeyManagementProps) {
  const [status, setStatus] = useState<KeyStatus | null>(null);
  const [passphrase, setPassphrase] = useState("");
  const [newPassphrase, setNewPassphrase] = useState("");
  const [confirm, setConfirm] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<ErrorInfo | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

  const load = useCallback(() => {
    void secrets
      .keyStatus()
      .then(setStatus)
      .catch((exc: unknown) =>
        setError(describeError(exc)),
      );
  }, []);

  useEffect(load, [load]);

  /** 조작 하나를 감싼다 — 성공/실패 표시와 busy 처리가 세 버튼에서 같다. */
  const run = <T,>(action: () => Promise<T>, onDone: (result: T) => void) => {
    setBusy(true);
    setError(null);
    setNotice(null);
    void action()
      .then((result) => {
        setConfirm("");
        onDone(result);
      })
      .catch((exc: unknown) =>
        setError(describeError(exc)),
      )
      .finally(() => setBusy(false));
  };

  const generate = () =>
    run(
      () => secrets.generateKey(passphrase.trim() === "" ? undefined : passphrase),
      (next) => {
        setStatus(next);
        setPassphrase("");
        setNotice(
          "키 쌍을 만들었습니다. 비밀키는 이 장비에만 있으며, 잃어버리면 보관된 민감 " +
            "값을 다시 읽을 수 없습니다.",
        );
      },
    );

  const regenerate = () =>
    run(
      () => secrets.regenerateKey(newPassphrase.trim() === "" ? undefined : newPassphrase),
      (result) => {
        setStatus(result.status);
        setNewPassphrase("");
        setNotice(
          `키를 교체했습니다. 이전 키로 봉인된 값 ${result.purged_secret_count}개를 함께 ` +
            "비웠습니다 — 새 키로는 읽을 수 없기 때문입니다. 민감 값을 다시 입력하세요." +
            (result.project_open
              ? ""
              : " 열린 프로젝트가 없어 다른 프로젝트의 암호문은 비우지 못했습니다."),
        );
      },
    );

  const destroy = () =>
    run(secrets.destroyKey, (result) => {
      setStatus(result.status);
      setNotice(
        `키를 지웠습니다. 봉인된 값 ${result.purged_secret_count}개도 함께 비웠습니다. ` +
          "민감 변수를 쓰는 테스트는 키를 다시 만들고 값을 입력할 때까지 실행할 수 없습니다.",
      );
    });

  const hasKeys = status?.private_key_present === true;
  const locked = status?.passphrase_protected === true;
  /** 서버의 제약과 같은 값이다 (`GenerateKeyRequest.passphrase`, min_length=8). */
  const tooShort = passphrase !== "" && passphrase.length < 8;
  const newTooShort = newPassphrase !== "" && newPassphrase.length < 8;
  const confirmed = confirm === DESTROY_CONFIRM;

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
        <ErrorNotice error={error} />
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
          {locked && <span className="badge">암호구 보호</span>}
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

      {/*
        잠긴 키는 봉인에는 지장이 없고 실행에서만 막힌다. 그 시점에 처음 알면 사용자는
        재실행이 왜 실패했는지 모른다 — 여기서 미리 말한다.
      */}
      {locked && (
        <section
          role="note"
          style={{
            border: "3px solid var(--warn)",
            background: "var(--warn-tint)",
            padding: 14,
            marginTop: 16,
          }}
        >
          <strong>암호구로 잠긴 키입니다</strong>
          <p style={{ margin: "8px 0 0", fontSize: 12.5 }}>
            비밀 값을 저장하는 데에는 문제가 없지만, <b>재실행과 AI 작성은 비밀키를 열어야
            합니다.</b> 백엔드 프로세스에 환경 변수{" "}
            <span className="mono">{PASSPHRASE_ENV}</span> 로 암호구를 공급하세요. 공급하지
            않으면 민감 변수를 쓰는 Step 이 사유와 함께 실패합니다.
          </p>
          <pre
            className="mono"
            style={{ margin: "8px 0 0", fontSize: 11.5, overflowX: "auto" }}
          >
            {PASSPHRASE_ENV}='…' uv run itb
          </pre>
          <p className="dim" style={{ margin: "8px 0 0", fontSize: 11.5 }}>
            암호구를 없애려면 아래에서 키를 교체하세요. 교체하면 보관된 민감 값은 다시
            입력해야 합니다.
          </p>
        </section>
      )}

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
            복구해 줄 방법은 없습니다. 실행할 때는 환경 변수{" "}
            <span className="mono">{PASSPHRASE_ENV}</span> 로 공급해야 합니다.
          </p>
          <div>
            {/* 제약에 맞지 않으면 제출 자체를 막는다 — 실패를 겪게 할 이유가 없다. */}
            <button disabled={busy || tooShort} onClick={generate}>
              키 쌍 만들기
            </button>
          </div>
        </section>
      )}

      {/*
        DR-031 — 교체·삭제는 되돌릴 수 없다. 확인 문구를 정확히 입력해야 두 버튼이 열린다.
        이 조작이 없으면 사용자는 키 파일을 직접 찾아 지우는 수밖에 없고, 그때 비밀 파일의
        지문은 남아 새 값 저장까지 막히는 상태가 된다 — 그 편이 더 위험하다.
      */}
      {hasKeys && (
        <section
          style={{
            border: "3px solid var(--fail)",
            background: "var(--paper)",
            padding: 14,
            marginTop: 16,
            display: "flex",
            flexDirection: "column",
            gap: 10,
          }}
        >
          <strong style={{ color: "var(--fail-dark)" }}>키 교체·삭제</strong>
          <p style={{ margin: 0, fontSize: 12.5 }}>
            <b>되돌릴 수 없습니다.</b> 지금 키로 봉인된 민감 값은 이후 어떤 방법으로도 읽을
            수 없으므로, 이 프로젝트의 암호문도 함께 비웁니다. 교체 뒤에는 모든 민감 값을
            다시 입력해야 합니다.
          </p>

          <label htmlFor="regen-passphrase">새 암호구 (선택, 교체할 때만 적용)</label>
          <input
            id="regen-passphrase"
            type="password"
            value={newPassphrase}
            onChange={(e) => setNewPassphrase(e.target.value)}
            placeholder="비워 두면 암호구 없는 키로 교체합니다"
            aria-describedby="regen-passphrase-rule"
          />
          <p
            id="regen-passphrase-rule"
            style={{ margin: 0, fontSize: 12, color: newTooShort ? "#A83A22" : "#6B675C" }}
          >
            {newTooShort
              ? `암호구는 8자 이상이어야 합니다. 지금 ${newPassphrase.length}자입니다.`
              : "암호구를 걸려면 8자 이상 200자 이하로 적으세요."}
          </p>

          <label htmlFor="destroy-confirm">
            확인 문구 — <span className="mono">{DESTROY_CONFIRM}</span> 를 그대로 입력하세요
          </label>
          <input
            id="destroy-confirm"
            className="mono"
            value={confirm}
            onChange={(e) => setConfirm(e.target.value)}
            placeholder={DESTROY_CONFIRM}
            autoComplete="off"
          />

          <div className="row" style={{ gap: 8 }}>
            <button disabled={busy || !confirmed || newTooShort} onClick={regenerate}>
              키 교체
            </button>
            <button className="secondary" disabled={busy || !confirmed} onClick={destroy}>
              키 삭제
            </button>
          </div>
          <p className="dim" style={{ margin: 0, fontSize: 11.5 }}>
            <b>교체</b>는 지우고 새 키를 바로 만듭니다. <b>삭제</b>는 지우기만 합니다 — 키가
            없으면 민감 값을 새로 저장할 수도, 기존 값을 읽을 수도 없습니다.
          </p>
        </section>
      )}
    </main>
  );
}
