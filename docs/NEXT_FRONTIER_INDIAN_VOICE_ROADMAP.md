# 🚀 Autopay Recovery Voice Agent: System Architecture & Frontier Roadmap

> **An exhaustive guide to the current production-grade implementation, verified capabilities, and the next-generation frontier for ultra-low latency, native Speech-to-Speech (S2S), and hyper-realistic human voice in Indian languages.**

---

## 📑 Table of Contents
1. [Executive Summary & Current Architecture](#1-executive-summary--current-architecture)
2. [What Works Right Now (The Verified Baseline)](#2-what-works-right-now-the-verified-baseline)
3. [Speech Recognition (STT): Faster-Whisper vs. Cloud Deepgram](#3-speech-recognition-stt-faster-whisper-vs-cloud-deepgram)
4. [Speech Output (TTS): Ultra-Fast Neural Streaming](#4-speech-output-tts-ultra-fast-neural-streaming)
5. [The Native Speech-to-Speech (S2S) Frontier: End-to-End Voice with Tools](#5-the-native-speech-to-speech-s2s-frontier-end-to-end-voice-with-tools)
6. [Achieving Hyper-Realistic Human Speech in Indian Languages](#6-achieving-hyper-realistic-human-speech-in-indian-languages)
7. [Implementation Blueprint & Recommendations](#7-implementation-blueprint--recommendations)

---

## 1. Executive Summary & Current Architecture

The **Autopay Recovery Voice Agent** is a full-stack, applied AI telephony system designed to resolve failed recurring subscription payments. Built on a **Dual-Boundary Architecture**, it strictly separates non-deterministic conversational intelligence (LLM) from deterministic financial ledger operations (FastAPI State Machine).

```
                      CUSTOMER (Browser WebRTC / Telephony)
                                      │
                                      ▼
                      LIVEKIT CLOUD SFU MEDIA SERVER
                                      │
                 ┌────────────────────┴────────────────────┐
                 │  Audio Track (RTP / WebRTC UDP)         │
                 ▼                                         ▼
   AGENT WORKER (Python dev)                     NEXT.JS OPERATOR DASHBOARD
   • Silero VAD (Silence / Barge-in)             • Real-time Stats & Polling (2s)
   • Speech-to-Text (STT)                        • Purified Customer Personas
   • Google Gemini 3.5 Flash Lite                • WebRTC Audio Modal
     (4-Key Round-Robin Rotation)                • State Machine Inspector
   • Tool Context Closures                       └─────────────┬───────────┘
   • Text-to-Speech (TTS)                                      │ HTTP / CORS
                 │                                             │
                 │ Internal Authenticated Tool Calls           │
                 ▼                                             ▼
                 └───────────────► FASTAPI BACKEND ◄───────────┘
                                   • /api/customers (operator token, CORS allow-list)
                                   • /api/calls (Session & Token JWTs)
                                   • /internal/calls/{id}/* (Guarded)
                                   • State Machine Core & Invariant Gates
                                   • SQLite / JSON Persona Store (Paise)
```

---

## 2. What Is Implemented Today (QUEST-004 audit, 2026-10-07)

This section replaces an earlier, more optimistic "verified baseline". Only things backed by code and a test or measured run are listed.

- **Backend (FastAPI + SQLite, money in paise):** operator API (`/api/*`, operator token), call-bound internal tool API (`/internal/calls/{id}/*`, internal token), guard order `CALL_LOCKED` -> `CALL_FINALIZED` -> `IDENTITY_NOT_VERIFIED` -> `NOT_RETRYABLE` -> `RETRY_LIMIT_REACHED`, server-side outcome derivation, backend-verified identity challenge (last 4 of the card on file, 3 attempts), post-hoc sensitive-data scan of transcript text sent to the backend.
- **Simulated everywhere it matters:** the payment processor is deterministic and fake; SIP dialing is not implemented (the endpoint answers 403/501); the dashboard has no LiveKit client, so there is no browser audio; nothing dispatches the agent worker to a room. The agent worker (`agent/agent.py`) is written against livekit-agents 1.x but has not been run end to end in this audit (it needs live keys).
- **Operator dashboard (Next.js):** polls every 2 s, shows customers/stats, creates call sessions. Sends `NEXT_PUBLIC_OPERATOR_TOKEN` (demo only: it is compiled into the browser bundle).
- **Not measured:** LLM latency, voice latency, request throughput. Earlier claims of "~100 ms TTFT", "sub-10 ms responses" and key-pool RPM figures were never measured here and have been removed.

### B. Verification (measured by running them)
- **pytest (`python -m pytest -q`):** 165 passed (see README for the breakdown).
- **Offline scenario/safety evals (`evals/run_evals.py`):** 16/16 scenarios, 12/12 sensitive-data patterns flagged. These are deterministic checks of the backend and a regex, not of an LLM.
- **Offline adversarial suite (`evals/run_offline_adversarial.py`):** 57/57 attacks blocked. No LLM involved.
- **Live Gemini adversarial evals (`evals/run_adversarial_evals.py`):** need `GEMINI_API_KEY`. The checked-in `evals/adversarial_eval_results.json` is from a prior manual run (2026-10-06, `gemini-3.5-flash-lite`, 12/12 scenarios passed) made BEFORE the identity challenge and auth changes; its tool wrappers re-implement the old free-form identity tool, so it must be updated before it is re-run. It was not re-run in this audit.

## 3. Speech Recognition (STT): Faster-Whisper vs. Cloud Deepgram

To reach sub-300ms conversational turn-taking, transcription latency must be minimized. There are two primary upgrade paths:

### Path A: Local `faster-whisper` (CTranslate2)
`faster-whisper` is a reimplementation of OpenAI's Whisper model using CTranslate2, a fast inference engine for Transformer models.

#### How It Works in LiveKit:
1. LiveKit captures incoming 20ms audio frames and feeds them to an embedded **Silero VAD**.
2. Once speech starts, audio buffers are streamed directly into an in-process `faster-whisper` instance running on local GPU/CPU.
3. Transcribed tokens are yielded in real-time as partial transcripts.

#### Performance & Trade-offs:
| Metric | Cloud Whisper (API) | `faster-whisper` (RTX 3080/4090) | `faster-whisper` (CPU) |
|---|---|---|---|
| **Latency** | ~300ms – 500ms | **~60ms – 100ms** | ~200ms – 350ms |
| **Network Overhead** | Cloud round-trip | **0ms (Local in-process)** | **0ms (Local in-process)** |
| **Cost** | $0.006 / minute | **$0.00 (Self-hosted)** | **$0.00 (Self-hosted)** |
| **Privacy / DPDP** | Audio leaves VPC | **100% on-premise** | **100% on-premise** |

#### Implementation in LiveKit Agents:
```python
# Custom LiveKit STT Plugin using Faster-Whisper
from faster_whisper import WhisperModel
from livekit.agents import stt

class FasterWhisperSTT(stt.STT):
    def __init__(self, model_size="base.en", device="cuda", compute_type="float16"):
        super().__init__(capabilities=stt.STTCapabilities(streaming=True))
        self.model = WhisperModel(model_size, device=device, compute_type=compute_type)

    async def _recognize_impl(self, buffer, *args, **kwargs):
        segments, _ = self.model.transcribe(buffer, beam_size=1)
        text = " ".join([segment.text for segment in segments])
        return stt.SpeechEvent(type=stt.SpeechEventType.FINAL_TRANSCRIPT, alternatives=[stt.SpeechData(text=text)])
```

---

## 4. Speech Output (TTS): Ultra-Fast Neural Streaming

Traditional TTS models wait for a full sentence or paragraph before synthesizing audio. Frontier streaming TTS models emit raw audio packets from the first 3–4 words:

| Provider | Engine | Time-To-First-Byte (TTFB) | Voice Quality / Emotion | Ideal Use Case |
|---|---|---|---|---|
| **Cartesia** | *Sonic* | **~90ms** | High naturalness, low robotic artifacts | Industry leader for low latency |
| **Deepgram** | *Aura* | **~120ms** | Crisp, conversational English | High-throughput commercial calls |
| **ElevenLabs** | *Turbo v2.5* | **~150ms** | Industry-best emotional expressiveness | Premium enterprise recovery |
| **OpenAI** | *tts-1* | ~250ms | Standard conversational | Reliable default fallback |

---

## 5. The Native Speech-to-Speech (S2S) Frontier: End-to-End Voice with Tools

### Does End-to-End Voice Support Tool Usage?
**YES! 100% natively.**

In modern Native Speech-to-Speech (S2S) architectures (such as **Gemini 2.0 / 3.1 Flash Multimodal Live API** and **OpenAI GPT-4o Realtime API**), audio is not converted to text first. The neural network processes raw audio tokens directly and generates raw audio tokens as output.

### How Tool Execution Works in Native Audio Streams:

```
[ Customer Speaks: "Go ahead and retry my card on file" ]
                           │
                           ▼ (Bidirectional WebRTC / WebSocket Audio)
      ┌────────────────────────────────────────────────────────┐
      │         GEMINI 2.0 / 3.1 MULTIMODAL LIVE API           │
      │                                                        │
      │ 1. Hears raw audio waveform directly                   │
      │ 2. Detects intent: customer requests card retry        │
      │ 3. PAUSES audio stream generation                      │
      │ 4. EMITS tool_call event over WebSocket protocol:      │
      │    {                                                   │
      │      "name": "retry_payment",                          │
      │      "args": {}                                        │
      │    }                                                   │
      └──────────────────────────┬─────────────────────────────┘
                                 │
                                 ▼
                     LIVEKIT AGENT PYTHON WORKER
                                 │
                                 │ POST /internal/calls/{cid}/retry
                                 ▼
                          FASTAPI BACKEND
                     (Executes simulated charge)
                                 │
                                 │ Returns: {"ok": true, "status": "success"}
                                 ▼
                     LIVEKIT AGENT PYTHON WORKER
                                 │
                                 │ Sends tool_response back to Gemini WebSocket
                                 ▼
      ┌────────────────────────────────────────────────────────┐
      │         GEMINI 2.0 / 3.1 MULTIMODAL LIVE API           │
      │                                                        │
      │ 5. Ingests tool result JSON                            │
      │ 6. Immediately resumes generating audio stream:        │
      │    "Great news Maya, your payment of ₹1,299 went       │
      │     through successfully! Your account is active."     │
      └──────────────────────────┬─────────────────────────────┘
                                 │
                                 ▼ (Direct Audio Packets)
                 [ Customer Hears Voice in ~280ms ]
```

### Why Native S2S is Superior to Cascaded Pipelines:
1. **Latency Collapse:** Eliminates STT (~100ms) and TTS (~100ms). Total response latency drops to **~250ms – 300ms** (matches human conversational response time).
2. **Emotional & Prosodic Understanding:** S2S hears *how* the customer speaks (hesitation, anger, distress, urgency) and adapts its tone accordingly.
3. **Natural Interruption:** The model stops speaking the millisecond it hears user audio tokens without relying on external VAD heuristics.

---

## 6. Achieving Hyper-Realistic Human Speech in Indian Languages

Voice recovery in India requires distinct localized nuance. A sterile English or formal textbook Hindi agent fails in the Indian market.

### A. The Linguistic Reality: Code-Switching (Hinglish)
Real Indian customer service conversations are predominantly **Hinglish** (fluid mixing of Hindi and English vocabulary):

- ❌ **Formal Hindi (Unnatural):** *"नमस्ते माया जी, आपका अपैक्स क्लाउड के लिए बारह सौ निन्यानवे रुपये का स्वतः भुगतान अपर्याप्त धनराशि के कारण विफल हो गया है।"* (Too archaic, sounds like a government broadcast).
- ❌ **Pure English (Impersonal):** *"Hello Maya, your recurring autopay of 1,299 rupees has failed due to insufficient funds."*
- 🟢 **Natural Hinglish (High Recovery Rate):**
  > *"Haanji Maya ji, namaste. Main Apex Cloud se bol raha hoon aapke account ke regarding. Aapka ₹1,299 ka autopay payment decline ho gaya tha insufficient balance ki wajah se. Kya hum abhi card retry karein, ya aapko payment link WhatsApp kar dein?"*

### B. Dedicated Indian Speech Engines

| Technology | Provider / Model | Strengths | Strategic Fit |
|---|---|---|---|
| **Sarvam AI** | **Bulbul (TTS) & Saarathi (STT)** | Built in India for 10+ Indian languages (Hindi, Tamil, Telugu, Marathi, Gujarati, Kannada, Bengali). Accurately pronounces Indian names, Rupee amounts, and colloquial cadences. | **#1 Pick for Indian Voice** |
| **Bhashini / AI4Bharat** | **IndicWav2Vec & IndicTTS** | Open-source state-of-the-art models developed by IIT Madras & MeitY. Full data sovereignty, zero per-minute licensing costs. | **#1 Pick for On-Premise / DPDP Compliance** |
| **Cartesia** | **Sonic Indic Voices** | Ultra-low 90ms latency with Indian English and Hindi accents. | Best for sub-300ms English/Hinglish calls |
| **ElevenLabs** | **Multilingual v2 (Indian Voices)** | Deep emotional resonance, natural conversational breathing and laughter. | Best for high-ticket B2B subscription recovery |

### C. The 5 Keys to Human-Like Indian Voice Realism
1. **Conversational Fillers & Affirmations (Backchanneling):**
   - Inject subtle conversational markers: *"Haanji"*, *"Achha"*, *"Theek hai"*, *"Sure, ek second"*.
2. **Indian Number & Currency Formatting:**
   - Always pronounce currency in Indian format: *"Bara sau ninyanve rupaye"* or *"One thousand two hundred ninety-nine rupees"*, never *"Twelve ninety-nine dollars"*.
3. **Respectful Indian Honorifics:**
   - Always append respectful honorifics (*"-ji"* e.g., *"Maya ji"*, *"Rahul ji"*). It significantly reduces defensive customer reactions.
4. **Acoustic Noise Robustness:**
   - In India, calls often take place in loud ambient environments (traffic, commuter rail, ceiling fans). Integrate **Krisp Audio** or **DeepFilterNet** at the WebRTC ingestion layer to strip background noise before STT.
5. **Dynamic Language Switching (Auto-Detect):**
   - If customer answers in Hindi (*"Kaun bol raha hai?"*), agent seamlessly shifts to Hindi. If customer speaks English (*"Yes, who is this?"*), agent speaks Indian English.

---

## 7. Implementation Blueprint & Recommendations

### Recommended Next Milestone Architecture:

```
[ Tier 1: Zero Cloud Cost & Ultra Low Latency ]
Local WebRTC Audio ──► Silero VAD ──► Faster-Whisper (CUDA) ──► Gemini 3.5 Flash Lite ──► Cartesia Sonic / Sarvam Bulbul

[ Tier 2: The Ultimate Conversational Frontier ]
Local WebRTC Audio ──────────────► Gemini Multimodal Live API (Direct Audio S2S) ──────────────► Customer Earpiece
                                  (Native Tool Calling + Hinglish Prosody)
```

### Action Items for Phase 3:
1. **Add `livekit-plugins-sarvam` / Sarvam API Integration:** Enable Indian regional language TTS (Bulbul) and STT (Saarathi) for authentic Hinglish payment recovery.
2. **Implement Native Multimodal Live S2S Mode:** Add a toggle in `agent/agent.py` enabling `livekit.plugins.google.realtime.RealtimeModel` for zero-STT/TTS direct audio streaming with our existing 6 tools.
3. **Deploy Local `faster-whisper` Sidecar:** Provide an on-premise transcription option using CTranslate2 for zero-cloud latency and full Indian DPDP Act compliance.
