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

## D-007: Two bearer tokens, fail closed (QUEST-004)
- **Date:** 2026-10-07
- **Context:** `/api/*` (including the data-wiping `POST /api/customers/reset`) was unauthenticated, CORS was `*`, and the internal token defaulted to a well-known string.
- **Decision:** Separate `OPERATOR_API_TOKEN` (all `/api/*` except `/api/health`) and `INTERNAL_API_TOKEN` (`/internal/*`), compared with `hmac.compare_digest`. No built-in default: an unset token rejects everything. `ENVIRONMENT=dev|test` is the only, explicit, opt-in fallback. CORS is an allow-list from `CORS_ALLOWED_ORIGINS`, never `*`, no credentials.
- **Consequences:** The dashboard needs `NEXT_PUBLIC_OPERATOR_TOKEN`, which is visible in the browser bundle. That is acceptable for a local demo only; a real deployment needs a login or server-side proxy.

## D-008: Identity is verified by the backend (QUEST-004)
- **Date:** 2026-10-07
- **Context:** The LLM used to assert `result="verified"`, so a prompt-injected model could unlock payment tools.
- **Decision:** The agent forwards the customer's answer (last 4 digits of the card on file) to `POST /internal/calls/{id}/identity`; the backend compares it with seed data, allows 3 attempts (atomic counter), then locks the call. `wrong_person` locks immediately. Locks are one-way.
- **Alternatives:** DOB (not in the seed data); OTP to the phone on file (needs SMS, not built).
- **Consequences:** Last-4 is a weak factor (it is printed on receipts and visible to operators). It demonstrates the control point; it is not production-grade authentication.

## D-009: The agent never opens the database or trusts room metadata (QUEST-004)
- **Date:** 2026-10-07
- **Decision:** The worker takes `call_id` from LiveKit job metadata (set by whoever dispatches), asks the backend `GET /internal/calls/{id}` who the call is for, and ignores participant metadata. Supersedes the old `customer_id`-from-participant-metadata behavior. The agent container no longer contains a database.

## D-010: Transcript scanning is a backend endpoint (QUEST-004)
- **Date:** 2026-10-07
- **Decision:** `POST /internal/calls/{id}/transcript` runs `scan_transcript` (regex, detection only, raw text never stored) and `finalize` reports `sensitive_data_flagged`. The agent worker forwards utterances best-effort; that hook is untested against a live LiveKit session.

## D-011: SIP dialing is not implemented
- **Date:** 2026-10-07
- **Decision:** Supersedes the plan in D-006 for now. `mode=sip` returns 403 without a trunk id and 501 with one, rather than pretending a call was placed.
