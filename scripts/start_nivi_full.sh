#!/usr/bin/env bash
set -euo pipefail
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_ROOT"
command -v uv >/dev/null || { echo "请先安装 uv，并确保 uv 位于 PATH 中。"; exit 1; }
if [[ ! -f .env ]]; then
  echo "请先复制 .env.example 为 .env，填写模型与腾讯云密钥、邀请码和管理员口令。"
  exit 1
fi
uv sync --frozen
uv run python - <<'CHECK'
import os
from dotenv import load_dotenv
load_dotenv('.env')
required = ['MODEL_API_KEY', 'INVITE_CODES']
if os.getenv('ASR_PROVIDER', 'mock') == 'tencent_realtime':
    required += ['TENCENT_ASR_APPID', 'TENCENT_ASR_SECRET_ID', 'TENCENT_ASR_SECRET_KEY']
missing = [key for key in required if not os.getenv(key, '').strip()]
if missing:
    raise SystemExit('请在 .env 中填写：' + ', '.join(missing))
CHECK
if [[ "${NIVI_REBUILD_FRONTEND:-0}" == "1" || ! -f backend/app/static/index.html ]]; then
  command -v npm >/dev/null || { echo "重新构建页面需要 Node.js 和 npm。"; exit 1; }
  (cd frontend && npm ci && npm run build)
fi
export PYTHONPATH="$PROJECT_ROOT/backend${PYTHONPATH:+:$PYTHONPATH}"
echo "NIVI：http://127.0.0.1:8001（Ctrl+C 停止服务）"
exec uv run uvicorn app.main:app --host 127.0.0.1 --port 8001
