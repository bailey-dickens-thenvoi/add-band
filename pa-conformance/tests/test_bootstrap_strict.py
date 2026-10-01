"""Strict bootstrap configuration and cleanup checks without live services."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from conftest import _llm_env, _teardown_bootstrap
from harness.contract import HarnessContext
from harness.openclaw import OpenClawHarness
from pa_settings import ModelMode

pytestmark = pytest.mark.hermetic


def test_strict_credentials_cannot_forward_real_provider_keys(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "conftest.pa_settings", lambda: SimpleNamespace(pa_model_mode=ModelMode.STRICT)
    )
    supplied = SimpleNamespace(
        llm_credentials=SimpleNamespace(
            anthropic_api_key="real-key-must-not-escape",
            openai_api_key="other-real-key",
        )
    )
    assert _llm_env(supplied) == {
        "ANTHROPIC_API_KEY": "pa-strict-dummy-not-a-provider-key"
    }


def test_model_routing_precedes_verbatim_bootstrap(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    harness = OpenClawHarness(
        HarnessContext(
            run_id="offline",
            band_base_url="http://host.docker.internal:4000",
            band_ws_url="ws://host.docker.internal:4000/api/v1/socket/websocket",
            work_root=tmp_path,
        )
    )
    events = []
    monkeypatch.setattr(harness, "_cli_offline", MagicMock())
    monkeypatch.setattr(
        harness, "_route_model_through_standin", lambda: events.append("route")
    )
    monkeypatch.setattr(harness, "up_standin", lambda: events.append("standin"))
    monkeypatch.setattr("harness.openclaw.wait_for", MagicMock())
    harness.stack = MagicMock()
    harness.stack.run.side_effect = lambda *args, **kwargs: (
        events.append("bootstrap")
        or SimpleNamespace(stdout="Registered agent minted-id.")
    )
    assert (
        harness.onboard_via_bootstrap(user_api_key="fake", agent_name="smoke")
        == "minted-id"
    )
    assert events == ["route", "standin", "bootstrap"]
    invocation = harness.stack.run.call_args
    assert (
        invocation.args[2]
        == (Path(__file__).resolve().parents[2] / "openclaw/bootstrap.sh").read_text()
    )
    assert (
        invocation.kwargs["env"]["BAND_BASE_URL"] == "http://host.docker.internal:4000"
    )


async def test_strict_teardown_fails_after_attempting_all_resources() -> None:
    events = []

    class Resources:
        async def reap_agent(self, agent_id: str) -> None:
            events.append(agent_id)
            raise RuntimeError("fake cleanup failure")

    class Harness:
        name = "test"

        def down(self) -> None:
            events.append("stack")

    with pytest.raises(RuntimeError, match="Bootstrap cleanup failed"):
        await _teardown_bootstrap([Harness()], ["agent"], Resources(), strict=True)
    assert events == ["agent", "stack"]
