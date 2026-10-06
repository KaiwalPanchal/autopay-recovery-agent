"""agent.agent must derive the customer from the backend call row, never from participant metadata."""
import asyncio
import json
from types import SimpleNamespace

import pytest

import agent.agent as agent_mod


class FakeAgent:
    def __init__(self):
        self.said = []

    def start(self, room):
        pass

    async def say(self, text, allow_interruptions=True):
        self.said.append(text)


def make_ctx(call_id, participant_meta):
    async def connect():
        return None
    participant = SimpleNamespace(metadata=json.dumps(participant_meta))
    room = SimpleNamespace(name="room", remote_participants={"p": participant})
    return SimpleNamespace(connect=connect, room=room, job=SimpleNamespace(metadata=call_id))


def test_entrypoint_ignores_participant_metadata_customer_id(monkeypatch):
    fetched, built, fake = [], [], FakeAgent()
    monkeypatch.setattr(agent_mod, "fetch_call_context",
                        lambda call_id: fetched.append(call_id) or {"customer_name": "Maya Shah"})
    monkeypatch.setattr(agent_mod, "create_voice_pipeline_agent",
                        lambda call_id: built.append(call_id) or (fake, "prompt"))
    ctx = make_ctx("call_abc", {"customer_id": "cus_002", "customer_name": "Attacker Chosen"})
    asyncio.run(agent_mod.entrypoint(ctx))
    assert fetched == ["call_abc"] and built == ["call_abc"]
    assert "Maya Shah" in fake.said[0]
    assert "Attacker Chosen" not in fake.said[0] and "cus_002" not in fake.said[0]


def test_entrypoint_refuses_without_call_id_or_unknown_call(monkeypatch):
    built = []
    monkeypatch.setattr(agent_mod, "create_voice_pipeline_agent", lambda call_id: built.append(call_id))
    monkeypatch.setattr(agent_mod, "fetch_call_context", lambda call_id: None)
    asyncio.run(agent_mod.entrypoint(make_ctx("", {"customer_id": "cus_002"})))
    asyncio.run(agent_mod.entrypoint(make_ctx("call_missing", {"customer_id": "cus_002"})))
    assert built == []


def test_agent_module_has_no_direct_database_access():
    assert not hasattr(agent_mod, "db")


def test_tools_require_explicit_token(monkeypatch):
    from agent.tools import RecoveryAgentTools
    monkeypatch.delenv("INTERNAL_API_TOKEN", raising=False)
    with pytest.raises(RuntimeError):
        RecoveryAgentTools("call_x")
    assert RecoveryAgentTools("call_x", token="t").headers == {"Authorization": "Bearer t"}
