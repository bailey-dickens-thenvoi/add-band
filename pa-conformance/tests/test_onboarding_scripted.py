"""Verbatim OpenClaw bootstrap with a strict, scripted model boundary."""

from __future__ import annotations

import pytest
from conftest import BootstrapFactory
from driver.chat import OwnerChat
from driver.exchange import liveness_name
from driver.sdk import CaptureFactory, ResourceManager, UserOps
from pa_settings import ModelMode, pa_settings

pytestmark = pytest.mark.integration


@pytest.mark.harness_skip(
    "hermes", reason="published bootstrap needs a headless skill runner"
)
@pytest.mark.harness_skip(
    "nanoclaw", reason="published bootstrap needs a headless skill runner"
)
async def test_published_bootstrap_scripted(
    pa_name: str,
    bootstrap_session: BootstrapFactory,
    resources: ResourceManager,
    user_ops: UserOps,
    capture: CaptureFactory,
    run_id: str,
) -> None:
    settings = pa_settings()
    assert settings.pa_standin and settings.pa_model_mode is ModelMode.STRICT
    onboarded = await bootstrap_session(pa_name)
    assert onboarded.model is not None, "Strict bootstrap requires a model stand-in"
    agent = onboarded.agent
    token = liveness_name(run_id)
    room_id = await resources.provision_room(
        title=f"pa-scripted-onboard-{pa_name}",
        participants=[agent.id],
    )
    try:
        async with capture(room_id) as room:
            chat = OwnerChat(
                agent=agent,
                room=room,
                user_ops=user_ops,
                standin=onboarded.model,
            )
            observed = await chat.ask_scripted(token=token)
        assert observed.served == "scripted" and observed.upstream_status is None
        calls = await onboarded.model.calls()
        assert calls and all(call.served != "passthrough" for call in calls)
    finally:
        await user_ops.delete_room(room_id)
