#!/bin/sh
set -eu

STAMP_DIR="node_modules/.dev-container"
STAMP_FILE="$STAMP_DIR/install-state"
PLATFORM="$(uname -s)-$(uname -m)"
LOCK_HASH="$(sha256sum package-lock.json | awk '{print $1}')"

needs_install=0

if [ ! -d node_modules ]; then
  needs_install=1
elif [ ! -x node_modules/.bin/vite ]; then
  needs_install=1
elif [ ! -f "$STAMP_FILE" ]; then
  needs_install=1
else
  recorded_platform="$(sed -n '1p' "$STAMP_FILE" || true)"
  recorded_lock_hash="$(sed -n '2p' "$STAMP_FILE" || true)"

  if [ "$recorded_platform" != "$PLATFORM" ] || [ "$recorded_lock_hash" != "$LOCK_HASH" ]; then
    needs_install=1
  fi
fi

if [ "$needs_install" -eq 1 ]; then
  echo "Installing ui-new dependencies for $PLATFORM"
  npm ci
  mkdir -p "$STAMP_DIR"
  printf '%s\n%s\n' "$PLATFORM" "$LOCK_HASH" > "$STAMP_FILE"
fi

exec npm run dev -- --host 0.0.0.0 --port 5173
