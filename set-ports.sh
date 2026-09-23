#!/usr/bin/env bash
# پورت پنل را روی 9001 و پورت API را روی 9002 می‌گذارد.
# Docker و ایمیج‌ها از قبل نصب شده‌اند؛ این اسکریپت چیزی نصب نمی‌کند.
#
#   sudo bash set-ports.sh
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT"

log() { printf '\n[%s] %s\n' "$(date '+%H:%M:%S')" "$*"; }
die() { printf '\nخطا: %s\n' "$*" >&2; exit 1; }

if [[ "$(id -u)" -ne 0 ]]; then
  exec sudo bash "$ROOT/set-ports.sh" "$@"
fi

[[ -f docker-compose.yml ]] || die "docker-compose.yml کنار این اسکریپت پیدا نشد."
[[ -f .env ]] || die "فایل .env وجود ندارد. اول استقرار را انجام دهید."
command -v docker >/dev/null || die "Docker نصب نیست."
docker compose version >/dev/null || die "افزونه docker compose نصب نیست."

PUBLIC_HOST="${PUBLIC_HOST:-$(hostname -I 2>/dev/null | awk '{print $1}')}"
PUBLIC_HOST="${PUBLIC_HOST:-localhost}"
export PUBLIC_HOST

log "تنظیم پورت پنل 9001 و پورت API 9002"
python3 - <<'PY'
import os
from pathlib import Path

host = os.environ.get("PUBLIC_HOST") or "localhost"
wanted = [f"http://localhost:9001", f"http://{host}:9001"]

def upsert(text: str, key: str, value: str) -> str:
    lines = text.splitlines()
    found = False
    out = []
    prefix = key + "="
    for line in lines:
        if line.startswith(prefix):
            out.append(prefix + value)
            found = True
        else:
            out.append(line)
    if not found:
        if out and out[-1] != "":
            out.append("")
        out.append(prefix + value)
    return "\n".join(out) + "\n"

env_path = Path(".env")
env = env_path.read_text(encoding="utf-8")
existing = []
for line in env.splitlines():
    if line.startswith("CORS_ORIGINS="):
        raw = line.split("=", 1)[1]
        existing = [item.strip() for item in raw.split(",") if item.strip()]
        break
kept = []
for origin in existing + wanted:
    if origin.endswith(":3000") or origin.endswith(":8000"):
        continue
    if origin not in kept:
        kept.append(origin)
env = upsert(env, "FRONTEND_PUBLISH_PORT", "9001")
env = upsert(env, "API_PUBLISH_PORT", "9002")
env = upsert(env, "CORS_ORIGINS", ",".join(kept))
env_path.write_text(env, encoding="utf-8")

compose_path = Path("docker-compose.yml")
compose = compose_path.read_text(encoding="utf-8")
compose = compose.replace('"8000:8000"', '"${API_PUBLISH_PORT:-9002}:8000"')
compose = compose.replace('"3000:3000"', '"${FRONTEND_PUBLISH_PORT:-9001}:3000"')
compose = compose.replace('"9002:8000"', '"${API_PUBLISH_PORT:-9002}:8000"')
compose = compose.replace('"9001:3000"', '"${FRONTEND_PUBLISH_PORT:-9001}:3000"')
compose_path.write_text(compose, encoding="utf-8")
PY

if systemctl is-active --quiet firewalld; then
  log "باز کردن 9001 و 9002 در firewalld"
  firewall-cmd --permanent --remove-port=3000/tcp >/dev/null 2>&1 || true
  firewall-cmd --permanent --remove-port=8000/tcp >/dev/null 2>&1 || true
  firewall-cmd --permanent --add-port=9001/tcp
  firewall-cmd --permanent --add-port=9002/tcp
  firewall-cmd --reload
elif command -v ufw >/dev/null 2>&1 && ufw status | grep -q 'Status: active'; then
  log "باز کردن 9001 و 9002 در ufw"
  ufw delete allow 3000/tcp >/dev/null 2>&1 || true
  ufw delete allow 8000/tcp >/dev/null 2>&1 || true
  ufw allow 9001/tcp
  ufw allow 9002/tcp
fi

log "اعمال پورت‌ها بدون ساخت دوباره ایمیج"
docker compose up -d --no-build --force-recreate api frontend

wait_http() {
  local url="$1" i
  for ((i = 1; i <= 30; i++)); do
    if curl -fsS "$url" >/dev/null; then
      return 0
    fi
    sleep 2
  done
  return 1
}

log "بررسی API روی 9002"
wait_http "http://127.0.0.1:9002/health" || {
  docker compose ps
  docker compose logs --tail 60 api
  die "API روی پورت 9002 جواب نداد."
}

log "بررسی پنل روی 9001"
wait_http "http://127.0.0.1:9001/login" || {
  docker compose logs --tail 60 frontend
  die "پنل روی پورت 9001 جواب نداد."
}

cat <<EOF

پورت‌ها اعمال شد.
  پنل مدیریت:  http://${PUBLIC_HOST}:9001
  API:         http://${PUBLIC_HOST}:9002
  مستندات API: http://${PUBLIC_HOST}:9002/docs
  سلامت:       http://${PUBLIC_HOST}:9002/health
EOF
