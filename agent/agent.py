"""LiveKit Voice Agent Worker for Autopay Recovery.

Coordinates real-time STT -> LLM (with deterministic function tools) -> TTS pipeline.
"""

import os
import json
import logging
from typing import Optional
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("autopay-recovery-agent")

LIVEKIT_URL = os.getenv("LIVEKIT_URL", "wss://recovery-demo.livekit.cloud")
LIVEKIT_API_KEY = os.getenv("LIVEKIT_API_KEY", "")
LIVEKIT_API_SECRET = os.getenv("LIVEKIT_API_SECRET", "")

from agent.prompts import get_system_prompt
from agent.tools import RecoveryAgentTools, create_livekit_function_context
from agent.state import AgentCallState
from backend.database import db
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


def create_voice_pipeline_agent(call_id: str, customer_id: str = "cus_001"):
    """Instantiates a configured LiveKit VoicePipelineAgent with safety constraints."""
    customer = db.get_customer(customer_id) or db.get_customer("cus_001")
    customer_dict = customer.model_dump() if customer else {"name": "Maya Shah", "customer_id": "cus_001", "amount": 1299}

    system_instruction = get_system_prompt(customer_dict)
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

    # Extract customer_id from room name or participant metadata
    customer_id = "cus_001"
    for p in ctx.room.remote_participants.values():
        if p.metadata:
            try:
                meta = json.loads(p.metadata)
                if "customer_id" in meta:
                    customer_id = meta["customer_id"]
                    break
            except Exception:
                pass

    logger.info(f"Initiating recovery voice session for customer: {customer_id}")
    customer = db.get_customer(customer_id)
    customer_name = customer.name if customer else "Maya"
    amount = customer.amount if customer else 1299
    currency = "₹" if (customer and customer.currency == "INR") else "$"

    call_id = getattr(getattr(ctx, "job", None), "metadata", "")
    if not call_id:
        logger.error("LiveKit dispatch metadata must contain call_id.")
        return
    agent_obj, system_instruction = create_voice_pipeline_agent(call_id, customer_id)
    if not agent_obj:
        logger.error("Could not construct Voice agent. Check API keys.")
        return

    # Initial identity verification greeting (no amount, failure reason, status, or payment link before verification)
    greeting = f"Hi, is this {customer_name}? I'm an automated assistant calling on behalf of Apex Cloud regarding your account. Do I have a moment to verify your identity before we continue?"

    if isinstance(agent_obj, tuple):
        session, agent = agent_obj
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
