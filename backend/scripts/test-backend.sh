#!/usr/bin/env bash
# 백엔드 전량 검증. **두 계층을 모두 돈다** — 어느 한쪽이 실패하면 전체가 실패한다.
#
#   1) 병렬 계층 — 코어 수만큼 나눠 돈다 (대부분)
#   2) 순차 계층 — 경과 시간을 단언하는 검증 (`-m timing`)
#
# 왜 나누는가: 2번은 제품이 얼마나 빠른지를 잰다. 프로세스 8개가 CPU 를 나눠 쓰면
# 재는 값이 제품의 성질이 아니라 그 순간의 부하가 된다 (실측: 8분할에서 녹화 반영
# 지연이 p95 737ms, 목표 200ms). 분류는 `tests/tiers.py` 의 `TIMING_MODULES` 다.
#
#   scripts/test-backend.sh                    # 전량
#   scripts/test-backend.sh tests/unit         # 경로를 좁혀서
#
# 개발 루프에서 브라우저 계층까지 빼려면 이 스크립트가 아니라 아래를 쓴다.
#
#   uv run pytest -m "not browser and not timing"

set -euo pipefail
cd "$(dirname "$0")/.."

# 두 계층 중 하나만 실패해도 사유를 다 보고 싶다. 그래서 첫 실패에서 멈추지 않고
# 둘 다 돌린 뒤 종료 코드를 합친다 — 순차 계층이 실패했는데 병렬 계층 결과를 못 보면
# 원인을 좁히는 데 한 번 더 돌려야 한다.
set +e

echo "── 병렬 계층 (경과 시간을 재지 않는 검증) ─────────────────────────────"
uv run pytest -m "not timing" "$@"
parallel_status=$?

echo
echo "── 순차 계층 (경과 시간을 재는 검증 — 프로세스 하나로) ────────────────"
uv run pytest -m timing -n 0 "$@"
timing_status=$?

echo
if [ "$parallel_status" -eq 0 ] && [ "$timing_status" -eq 0 ]; then
  echo "두 계층 모두 통과."
  exit 0
fi

# 경로를 좁혀 돌리면 한쪽이 "선택된 검증 없음"(종료 코드 5)일 수 있다. 그것은 실패가
# 아니다 — 그 계층에 해당하는 검증이 그 경로에 없다는 뜻이다.
for name_status in "병렬:$parallel_status" "순차:$timing_status"; do
  name=${name_status%%:*}
  status=${name_status##*:}
  case "$status" in
    0) echo "$name 계층: 통과" ;;
    5) echo "$name 계층: 선택된 검증 없음 (경로를 좁혀 돌린 경우 정상)" ;;
    *) echo "$name 계층: 실패 (종료 코드 $status)" ;;
  esac
done

# 5(선택된 검증 없음)는 실패로 세지 않는다.
for status in "$parallel_status" "$timing_status"; do
  if [ "$status" -ne 0 ] && [ "$status" -ne 5 ]; then
    exit 1
  fi
done
exit 0
