#!/bin/sh
set -eu
PORT="${PORT:-10000}"
export PORT
envsubst '${PORT}' < /etc/nginx/templates/default.conf.template > /etc/nginx/conf.d/default.conf
cd /opt/rf983/backend
uvicorn app.main:app --host 127.0.0.1 --port 8000 &
API_PID=$!
nginx -g 'daemon off;' &
NGINX_PID=$!
cleanup() {
  kill "$API_PID" "$NGINX_PID" 2>/dev/null || true
}
trap cleanup INT TERM EXIT
while kill -0 "$API_PID" 2>/dev/null && kill -0 "$NGINX_PID" 2>/dev/null; do
  sleep 2
done
cleanup
wait "$API_PID" 2>/dev/null || true
wait "$NGINX_PID" 2>/dev/null || true
exit 1
