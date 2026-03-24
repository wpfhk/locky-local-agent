#!/usr/bin/env bash
# Locky 설치 스크립트 — 저장소 클론 후 프로젝트 루트에서 실행하세요.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

echo "==> Locky 설치 ($ROOT)"

need_python() {
  if command -v python3 >/dev/null 2>&1; then
    PY="python3"
  elif command -v python >/dev/null 2>&1; then
    PY="python"
  else
    echo "python3 또는 python 이 필요합니다." >&2
    exit 1
  fi
}

need_python

"$PY" - <<'PY' || { echo "Python 3.10 이상이 필요합니다." >&2; exit 1; }
import sys
if sys.version_info < (3, 10):
    sys.exit(1)
PY

VENV="${LOCKY_VENV:-$ROOT/.venv}"
echo "==> 가상환경: $VENV"

if [[ ! -d "$VENV" ]]; then
  "$PY" -m venv "$VENV"
fi

# shellcheck disable=SC1090
source "$VENV/bin/activate"

pip install -U pip setuptools wheel
pip install -e "."

echo ""
echo "설치 완료. 아래를 셸 설정에 추가하거나, 매번 활성화하세요:"
echo "  source \"$VENV/bin/activate\""
echo "  locky --help"
echo ""
echo "전역으로 쓰려면 pipx 사용 권장:"
echo "  pipx install \"$ROOT\""
echo ""
