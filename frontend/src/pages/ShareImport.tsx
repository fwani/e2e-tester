/**
 * 공유 파일에서 가져오기 (019 US2·US3·US5).
 *
 * 세 걸음이다 — **파일 고르기 → 계획 확인 → 확정**. 계획 단계에서는 디스크에 아무것도
 * 만들어지지 않으므로, 사용자는 무엇이 생길지 보고 취소할 수 있다.
 *
 * 확정 뒤에는 **채워야 할 값**을 보여 준다 (US3). 민감한 것과 그렇지 않은 것을 한 목록에
 * 두되 저장 위치가 다름을 구분한다 — 받는 사람에게는 둘 다 "채워야 실행되는 것" 이고,
 * 다른 것은 어디에 저장되느냐뿐이다.
 *
 * 「엑셀에서 가져오기」(014)와 **다른 것**이다. 그쪽은 초안을 만들고 녹화가 필요하다.
 * 이쪽은 실행 가능한 테스트를 그대로 복원한다.
 */
import { useState } from "react";

import {
  ApiError,
  shareImport,
  type SharePlanView,
  type ShareReportView,
  type SharePlannedValue,
} from "../api/client";
import { ErrorNotice, describeError, type ErrorInfo } from "../components/ErrorNotice";
import { paths } from "../lib/paths";
import { Button, ButtonLink } from "../ui/Button";
import { Input } from "../ui/Input";
import { FieldLabel } from "../ui/Label";
import { NativeSelect } from "../ui/NativeSelect";
import { Notice } from "../ui/Notice";
import { Pane, PaneHead } from "../ui/Surface";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "../ui/Table";

export interface ShareImportProps {
  /** 열린 프로젝트가 있는가. 없으면 「이 프로젝트로」를 고를 수 없다. */
  hasOpenProject?: boolean;
  onDone?: (report: ShareReportView) => void;
  onClose?: () => void;
}

type Target = "new" | "current";

export function ShareImport({ hasOpenProject = false, onDone, onClose }: ShareImportProps) {
  const [target, setTarget] = useState<Target>(hasOpenProject ? "current" : "new");
  const [plan, setPlan] = useState<SharePlanView | null>(null);
  const [report, setReport] = useState<ShareReportView | null>(null);
  const [projectName, setProjectName] = useState("");
  const [startUrl, setStartUrl] = useState("");
  const [values, setValues] = useState<Record<string, string>>({});
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<ErrorInfo | null>(null);

  const pick = (file: File) => {
    setBusy(true);
    setError(null);
    setReport(null);
    void shareImport
      .plan(file, target)
      .then((next) => {
        setPlan(next);
        setProjectName(next.target_project_name ?? "");
      })
      .catch((exc: unknown) => setError(describeError(exc)))
      .finally(() => setBusy(false));
  };

  const commit = () => {
    if (plan === null) return;
    setBusy(true);
    setError(null);
    void shareImport
      .commit({
        plan_id: plan.plan_id,
        project_name: target === "new" ? projectName || null : null,
        default_start_url: startUrl.trim() || null,
        // **비민감 값만 보낸다.** 민감 값을 실으면 서버가 400 으로 거절한다 (C12).
        variable_values: Object.fromEntries(
          Object.entries(values).filter(([name]) =>
            plan.required_values.some((v) => v.name === name && !v.sensitive),
          ),
        ),
      })
      .then((next) => {
        setReport(next);
        setPlan(null);
        onDone?.(next);
      })
      .catch((exc: unknown) => {
        setError(describeError(exc));
        /*
          계획이 낡았으면 서버가 **다시 세운 계획**을 실어 보낸다 (SHARE_PLAN_STALE).
          그것으로 갈아 끼운다 — 파일을 다시 고르게 하면 사용자가 한 입력이 사라진다.
        */
        if (exc instanceof ApiError && exc.code === "SHARE_PLAN_STALE") {
          const fresh = exc.detail.plan as SharePlanView | undefined;
          if (fresh) setPlan(fresh);
        }
      })
      .finally(() => setBusy(false));
  };

  const blocked = plan !== null && plan.blocking.length > 0;

  return (
    <section data-screen="share-import">
      <header>
        <h1>공유 파일에서 가져오기</h1>
        <p>동료가 보낸 묶음 파일을 골라 테스트를 복원합니다.</p>
      </header>

      {error !== null && <ErrorNotice error={error} />}

      {plan === null && report === null && (
        <Pane>
          <PaneHead>파일 고르기</PaneHead>
          {hasOpenProject && (
            <FieldLabel>
              <NativeSelect
                data-testid="share-import-target"
                aria-label="가져올 대상"
                value={target}
                onChange={(e) => setTarget(e.target.value as Target)}
              >
                <option value="current">이 프로젝트에 더하기</option>
                <option value="new">새 프로젝트로 만들기</option>
              </NativeSelect>
            </FieldLabel>
          )}
          <Input
            type="file"
            accept=".yaml,.yml,application/yaml"
            data-testid="share-import-file"
            aria-label="묶음 파일"
            disabled={busy}
            onChange={(e) => {
              const file = e.target.files?.[0];
              if (file) pick(file);
            }}
          />
        </Pane>
      )}

      {plan !== null && (
        <>
          <Pane>
            <PaneHead>들어올 것</PaneHead>
            <p data-testid="share-import-summary">
              {plan.target === "new"
                ? `새 프로젝트 「${plan.target_project_name ?? ""}」`
                : "이 프로젝트"}
              에 테스트 {plan.tests.filter((t) => t.status === "create").length}건이 들어옵니다.
            </p>
            <Table data-testid="share-import-tests">
              <TableHeader>
                <TableRow>
                  <TableHead>묶음 안</TableHead>
                  <TableHead>여기서는</TableHead>
                  <TableHead>이름</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {plan.tests.map((t) => (
                  <TableRow key={t.source_id}>
                    <TableCell>{t.source_id}</TableCell>
                    <TableCell>
                      {t.status === "skip" ? `건너뜀 — ${t.reason ?? ""}` : t.target_id}
                      {/* 바뀐 번호를 강조한다 — 사용자의 설계서에는 원래 번호가 적혀 있다. */}
                      {t.renumbered && " (번호 변경)"}
                    </TableCell>
                    <TableCell>{t.name}</TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </Pane>

          {plan.groups.length > 0 && (
            <Pane>
              <PaneHead>그룹</PaneHead>
              <ul data-testid="share-import-groups">
                {plan.groups.map((g) => (
                  <li key={g.source_prefix}>
                    {g.source_name} — {g.action === "reuse" ? "기존 그룹에 넣음" : g.target_prefix}
                    {g.reason && ` (${g.reason})`}
                  </li>
                ))}
              </ul>
            </Pane>
          )}

          {plan.required_values.length > 0 && (
            <Pane>
              <PaneHead>가져온 뒤 채워야 할 값</PaneHead>
              <ValueList values={plan.required_values} />
            </Pane>
          )}

          {plan.notices.map((n) => (
            <Notice key={n.code} tone="ai" data-testid={`share-import-notice-${n.code}`}>
              {n.message}
            </Notice>
          ))}

          {blocked && (
            <Notice tone="fail" data-testid="share-import-blocking">
              {plan.blocking.join(" ")}
            </Notice>
          )}

          <Pane>
            <PaneHead>확정 전에 고칠 수 있는 것</PaneHead>
            {plan.target === "new" && (
              <FieldLabel>
                프로젝트 이름
                <Input
                  data-testid="share-import-name"
                  value={projectName}
                  onChange={(e) => setProjectName(e.target.value)}
                />
              </FieldLabel>
            )}
            {/* 받는 쪽 환경이 다를 수 있다 (spec Edge Cases). 비우면 묶음의 값을 쓴다. */}
            <FieldLabel>
              시작 주소 (비우면 묶음의 값)
              <Input
                data-testid="share-import-url"
                placeholder="https://..."
                value={startUrl}
                onChange={(e) => setStartUrl(e.target.value)}
              />
            </FieldLabel>
          </Pane>

          <div>
            <Button
              variant="primary"
              data-action="share.import-commit"
              disabled={busy || blocked}
              onClick={commit}
            >
              {busy ? "가져오는 중…" : "가져오기"}
            </Button>
            <Button data-action="share.import-cancel" onClick={() => setPlan(null)}>
              취소
            </Button>
          </div>
        </>
      )}

      {report !== null && (
        <ShareImportDone
          report={report}
          values={values}
          onChange={(name, value) => setValues((prev) => ({ ...prev, [name]: value }))}
          onClose={onClose}
        />
      )}
    </section>
  );
}

/** 채워야 할 값 목록. **민감·비민감을 한 목록에 두되 저장 위치를 구분한다** (FR-048). */
function ValueList({ values }: { values: SharePlannedValue[] }) {
  return (
    <Table data-testid="share-import-values">
      <TableHeader>
        <TableRow>
          <TableHead>이름</TableHead>
          <TableHead>어디에 쓰이나</TableHead>
          <TableHead>상태</TableHead>
        </TableRow>
      </TableHeader>
      <TableBody>
        {values.map((v) => (
          <TableRow key={v.name}>
            <TableCell>
              {v.name}
              {/* 선언이 없어 보충한 것임을 알린다 — 조용히 고치면 파일이 온전했다고 믿는다. */}
              {!v.declared && " (선언이 없어 보충함)"}
            </TableCell>
            <TableCell>
              {v.usages.map((u) => `${u.test_id} · ${u.step_label ?? u.step_id}`).join(", ")}
            </TableCell>
            <TableCell>
              {v.sensitive ? "봉인 저장" : "테스트 정의"}
              {v.already_stored === true && " — 이미 값이 있음"}
              {v.env_provided === true && " — 환경 변수로 공급됨"}
              {v.blocks_run && " — 채워야 실행됩니다"}
            </TableCell>
          </TableRow>
        ))}
      </TableBody>
    </Table>
  );
}

/**
 * 가져오기 결과 (US3).
 *
 * **남은 할 일을 보여 주는 것이 이 화면의 목적이다.** 「가져왔습니다」만 말하고 끝내면,
 * 받은 사람은 실행이 막힐 때까지 무엇이 빠졌는지 모른다.
 */
export function ShareImportDone({
  report,
  values,
  onChange,
  onClose,
}: {
  report: ShareReportView;
  values: Record<string, string>;
  onChange: (name: string, value: string) => void;
  onClose?: () => void;
}) {
  const todo = report.required_values;
  return (
    <>
      <Notice tone="pass" data-testid="share-import-done">
        「{report.project_name}」에 테스트 {report.created_tests.length}건을 가져왔습니다.
        {report.project_renamed_from !== null &&
          ` 같은 이름이 있어 「${report.project_renamed_from}」 대신 이 이름으로 만들었습니다.`}
      </Notice>

      {report.renumbered.length > 0 && (
        <Pane>
          <PaneHead>번호가 바뀐 테스트</PaneHead>
          <ul data-testid="share-import-renumbered">
            {report.renumbered.map((r) => (
              <li key={r.from}>
                {r.from} → {r.to}
              </li>
            ))}
          </ul>
        </Pane>
      )}

      {report.skipped.length > 0 && (
        <Notice tone="warn" data-testid="share-import-skipped">
          건너뛴 테스트 {report.skipped.length}건:{" "}
          {report.skipped.map((s) => `${s.source_id} (${s.reason})`).join(", ")}
        </Notice>
      )}

      {todo.length > 0 && (
        <Pane>
          <PaneHead>채워야 실행됩니다</PaneHead>
          <ValueList values={todo} />
          <p>
            비밀번호 같은 민감 값은 묶음에 들어 있지 않습니다. 아래에서 직접 입력하면 이
            장비의 키로 봉인되어 저장됩니다.
          </p>
          {todo
            .filter((v) => !v.sensitive)
            .map((v) => (
              <FieldLabel key={v.name}>
                {v.name}
                <Input
                  data-testid={`share-import-value-${v.name}`}
                  value={values[v.name] ?? ""}
                  onChange={(e) => onChange(v.name, e.target.value)}
                />
              </FieldLabel>
            ))}
          {todo.some((v) => v.sensitive) && (
            <ButtonLink data-action="share.import-secrets" href={paths.secrets()}>
              민감 값 채우러 가기
            </ButtonLink>
          )}
        </Pane>
      )}

      {onClose !== undefined && (
        <Button data-action="share.import-close" onClick={onClose}>
          테스트 목록으로
        </Button>
      )}
    </>
  );
}
