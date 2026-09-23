/**
 * 공유용 내보내기 (019 US1·US4).
 *
 * **확인 없이 내려받을 수 없다.** 내보내기는 되돌릴 수 없고, 파일이 나간 뒤에는 회수할
 * 방법이 없다. 나가기 전에 보이는 것이 유일한 방어선이므로(spec US4) 이 화면은 요약을
 * 먼저 그리고, 사용자가 읽은 뒤에만 내려받기를 연다.
 *
 * **평문 값을 가리지 않는다.** 이 화면의 목적이 값을 보여 주는 것이다 — 가려 놓으면 사번이나
 * 사내 계정이 섞여 있어도 발견할 수 없다 (research R11). 민감 값은 애초에 파일에 들어가지
 * 않으므로 여기 나타나지도 않는다.
 *
 * 「엑셀로 내보내기」(014)와 **다른 것**이다. 그쪽은 사람이 읽는 설계서이고 스텝을 복원하지
 * 못한다. 이름이 섞이지 않게 「공유용」을 앞에 둔다.
 */
import { useCallback, useEffect, useState } from "react";

import { share, saveBlob, type ShareExportPreview } from "../api/client";
import { ErrorNotice, describeError, type ErrorInfo } from "../components/ErrorNotice";
import { Button } from "../ui/Button";
import { Checkbox } from "../ui/Checkbox";
import { FieldLabel } from "../ui/Label";
import { Notice } from "../ui/Notice";
import { Pane, PaneHead } from "../ui/Surface";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "../ui/Table";

export interface ShareExportProps {
  /** 고른 테스트. 비었거나 없으면 프로젝트 전체다 (FR-001·FR-002). */
  testIds?: string[] | null;
  onClose?: () => void;
}

interface Done {
  filename: string;
  testCount: number;
  unreadable: number;
}

export function ShareExport({ testIds = null, onClose }: ShareExportProps) {
  const [preview, setPreview] = useState<ShareExportPreview | null>(null);
  const [acknowledged, setAcknowledged] = useState(false);
  const [busy, setBusy] = useState(false);
  const [done, setDone] = useState<Done | null>(null);
  const [error, setError] = useState<ErrorInfo | null>(null);

  /*
    **대상을 문자열 하나로 좁혀 의존성에 쓴다.** 배열을 그대로 두면 부모가 매번 새 배열을
    만들 때마다 미리보기를 다시 읽는다 — 같은 대상인데 화면이 깜빡이고, 확인 체크가 풀린다.
  */
  const selectionKey = testIds && testIds.length > 0 ? testIds.join(",") : "";

  const load = useCallback(() => {
    const picked = selectionKey === "" ? null : selectionKey.split(",");
    setError(null);
    // 선택이 바뀌면 확인을 다시 받는다 — 앞서 본 요약은 다른 대상의 것이다.
    setAcknowledged(false);
    setDone(null);
    void share
      .exportPreview(picked)
      .then(setPreview)
      .catch((exc: unknown) => setError(describeError(exc)));
  }, [selectionKey]);

  useEffect(load, [load]);

  const download = () => {
    setBusy(true);
    setError(null);
    void share
      .exportBundle(selectionKey === "" ? null : selectionKey.split(","))
      .then(({ blob, filename, testCount, unreadable }) => {
        saveBlob(blob, filename);
        setDone({ filename, testCount, unreadable });
      })
      .catch((exc: unknown) => setError(describeError(exc)))
      .finally(() => setBusy(false));
  };

  return (
    <section data-screen="share-export">
      <header>
        <h1>공유용 내보내기</h1>
        <p>
          {selectionKey === ""
            ? "프로젝트의 테스트 전부를 파일 하나로 만듭니다."
            : `고른 테스트 ${selectionKey.split(",").length}건을 파일 하나로 만듭니다.`}
        </p>
      </header>

      {error !== null && <ErrorNotice error={error} action={{ label: "다시 시도", onClick: load }} />}

      {preview !== null && (
        <>
          <Pane>
            <PaneHead>나가는 것</PaneHead>
            <dl data-testid="share-export-summary">
              <div>
                <dt>테스트</dt>
                <dd>{preview.test_count}건</dd>
              </div>
              <div>
                <dt>그룹</dt>
                <dd>{preview.group_count}개</dd>
              </div>
            </dl>
          </Pane>

          {/*
            비밀번호는 파일에 들어가지 않는다. 그 사실을 **보내는 사람에게도** 알린다 —
            "받는 사람이 왜 로그인을 못 하지" 가 나중에 나오지 않게 한다 (FR-004).
          */}
          <Notice tone="ai" data-testid="share-export-secret-notice">
            비밀번호 같은 민감 값은 파일에 들어가지 않습니다. 받는 분이 가져온 뒤 직접
            입력합니다.
            {preview.required_values.length > 0 && (
              <>
                {" "}
                받는 분이 채워야 할 항목 {preview.required_values.length}개:{" "}
                {preview.required_values.map((v) => v.name).join(", ")}
              </>
            )}
          </Notice>

          {/*
            **가리지 않는다.** 이 표의 목적이 값을 보여 주는 것이다 (research R11).
            사번·사내 계정이 섞여 있으면 여기서 발견해야 한다 — 파일이 나간 뒤에는 늦다.
          */}
          <Pane>
            <PaneHead>파일에 그대로 들어가는 값</PaneHead>
            {preview.plaintext_values.length === 0 ? (
              <p>스텝에 직접 적힌 값이 없습니다.</p>
            ) : (
              <Table data-testid="share-export-plaintext">
                <TableHeader>
                  <TableRow>
                    <TableHead>테스트</TableHead>
                    <TableHead>스텝</TableHead>
                    <TableHead>값</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {preview.plaintext_values.map((v) => (
                    <TableRow key={`${v.test_id}:${v.step_id}:${v.field}`}>
                      <TableCell>{v.test_id}</TableCell>
                      <TableCell>{v.step_label ?? v.step_id}</TableCell>
                      <TableCell>
                        {v.value}
                        {v.truncated && "…"}
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            )}
          </Pane>

          <Pane>
            <PaneHead>시작 주소</PaneHead>
            <ul data-testid="share-export-urls">
              {preview.start_urls.map((u) => (
                <li key={`${u.scope}:${u.test_id ?? ""}`}>
                  {u.scope === "project" ? "프로젝트 기본" : u.test_id} — {u.url}
                </li>
              ))}
            </ul>
          </Pane>

          {preview.unreadable.length > 0 && (
            <Notice tone="warn" data-testid="share-export-unreadable">
              읽을 수 없어 빠지는 테스트가 {preview.unreadable.length}건 있습니다. 나머지는
              그대로 나갑니다.
            </Notice>
          )}

          {done === null ? (
            <div>
              <FieldLabel>
                <Checkbox
                  data-testid="share-export-ack"
                  aria-label="위 내용을 확인했습니다"
                  checked={acknowledged}
                  onCheckedChange={setAcknowledged}
                />{" "}
                위 내용을 확인했습니다.
              </FieldLabel>
              <Button
                variant="primary"
                data-action="share.export"
                disabled={busy || !acknowledged}
                onClick={download}
              >
                {busy ? "만드는 중…" : "파일 내려받기"}
              </Button>
              {onClose !== undefined && (
                <Button data-action="share.export-cancel" onClick={onClose}>
                  취소
                </Button>
              )}
            </div>
          ) : (
            <Notice tone="pass" data-testid="share-export-done">
              {done.filename} 을 내려받았습니다. 테스트 {done.testCount}건이 담겼습니다.
              {done.unreadable > 0 && ` 읽을 수 없어 빠진 것이 ${done.unreadable}건 있습니다.`}
            </Notice>
          )}
        </>
      )}
    </section>
  );
}
