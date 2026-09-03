/**
 * 프로젝트 생성·열기 (T066). **확정 디자인에 없는 화면** — 8화면의 시각 언어를 따른다
 * (spec 디자인 차이 3).
 */
import { useState } from "react";

import { ApiError, project, type ProjectView } from "../api/client";

export function ProjectSetup({ onOpened }: { onOpened: (p: ProjectView) => void }) {
  const [path, setPath] = useState("");
  const [name, setName] = useState("");
  const [startUrl, setStartUrl] = useState("");
  const [testIdAttr, setTestIdAttr] = useState("data-testid");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const run = async (action: () => Promise<ProjectView>) => {
    setBusy(true);
    setError(null);
    try {
      onOpened(await action());
    } catch (exc) {
      // 서버 메시지를 그대로 보여준다 — 무엇을 해야 하는지 알려주도록 쓰여 있다.
      setError(exc instanceof ApiError ? exc.message : String(exc));
    } finally {
      setBusy(false);
    }
  };

  return (
    <main style={{ maxWidth: 560, margin: "48px auto", padding: "0 16px" }}>
      <h1 style={{ fontFamily: "var(--font-display)", fontSize: 24 }}>프로젝트</h1>
      <p className="muted">
        테스트 정의는 이 디렉터리의 <code>tests/</code> 에 평문 YAML 로 저장됩니다. 그대로
        버전 관리에 넣을 수 있습니다. 비밀 값과 실행 산출물은 <code>.gitignore</code> 로
        제외됩니다.
      </p>

      <div className="card" style={{ marginTop: 16 }}>
        <label htmlFor="path">프로젝트 디렉터리 (절대 경로)</label>
        <input
          id="path"
          value={path}
          onChange={(e) => setPath(e.target.value)}
          placeholder="/Users/me/tests/dataplatform"
        />

        <label htmlFor="name">프로젝트 이름</label>
        <input id="name" value={name} onChange={(e) => setName(e.target.value)} />

        <label htmlFor="url">기본 시작 URL</label>
        <input
          id="url"
          value={startUrl}
          onChange={(e) => setStartUrl(e.target.value)}
          placeholder="https://example.internal/login"
        />

        <label htmlFor="attr">testId 속성명</label>
        <input id="attr" value={testIdAttr} onChange={(e) => setTestIdAttr(e.target.value)} />
        <p className="dim" style={{ fontSize: 12, marginTop: 4 }}>
          대상 앱이 쓰는 속성명입니다. <code>data-test</code>, <code>data-cy</code> 를 쓰는
          앱도 흔합니다. 요소를 찾는 최우선 기준이 됩니다.
        </p>

        {error !== null && (
          <p style={{ color: "var(--fail-dark)", whiteSpace: "pre-wrap" }}>{error}</p>
        )}

        <div className="row" style={{ justifyContent: "flex-end", marginTop: 16 }}>
          <button
            className="secondary"
            disabled={busy || path.trim() === ""}
            onClick={() => run(() => project.open(path.trim()))}
          >
            기존 프로젝트 열기
          </button>
          <button
            disabled={busy || path.trim() === "" || name.trim() === "" || startUrl.trim() === ""}
            onClick={() =>
              run(() =>
                project.create({
                  path: path.trim(),
                  name: name.trim(),
                  default_start_url: startUrl.trim(),
                  test_id_attribute: testIdAttr.trim() || "data-testid",
                }),
              )
            }
          >
            새로 만들기
          </button>
        </div>
      </div>
    </main>
  );
}
