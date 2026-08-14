#!/usr/bin/env sh
set -eu
cd "$(dirname "$0")"
exec python3 -m roi_web --host 127.0.0.1 --port 8877
