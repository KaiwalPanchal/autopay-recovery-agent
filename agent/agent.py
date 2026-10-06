"""LiveKit Voice Agent Worker for Autopay Recovery.

Coordinates real-time STT -> LLM (with deterministic function tools) -> TTS pipeline.
"""

import asyncio
import os
import logging
from typing import Optional
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("autopay-recovery-agent")

from agent.prompts import get_system_prompt
from agent.tools import RecoveryAgentTools, create_livekit_function_context
import itertools

_gemini_key_cycle = None

def get_next_gemini_key() -> Optional[str]:
    """Rotates through comma-separated GEMINI_API_KEYS or single GEMINI_API_KEY/GOOGLE_API_KEY."""
    global _gemini_key_cycle
    keys_raw = os.getenv("GEMINI_API_KEYS", "")
    keys = [k.strip() for k in keys_raw.split(",") if k.strip()]
    if not keys:
        single = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
        if single:
            keys = [single.strip()]
    if not keys:
        return None
    if _gemini_key_cycle is None:
        _gemini_key_cycle = itertools.cycle(keys)
    return next(_gemini_key_cycle)


def fetch_call_context(call_id: str):
    """Ask the backend (not the local DB, not the room) who this call is for. None if unknown."""
    try:
        resp = RecoveryAgentTools(call_id).context()
    except RuntimeError:
        raise
    except Exception as e:
        logger.error(f"Could not reach backend for call context: {e}")
        return None
    return resp.get("data") if resp.get("ok") else None


def attach_transcript_hook(session, call_id: str):
    """Forward each finalized utterance to the backend, which runs the sensitive-data scan.

    Best effort and detection-only: a failure here never interrupts the call. Written against
    livekit-agents 1.x ``conversation_item_added``; not exercised by the automated tests.
    """
    tools = RecoveryAgentTools(call_id)

    def on_item(ev):
        try:
            role = getattr(ev.item, "role", None)
            text = getattr(ev.item, "text_content", None)
            if role not in ("user", "assistant") or not text:
                return
            speaker = "customer" if role == "user" else "agent"
            asyncio.get_running_loop().create_task(asyncio.to_thread(tools.record_transcript, speaker, text))
        except Exception as e:  # never break the call
            logger.warning(f"transcript hook error: {e}")

    session.on("conversation_item_added", on_item)


def create_voice_pipeline_agent(call_id: str):
    """Instantiates a configured LiveKit voice agent with safety constraints."""
    system_instruction = get_system_prompt()
    fnc_ctx = create_livekit_function_context(call_id)

    try:
        from livekit.plugins import openai
        stt_provider = openai.STT()
        gemini_key = get_next_gemini_key()
        if gemini_key:
            try:
                from livekit.plugins import google
                gemini_model = os.getenv("LLM_MODEL", "gemini-3.5-flash-lite")
                llm_provider = google.LLM(
                    model=gemini_model,
                    api_key=gemini_key,
                    temperature=0.2,
                )
                logger.info(f"Initialized Google Gemini LLM provider: {gemini_model} (key ending in ...{gemini_key[-6:]})")
            except Exception as e:
                logger.warning(f"Could not load Google Gemini LLM ({e}), falling back to OpenAI")
                llm_provider = openai.LLM(
                    model="gpt-4o-mini",
                    temperature=0.2,
                )
        else:
            llm_provider = openai.LLM(
                model=os.getenv("LLM_MODEL", "gpt-4o-mini"),
                temperature=0.2,
            )
        tts_provider = openai.TTS()

        try:
            from livekit.plugins import deepgram
            if os.getenv("DEEPGRAM_API_KEY"):
                stt_provider = deepgram.STT()
        except ImportError:
            pass

        try:
            from livekit.plugins import cartesia
            if os.getenv("CARTESIA_API_KEY"):
                tts_provider = cartesia.TTS()
        except ImportError:
            pass

        try:
            from livekit.agents import voice
            agent = voice.Agent(instructions=system_instruction, tools=fnc_ctx)
            session = voice.AgentSession(
                llm=llm_provider,
                stt=stt_provider,
                tts=tts_provider,
            )
            return (session, agent), system_instruction
        except (ImportError, AttributeError):
            from livekit.agents.pipeline import VoicePipelineAgent
            agent = VoicePipelineAgent(
                vad=None,
                stt=stt_provider,
                llm=llm_provider,
                tts=tts_provider,
                fnc_ctx=fnc_ctx,
            )
            return agent, system_instruction
    except Exception as e:
        logger.warning(f"LiveKit Voice agent initialization error: {e}")
        return None, system_instruction


async def entrypoint(ctx):
    """LiveKit Agents Job Entrypoint."""
    logger.info(f"Connecting to room: {ctx.room.name}")
    await ctx.connect()

    # The call id comes from the dispatch job metadata (server side). Participant metadata is
    # client-controlled and is deliberately NOT used to pick the customer.
    call_id = getattr(getattr(ctx, "job", None), "metadata", "")
    if not call_id:
        logger.error("LiveKit dispatch metadata must contain call_id.")
        return
    call_ctx = fetch_call_context(call_id)
    if not call_ctx:
        logger.error(f"Backend does not know call {call_id}; refusing to start.")
        return
    customer_name = call_ctx.get("customer_name") or "the account holder"
    logger.info(f"Initiating recovery voice session for call: {call_id}")

    agent_obj, system_instruction = create_voice_pipeline_agent(call_id)
    if not agent_obj:
        logger.error("Could not construct Voice agent. Check API keys.")
        return

    # Initial identity verification greeting (no amount, failure reason, status, or payment link before verification)
    greeting = f"Hi, is this {customer_name}? I'm an automated assistant calling on behalf of Apex Cloud regarding your account. Do I have a moment to verify your identity before we continue?"

    if isinstance(agent_obj, tuple):
        session, agent = agent_obj
        attach_transcript_hook(session, call_id)
        await session.start(agent, room=ctx.room)
        await session.say(greeting, allow_interruptions=True)
    else:
        agent_obj.start(ctx.room)
        await agent_obj.say(greeting, allow_interruptions=True)


if __name__ == "__main__":
    try:
        from livekit.agents import cli, WorkerOptions
        cli.run_app(WorkerOptions(entrypoint_fnc=entrypoint))
    except Exception as e:
        logger.info(f"To run with livekit worker: python -m agent.agent dev (Requires livekit-agents package: {e})")
