# Architecture & Implementation Decisions Log

## D-001: SQLite Database for Persistence
- **Date:** 2026-10-04
- **Context:** System requires persistent storage for customers, payments, calls, and append-only event logs.
- **Decision:** Use SQLite (file `data/app.db`) managed via SQLAlchemy 2.0 with single-writer WAL mode.
- **Alternatives:** In-memory JSON files (insufficient concurrency/querying); PostgreSQL (unnecessary operational overhead for local evaluation).
- **Consequences:** Zero-dependency local setup with standard SQL portability.

## D-002: Currency Representation in Integer Minor Units (Paise)
- **Date:** 2026-10-04
- **Context:** Financial amounts must never suffer IEEE 754 floating-point rounding errors or precision loss.
- **Decision:** All monetary values stored and processed as integer paise (`amount_minor`, e.g., ₹1,299 is stored as `129900`). Display formatting (`₹1,299`) is generated server-side.
- **Alternatives:** Floating-point floats/doubles (prone to rounding glitches); Decimal strings.
- **Consequences:** Clean mathematical operations and strict invariant adherence.

## D-003: Session-Bound Agent Tools (INV-2)
- **Date:** 2026-10-04
- **Context:** LLMs must not be trusted with customer identification or routing parameters.
- **Decision:** Every tool exposed to the agent takes zero customer ID parameters. The agent runtime injects `call_id` from the session context, and the backend derives the customer securely.
- **Alternatives:** LLM passing `customer_id` (violates INV-2, risks unauthorized cross-customer account modification).
- **Consequences:** Eliminates prompt injection vectors targeting customer identity.

## D-004: Server-Side Outcome Derivation (INV-5)
- **Date:** 2026-10-04
- **Context:** The final call outcome (RECOVERED, PAYMENT_LINK_SENT, etc.) represents legally binding business data.
- **Decision:** The LLM does not set the outcome. The backend derives the outcome deterministically upon `finalize` from recorded events and state machine history.
- **Alternatives:** Agent invoking `set_outcome(...)` (allows hallucinations and inaccurate reporting).
- **Consequences:** 100% deterministic and auditable call records.

## D-005: Browser Voice / WebSocket (WebRTC) First Strategy
- **Date:** 2026-10-04
- **Context:** Need to test voice interaction, conversational turns, interruptions, and tool calls rapidly without incurring telecom costs or debugging phone network anomalies simultaneously.
- **Decision:** Prioritize the WebSocket/WebRTC browser voice interface via LiveKit Agents first. Connect to SIP trunk once WebRTC loop is verified.
- **Alternatives:** Debugging SIP trunk and voice AI concurrently (multiplies failure modes).
- **Consequences:** Fast iterative testing and transparent debugging.

## D-006: Telephony & SIP Outbound Trunk Strategy
- **Date:** 2026-10-04
- **Context:** Final demo requires an outbound phone call to an authorized test number (`DEMO_PHONE_NUMBER`).
- **Decision:** Utilize LiveKit SIP Outbound Trunk connected to a SIP termination provider (e.g. Twilio Elastic SIP Trunking). Strict dial guard enforced at the API level (INV-9).
- **Alternatives:** Third-party telephony abstraction (Vapi/Retell - rejected in spec Section 4.1).
- **Consequences:** Adheres to applied AI engineering criteria with direct infrastructure control.
