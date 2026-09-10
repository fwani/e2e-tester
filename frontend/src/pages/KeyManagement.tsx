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
import { Toast } from "../components/Toast";
import type { ErrorInfo } from "../components/ErrorNotice";

import { DESTROY_CONFIRM, secrets, type KeyStatus } from "../api/client";

import { Button } from "../ui/Button";

import { Chip } from "../ui/Chip";
const PASSPHRASE_ENV = "ITB_KEY_PASSPHRASE";

export interface KeyManagementProps {
  onClose?: () => void;
}

export function KeyManagement({ onClose }: KeyManagementProps) {
  const [status, setStatus] = useState<KeyStatus | null>(null);
  const [passphrase, setPassphrase] = useState("");
  const [unlockPassphrase, setUnlockPassphrase] = useState("");
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
  /**
   * 잠금 해제. **여기가 이 화면의 핵심 조작이다** (FR-089e-3).
   *
   * 예전에는 암호구를 걸어 키를 만든 사용자가 같은 암호구를 셸 환경 변수로 다시 넣고
   * 백엔드를 재기동해야 민감 변수를 쓸 수 있었다 — 화면이 이미 받은 것을 화면이 쓰지
   * 못했다 (UX U-26).
   */
  const unlock = () =>
    run(
      () => secrets.unlockKey(unlockPassphrase),
      (next) => {
        setStatus(next);
        setUnlockPassphrase("");
        setNotice(
          "잠금을 해제했습니다. 민감 변수를 쓰는 재실행과 AI 작성이 가능합니다. " +
            "백엔드를 다시 띄우면 다시 잠깁니다.",
        );
      },
    );

  const lock = () =>
    run(secrets.lockKey, (next) => {
      setStatus(next);
      setNotice(
        "다시 잠갔습니다. 민감 변수를 쓰는 실행은 잠금을 해제할 때까지 사유와 함께 " +
          "실패합니다. 비밀 값 저장은 그대로 됩니다 — 봉인은 공개키만으로 하기 때문입니다.",
      );
    });

  const destroy = () =>
    run(secrets.destroyKey, (result) => {
      setStatus(result.status);
      setNotice(
        `키를 지웠습니다. 봉인된 값 ${result.purged_secret_count}개도 함께 비웠습니다. ` +
          "민감 변수를 쓰는 테스트는 키를 다시 만들고 값을 입력할 때까지 실행할 수 없습니다.",
      );
    });

  const hasKeys = status?.private_key_present === true;
  /** 키 파일에 암호구가 걸려 있는가 — **지금 열려 있는지와는 다른 질문이다.** */
  const protectedKey = status?.passphrase_protected === true;
  /** 지금 이 백엔드가 비밀키를 열 수 있는가. */
  const unlocked = status?.unlocked === true;
  const needsUnlock = protectedKey && !unlocked;
  const unlockTooShort = unlockPassphrase !== "" && unlockPassphrase.length < 8;
  /** 서버의 제약과 같은 값이다 (`GenerateKeyRequest.passphrase`, min_length=8). */
  const tooShort = passphrase !== "" && passphrase.length < 8;
  const newTooShort = newPassphrase !== "" && newPassphrase.length < 8;
  const confirmed = confirm === DESTROY_CONFIRM;

  return (
    <main className="max-w-[720px] my-s6 mx-auto py-0 px-s4">
      <div className="flex items-center gap-s2 mb-s4">
        <h1 className="font-sans text-[20px] font-bold leading-[1.3] m-0">키 관리</h1>
        <span className="flex-1" />
        {onClose && (
          <Button onClick={onClose}>
            닫기
          </Button>
        )}
      </div>

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

      {status !== null && status.permission_warning !== null && (
        <p
          role="alert"
          className="bg-warn-t border border-warn-line rounded-base py-s2 px-[10px]"
        >
          ⚠ {status.permission_warning}
        </p>
      )}

      <section
        className="bg-panel border border-hair rounded-base p-[14px] flex flex-col gap-[10px]"
      >
        <div className="flex items-center gap-s2">
          <strong>키 상태</strong>
          <span className={`${`chip ${hasKeys ? "pass" : "warn"}`} m-0`}>
            {hasKeys ? "준비됨" : "없음"}
          </span>
          {protectedKey && <Chip>암호구 보호</Chip>}
          {/* 보호 여부와 **지금 열려 있는지**는 다른 정보다. 둘 다 보여야 한다. */}
          {protectedKey && (
            <span className={`${`chip ${unlocked ? "pass" : "warn"}`} m-0`}>
              {unlocked ? "열림" : "잠김"}
            </span>
          )}
        </div>

        <dl className="m-0 grid grid-cols-[auto_1fr] gap-[6px]">
          <dt className="text-ink-2">비밀키</dt>
          <dd className="m-0">{status?.private_key_present ? "있음" : "없음"}</dd>
          <dt className="text-ink-2">공개키</dt>
          <dd className="m-0">{status?.public_key_present ? "있음" : "없음"}</dd>
          <dt className="text-ink-2">공개키 지문</dt>
          <dd className="font-mono m-0 break-all">
            {status?.public_key_fingerprint ?? "—"}
          </dd>
        </dl>

        <p className="font-sans text-[11px] leading-[1.4] text-ink-3 m-0">
          키는 프로젝트 밖(
          <span className="font-mono">{status?.key_dir ?? "…"}</span>
          )에 있습니다. 이 장비의 모든 ITB 프로젝트가 이 키 하나를 씁니다. 테스트 정의에는
          민감 값이 들어가지 않으며, 암호문은 각 프로젝트의 비밀 파일에만 있습니다.
        </p>
      </section>

      {/*
        잠긴 키는 봉인에는 지장이 없고 실행에서만 막힌다. 그 시점에 처음 알면 사용자는
        재실행이 왜 실패했는지 모른다 — 여기서 미리 말하고, **여기서 풀 수 있게 한다.**

        예전에는 이 자리가 환경 변수 사용법만 알려 주는 안내였다. 화면에서 암호구를 받아
        키를 만들었는데 같은 값을 셸에 다시 넣고 재기동하라고 요구한 셈이다 (UX U-26).
      */}
      {needsUnlock && (
        <section
          role="note"
          className="bg-warn-t border border-warn-line rounded-base p-[14px] mt-s4 flex flex-col gap-[10px]"
        >
          <strong>비밀키가 잠겨 있습니다</strong>
          <p className="font-sans text-[13px] leading-[1.4] m-0">
            비밀 값을 저장하는 데에는 문제가 없지만, <b>재실행과 AI 작성은 비밀키를 열어야
            합니다.</b> 암호구를 입력해 잠금을 해제하세요. 해제하지 않으면 민감 변수를 쓰는
            Step 이 사유와 함께 실패합니다.
          </p>
          <label htmlFor="unlock-passphrase">암호구</label>
          <input
            id="unlock-passphrase"
            type="password"
            value={unlockPassphrase}
            onChange={(e) => setUnlockPassphrase(e.target.value)}
            placeholder="키를 만들 때 입력한 암호구"
            aria-describedby="unlock-rule"
            onKeyDown={(e) => {
              // 암호구 입력란 하나뿐인 양식이다. Enter 로 끝나야 한다.
              if (e.key === "Enter" && !busy && !unlockTooShort && unlockPassphrase !== "") {
                unlock();
              }
            }}
          />
          <p
            id="unlock-rule"
            className="font-sans text-[11px] leading-[1.4] text-ink-3 m-0"
          >
            {unlockTooShort
              ? `암호구는 8자 이상입니다. 지금 ${unlockPassphrase.length}자입니다.`
              : "암호구는 이 백엔드 프로세스의 메모리에만 보관됩니다. 디스크에 쓰지 않으며, " +
                "백엔드를 다시 띄우면 다시 잠깁니다."}
          </p>
          <div>
            <button
              disabled={busy || unlockPassphrase === "" || unlockTooShort}
              onClick={unlock}
            >
              잠금 해제
            </button>
          </div>
          <p className="font-sans text-[11px] leading-[1.4] text-ink-3 m-0">
            사람이 없는 실행(CI 등)에서는 백엔드 프로세스에 환경 변수{" "}
            <span className="font-mono">{PASSPHRASE_ENV}</span> 로 공급할 수도 있습니다. 암호구
            자체를 없애려면 아래에서 키를 교체하세요 — 교체하면 보관된 민감 값은 다시
            입력해야 합니다.
          </p>
        </section>
      )}

      {/* 열려 있다는 것도 상태다. 알려주지 않으면 사용자는 매번 실행해 봐야 안다. */}
      {protectedKey && unlocked && (
        <section
          role="note"
          className="bg-panel border border-hair rounded-base bg-sunken-2 p-[14px] mt-s4"
        >
          <div className="flex gap-s2 items-center">
            <strong>비밀키가 열려 있습니다</strong>
            <span className="flex-1" />
            <Button disabled={busy} onClick={lock}>
              다시 잠그기
            </Button>
          </div>
          <p className="font-sans text-[13px] leading-[1.4] mt-s2 mx-0 mb-0">
            암호구로 보호된 키이며, 이 백엔드 프로세스가 암호구를 들고 있습니다. 민감
            변수를 쓰는 재실행과 AI 작성이 가능합니다. <b>백엔드를 다시 띄우면 다시
            잠깁니다.</b>
          </p>
        </section>
      )}

      {!hasKeys && (
        <section
          className="bg-panel border border-hair rounded-base bg-sunken-2 p-[14px] mt-s4 flex flex-col gap-[10px]"
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
            className={`why ${tooShort ? "fail-ink" : ""}`.trimEnd()}
          >
            {tooShort
              ? `암호구는 8자 이상이어야 합니다. 지금 ${passphrase.length}자입니다.`
              : "암호구를 걸려면 8자 이상 200자 이하로 적으세요."}
          </p>
          <p className="font-sans text-[11px] leading-[1.4] text-ink-3 m-0">
            암호구를 걸면 비밀키 <b>파일</b>이 잠깁니다. 잊으면 보관된 값을 읽을 수 없고,
            제품이 복구해 줄 방법은 없습니다. 만든 직후에는 바로 실행할 수 있고, 백엔드를
            다시 띄운 뒤에는 이 화면에서 잠금을 해제하면 됩니다.
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
          className="bg-panel border border-hair rounded-base border-fail p-[14px] mt-s4 flex flex-col gap-[10px]"
        >
          <strong className="text-fail">키 교체·삭제</strong>
          <p className="font-sans text-[13px] leading-[1.4] m-0">
            <b>되돌릴 수 없습니다.</b> 키는 장비에 하나이므로 <b>이 장비의 모든 ITB 프로젝트</b>
            에서 지금 키로 봉인된 민감 값이 전부 못 읽게 됩니다. 열려 있는 프로젝트의 암호문은
            함께 비우고, 다른 프로젝트의 암호문은 그 프로젝트를 열 때 재입력을 안내합니다.
          </p>
          {/* 영향 범위를 숫자와 이름으로 보인다 — "이 프로젝트" 라고만 말하면 나머지가
              조용히 깨진다 (UX U-09). */}
          <p className="font-sans text-[13px] leading-[1.4] m-0" data-sealed-projects>
            {status === null ? (
              "영향받는 프로젝트를 확인하는 중…"
            ) : status.sealed_projects.length === 0 ? (
              "지금 키로 봉인된 값을 가진 프로젝트는 없습니다."
            ) : (
              <>
                영향받는 프로젝트 <b>{status.sealed_projects.length}개</b>:{" "}
                {status.sealed_projects.join(", ")}
              </>
            )}
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
            className={`why ${newTooShort ? "fail-ink" : ""}`.trimEnd()}
          >
            {newTooShort
              ? `암호구는 8자 이상이어야 합니다. 지금 ${newPassphrase.length}자입니다.`
              : "암호구를 걸려면 8자 이상 200자 이하로 적으세요."}
          </p>

          <label htmlFor="destroy-confirm">
            확인 문구 — <span className="font-mono">{DESTROY_CONFIRM}</span> 를 그대로 입력하세요
          </label>
          <input
            id="destroy-confirm"
            className="font-mono"
            value={confirm}
            onChange={(e) => setConfirm(e.target.value)}
            placeholder={DESTROY_CONFIRM}
            autoComplete="off"
          />

          <div className="flex items-center gap-s2">
            <button disabled={busy || !confirmed || newTooShort} onClick={regenerate}>
              키 교체
            </button>
            <Button disabled={busy || !confirmed} onClick={destroy}>
              키 삭제
            </Button>
          </div>
          <p className="font-sans text-[11px] leading-[1.4] text-ink-3 m-0">
            <b>교체</b>는 지우고 새 키를 바로 만듭니다. <b>삭제</b>는 지우기만 합니다 — 키가
            없으면 민감 값을 새로 저장할 수도, 기존 값을 읽을 수도 없습니다.
          </p>
        </section>
      )}
    </main>
  );
}
