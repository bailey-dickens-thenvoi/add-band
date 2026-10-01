# OpenClaw platform compatibility pilot

Run `scripts/platform-compat/run.sh` on a Linux host with Docker Compose, uv,
Python 3, and access to the pinned SDK source, PyPI and container/npm registries.
The platform must already be running and have a disposable seeded user.

Required environment:

- `BAND_REST_URL` and `BAND_BASE_URL`: `http://127.0.0.1:4000`
- `BAND_WS_URL`: `ws://127.0.0.1:4000/api/v1/socket/websocket`
- `BAND_CONTAINER_REST_URL`: `http://host.docker.internal:4000`
- `BAND_CONTAINER_WS_URL`: `ws://host.docker.internal:4000/api/v1/socket/websocket`
- `BAND_API_KEY_USER`: disposable user key with agent registration permission
- `RESULTS_DIR`: output directory

OpenClaw's Compose service maps `host.docker.internal` to `host-gateway`.
The driver uses host endpoints, while the published bootstrap and OpenClaw use
container endpoints. The entrypoint rejects production endpoints.

The single scenario is `addband-openclaw-bootstrap-scripted`. It executes the
published OpenClaw bootstrap unchanged, provisions its own agent, and requires a
real Band round trip through OpenClaw using the strict scripted model service.
No real model key is supplied; a dummy Anthropic key satisfies client-side
configuration. The pilot must verify that the upstream OpenClaw build accepts
this configuration. Strict mode rejects unscripted requests and cannot forward
them upstream. This does not certify real-model behavior.

The SDK/toolkit revision comes from the existing `uv.lock`. The gateway image
comes from the catalog's pins; the bootstrap intentionally installs the published
channel plugin as written, including its floating npm resolution. Record the
add-band commit in the parent workflow; this lane does not claim all downloads
are immutable.

The entrypoint writes sanitized `results.json` and `junit.xml`, including on
dependency/setup failure. Missing/skipped/error results never pass. Temporary
raw logs and pytest XML are not published because they can contain request data.
Use a 20-minute step timeout inside the parent workflow's total budget. No retries
are enabled. Normal fixture teardown removes the new room, agent and Compose
stack; the ephemeral CI runner remains the process-kill cleanup backstop.
