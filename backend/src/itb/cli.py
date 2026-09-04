"""`itb` 명령. FR-088a.

`pyproject.toml` 이 `itb = "itb.cli:main"` 을 선언하는데 이 모듈이 없어 콘솔 스크립트가
설치돼 있으면서 임포트 오류로 죽었다 (002 조사 중 발견). README 가 안내하는
`uvicorn itb.api.app:app` 과 같은 것을 한 줄로 띄운다.

**로컬 인터페이스에만 바인드한다.** 단독 로컬 도구이므로(001 FR-088) 바깥에서 접근할
수 있게 열어 줄 이유가 없다. `--host` 를 두지 않은 것은 의도다.
"""

from __future__ import annotations

import argparse
import sys

from itb.api.state import BIND_HOST, BIND_PORT


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="itb",
        description="Interactive AI Test Builder — 브라우저 기반 E2E 테스트 자동화 도구",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=BIND_PORT,
        help=f"들을 포트 (기본 {BIND_PORT})",
    )
    parser.add_argument("--reload", action="store_true", help="개발용 자동 재시작")
    args = parser.parse_args(argv)

    try:
        import uvicorn
    except ImportError:  # pragma: no cover - 의존성은 설치되어 있다
        print("uvicorn 이 설치돼 있지 않습니다. `uv sync` 후 다시 시도하세요.", file=sys.stderr)
        return 1

    print(f"Interactive AI Test Builder — http://{BIND_HOST}:{args.port}")
    print("테스트 정의는 ~/.local/share/itb/projects/ 에, 설정과 키는 ~/.config/itb/ 에 있습니다.")
    uvicorn.run(
        "itb.api.app:app",
        host=BIND_HOST,
        port=args.port,
        reload=args.reload,
    )
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
