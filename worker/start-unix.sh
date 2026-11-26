#!/usr/bin/env sh
set -eu
cd "$(dirname "$0")"
if [ ! -d .venv ]; then
  python3 -m venv .venv
fi
if [ ! -f .env ]; then
  cp .env.example .env
  echo "Created worker/.env. Set RF983_WORKER_TOKEN, then run this script again."
  exit 0
fi
set -a
. ./.env
set +a
.venv/bin/python worker.py
