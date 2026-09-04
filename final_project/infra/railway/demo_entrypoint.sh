#!/usr/bin/env bash
set -euo pipefail

if [[ "${DEMO_MODE:-false}" != "true" ]]; then
  echo "Demo service is dormant. Set DEMO_MODE=true and redeploy to start it."
  exit 0
fi

exec "$@"
