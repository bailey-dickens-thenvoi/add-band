#!/usr/bin/env bash
set -euo pipefail

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
: "${RESULTS_DIR:?RESULTS_DIR is required}"
mkdir -p -- "$RESULTS_DIR"
RESULTS_DIR="$(cd -- "$RESULTS_DIR" && pwd)"
export RESULTS_DIR
python3 "$script_dir/report.py" "$RESULTS_DIR"

# This entrypoint is exclusively for the local ephemeral platform.
for name in BAND_REST_URL BAND_BASE_URL; do
  case "${!name:-}" in
    http://127.0.0.1:4000|http://localhost:4000) ;;
    *) echo 'Host REST endpoints must explicitly target the local test stack.' >&2; exit 1 ;;
  esac
done
case "${BAND_WS_URL:-}" in
  ws://127.0.0.1:4000/api/v1/socket/websocket|ws://localhost:4000/api/v1/socket/websocket) ;;
  *) echo 'Host WebSocket endpoint must explicitly target the local test stack.' >&2; exit 1 ;;
esac
[[ "${BAND_CONTAINER_REST_URL:-}" == 'http://host.docker.internal:4000' ]] || exit 1
[[ "${BAND_CONTAINER_WS_URL:-}" == 'ws://host.docker.internal:4000/api/v1/socket/websocket' ]] || exit 1
[[ -n "${BAND_API_KEY_USER:-}" ]] || exit 1

export PA_HARNESSES=openclaw PA_TEST_LANE=integration PA_MODEL_MODE=strict PA_STANDIN=true
export E2E_TESTS_ENABLED=true E2E_TIMEOUT=120
export ANTHROPIC_API_KEY=pa-strict-dummy-not-a-provider-key
export PYTHON_DOTENV_DISABLED=1 BAND_E2E_AUTOCLEAN=true BAND_E2E_ORPHAN_SWEEP=false
unset ANTHROPIC_AUTH_TOKEN OPENAI_API_KEY BAND_USER_API_KEY BAND_SDK_PATH PYTHONPATH PYTHONHOME

work_dir="$(mktemp -d)"
trap 'rm -rf -- "$work_dir"' EXIT
export UV_PROJECT_ENVIRONMENT="$work_dir/venv"
cd -- "$script_dir/../../pa-conformance"
set -a
source pins.env
set +a
# Raw subprocess output may contain failed request bodies. Publish only the
# sanitized report, never these temporary diagnostics or raw pytest XML.
# The locked SDK's .claude submodule is assistant configuration, not package
# code. Avoid requiring private configuration-repo access to build the SDK.
GIT_CONFIG_COUNT=1 GIT_CONFIG_KEY_0=submodule..claude.update GIT_CONFIG_VALUE_0=none \
  uv sync --frozen --python 3.12 >"$work_dir/setup.log" 2>&1
set +e
"$work_dir/venv/bin/python" -m pytest tests/test_onboarding_scripted.py \
  --junitxml="$work_dir/raw.xml" --tb=no -q --reruns=0 \
  >"$work_dir/pytest.log" 2>&1
test_status=$?
set -e
python3 "$script_dir/report.py" "$RESULTS_DIR" "$work_dir/raw.xml" "$test_status"
