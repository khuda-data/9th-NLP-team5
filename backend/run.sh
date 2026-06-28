#!/usr/bin/env bash
# 로컬 개발 서버 실행 스크립트
set -euo pipefail
cd "$(dirname "$0")"

# 1) 가상환경
if [ ! -d ".venv" ]; then
  echo "[*] .venv 생성 중..."
  python3 -m venv .venv
fi
# shellcheck disable=SC1091
source .venv/bin/activate

# 2) 의존성
echo "[*] 의존성 설치/확인..."
pip install -q -r requirements.txt

# 3) .env 준비 (main.py 의 load_dotenv() 가 자동으로 읽음)
if [ ! -f ".env" ]; then
  cp .env.example .env
  echo "[!] .env 를 새로 만들었어. ANTHROPIC_API_KEY 를 채워야 /generate, /regenerate 가 동작해."
fi

# 4) 실행
HOST="${HOST:-0.0.0.0}"
PORT="${PORT:-8000}"
echo "[*] http://localhost:${PORT}/docs 에서 API 문서 확인 가능"
exec uvicorn main:app --host "$HOST" --port "$PORT" --reload
