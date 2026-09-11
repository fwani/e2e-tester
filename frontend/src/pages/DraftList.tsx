/**
 * 초안 목록 (014 US3 · FR-027·FR-029·FR-035).
 *
 * **초안은 테스트가 아니다.** 그래서 테스트 목록의 행으로 섞지 않고 이 영역에 따로 둔다 —
 * 실행할 수 없고, 결말이 없고, 할 수 있는 일이 「녹화 시작」과 「삭제」 둘뿐이다. 같은 표에
 * 두면 사용자가 행마다 무엇을 할 수 있는지 매번 확인해야 한다.
 *
 * 「몇 건 남았다」를 크게 보이는 것이 이 화면의 일이다 (FR-035). 설계서에서 스무 건을
 * 들여온 사용자에게 필요한 것은 목록이 아니라 **다음에 무엇을 할지**다.
 */
import { useState } from "react";

import type { DraftRow } from "../api/client";
import { drafts as draftsApi } from "../api/client";
import { describeError } from "../components/ErrorNotice";
import type { ErrorInfo } from "../components/ErrorNotice";

import { Button } from "../ui/Button";

export function DraftSection({
  drafts,
  problems,
  busy,
  onRecord,
  onChanged,
  onError,
}: {
  drafts: DraftRow[];
  problems: string[];
  busy: boolean;
  /** 초안에서 AI 작성 세션을 시작한다 — 기존 「테스트 만들기 → AI」와 같은 경로다. */
  onRecord: (draft: DraftRow) => void;
  onChanged: () => void;
  onError: (error: ErrorInfo) => void;
}) {
  const [confirming, setConfirming] = useState<string | null>(null);

  if (drafts.length === 0 && problems.length === 0) return null;

  const remove = (id: string) => {
    setConfirming(null);
    void draftsApi
      .remove(id)
      .then(onChanged)
      .catch((exc: unknown) => onError(describeError(exc)));
  };

  return (
    <section data-draft-section className="mt-[20px]">
 <div className="flex gap-s2 items-baseline mb-s2">
        {/* 표제로 둔다 — 낭독기가 구획을 건너뛸 수 있어야 한다. */}
        <h2 className="font-sans text-[13px] font-semibold leading-none m-0">
          녹화하지 않은 초안
        </h2>
        <span className="font-mono text-[12px] leading-none text-ink-3" data-draft-count>
          {drafts.length}
        </span>
        <span className="font-sans text-[11px] leading-[1.4] text-ink-3">
          엑셀에서 들여온 항목입니다. 하나씩 녹화하면 테스트가 됩니다.
        </span>
      </div>

      {problems.length > 0 && (
        <div className="bg-warn-t border border-warn-line rounded-base py-s2 px-[10px] mb-s2">
          {problems.map((p) => (
            <div key={p} className="font-sans text-[11px] leading-[1.4] text-ink-3">
              {p}
            </div>
          ))}
        </div>
      )}

      <table className="w-full border-collapse">
        {/* `scope` 가 없으면 낭독기가 칸을 읽을 때 어느 열인지 말할 수 없다. */}
        <thead className="bg-sunken border-b border-hair-2">
          <tr>
            <th scope="col" className="py-[6px] px-s2 w-[110px]">희망 번호</th>
            <th scope="col" className="py-[6px] px-s2">대상기능</th>
            <th scope="col" className="py-[6px] px-s2 w-[110px]">수행자</th>
            <th scope="col" className="py-[6px] px-s2">출처</th>
            <th scope="col" className="py-[6px] px-s2 w-[190px]">
              <span className="font-mono text-[11px] font-semibold leading-none tracking-[.08em] uppercase text-ink-3">할 수 있는 일</span>
            </th>
          </tr>
        </thead>
        <tbody>
          {drafts.map((draft) => (
            <tr key={draft.draft_id} data-draft-row={draft.draft_id}>
              <td className="py-[6px] px-s2">
                <span className="font-mono">{draft.desired_test_id ?? "—"}</span>
                {draft.desired_test_id !== null && !draft.desired_id_available && (
                  /*
                    희망 번호가 이미 쓰이고 있다. **막지 않는다** — 저장할 때 다른 번호를
                    받는다는 예고일 뿐이다 (FR-032). 초안은 번호를 예약하지 않는다.
                  */
                  <div className="font-sans text-[11px] leading-[1.4] text-ink-3" data-id-taken={draft.draft_id}>
                    이 번호는 이미 쓰입니다. 저장할 때 다른 번호를 받습니다.
                  </div>
                )}
              </td>
              <td className="py-[6px] px-s2">
                <div id={`draft-name-${draft.draft_id}`}>{draft.name}</div>
                {draft.description !== null && <div className="font-sans text-[11px] leading-[1.4] text-ink-3">{draft.description}</div>}
              </td>
              <td className="py-[6px] px-s2">{draft.actor ?? "—"}</td>
              <td className="py-[6px] px-s2">
                <span className="font-sans text-[11px] leading-[1.4] text-ink-3">
                  {draft.source.file_name} · {draft.source.sheet_name} {draft.source.row}행
                </span>
              </td>
              <td className="py-[6px] px-s2 text-right">
                {/*
                  **어느 초안인지 조작에 붙인다.** 행이 스무 개면 「녹화 시작」이 스무
                  개고, 낭독기로 도는 사용자에게는 전부 같은 조작으로 들린다.

                  `aria-label` 이 아니라 `aria-describedby` 다 — 라벨을 덮으면 조작의
                  이름이 행마다 달라지고, 사용자가 화면에서 읽는 글자(「녹화 시작」)와
                  낭독기가 부르는 이름이 어긋난다. 이름은 그대로 두고 대상을 **설명**으로
                  더한다.
                */}
                {confirming === draft.draft_id ? (
 <span className="flex items-center gap-[6px] justify-end">
                    <span className="font-sans text-[11px] leading-[1.4] text-ink-3">지울까요?</span>
                    {/*
                      되돌릴 수 없는 쪽을 형태로 구분한다 — 「지우기」와 「그대로」가 같은
                      형태면 어느 쪽이 무엇을 하는지 글자를 읽어야만 알 수 있다.

                      확인 버튼에 초점을 옮긴다. 누른 버튼이 사라지면서 초점이 문서
                      처음으로 튀어, 키보드 사용자는 확인 자리를 다시 찾아야 했다.
                    */}
                    <Button
                      size="sm" variant="danger"
                      data-action="draft.delete-confirm"
                      aria-describedby={`draft-name-${draft.draft_id}`}
                      ref={(el) => el?.focus()}
                      onClick={() => remove(draft.draft_id)} >
                      지우기
                    </Button>
                    <Button
                      size="sm"
                      aria-describedby={`draft-name-${draft.draft_id}`}
                      onClick={() => setConfirming(null)} >
                      그대로
                    </Button>
                  </span>
                ) : (
 <span className="flex items-center gap-[6px] justify-end">
                    <Button
                      size="sm"
                      data-action="draft.record"
                      aria-describedby={`draft-name-${draft.draft_id}`}
                      disabled={busy}
                      onClick={() => onRecord(draft)} >
                      녹화 시작
                    </Button>
                    <Button
                      size="sm"
                      data-action="draft.delete"
                      aria-describedby={`draft-name-${draft.draft_id}`}
                      disabled={busy}
                      onClick={() => setConfirming(draft.draft_id)} >
                      지우기
                    </Button>
                  </span>
                )}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </section>
  );
}
