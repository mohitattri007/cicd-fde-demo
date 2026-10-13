#!/usr/bin/env bash
set -euo pipefail
BASE_URL="${1:?Usage: scripts/smoke_test.sh http://localhost:8000 [expected-version]}"
EXPECTED_VERSION="${2:-}"

health="$(curl --fail --silent --show-error "${BASE_URL%/}/health")"
echo "Health response: ${health}"
python -c 'import json,sys; data=json.loads(sys.argv[1]); assert data.get("status")=="ok", data' "$health"
version="$(curl --fail --silent --show-error "${BASE_URL%/}/version")"
echo "Version response: ${version}"
if [[ -n "$EXPECTED_VERSION" ]]; then
  python -c 'import json,sys; data=json.loads(sys.argv[1]); assert data.get("version")==sys.argv[2], (data,sys.argv[2])' "$version" "$EXPECTED_VERSION"
fi
echo "Smoke tests passed."
