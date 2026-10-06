# Threat model

Scope: what is in this repository as of QUEST-004 (2026-10-07). Every mitigation below names the code that implements it and the test that exercises it. Anything not listed there is not implemented. The payment processor is a deterministic simulator, so "money" below means simulated state, not real funds.

## 1. Assets

| Asset | Where | Why it matters |
|---|---|---|
| Customer records (name, phone, amount due, card last 4) | SQLite `customers` | PII; the card last 4 is also the identity challenge answer |
| Payment state (recovered, link sent, scheduled, retry count) | SQLite `customers`, `payments` | In a real system this would move money |
| Call records and event log | SQLite `calls`, `call_events` | Audit trail of what the agent was allowed to do |
| Operator token, internal token | environment | Whoever holds them can use the matching API |
| Provider keys (LiveKit, OpenAI, Gemini, ...) | `.env` (gitignored) | Spend and account access. They are only needed by the voice worker and live evals |
| The call's trust decisions (verified, locked) | `calls.identity_verified`, `calls.locked` | The only thing standing between a talker and payment tools |

## 2. Actors and trust boundaries

```
 Customer (voice, untrusted) --> STT/LLM/TTS providers --> Agent worker --HTTP, internal token--> Backend /internal/*
 Operator browser (semi-trusted) ----------HTTP, operator token----------------------------------> Backend /api/*
                                                                                                    |
                                                                                                    v
                                                                                                 SQLite
```

1. **Customer to LLM.** Untrusted speech reaches a model. Treat the model's choices as attacker-influenced.
2. **LLM/agent to backend.** The backend must not believe the agent. It only accepts call-bound requests with the internal token and re-derives everything (customer, guards, outcome) from its own database.
3. **Operator browser to backend.** Anyone who can reach port 8000 is untrusted until they present the operator token.
4. **Backend to disk.** Single SQLite file; whoever can read it owns all data.

## 3. Attacker capabilities considered

- **A1, malicious or confused caller:** controls what the LLM hears; can try prompt injection, impersonation, repeated guessing, abusive or wrong-person calls, reading card data aloud.
- **A2, compromised or prompt-injected agent:** can call any tool the agent is given, with arbitrary argument values, but does not hold the operator token and cannot choose the customer or the call.
- **A3, unauthenticated network client:** can send any HTTP request to the backend and any browser origin can try cross-origin requests.
- **A4, someone holding only one of the two tokens:** tries to use it on the other API.
- **A5, repository reader:** reads the code, git history and the docs.

Out of scope: attacker with host/disk access, supply-chain compromise of dependencies, a malicious operator who legitimately holds the operator token, denial of service.

## 4. Implemented mitigations

| Threat | Mitigation | Code | Tests |
|---|---|---|---|
| A3 reads or wipes data via `/api/*`, including `POST /api/customers/reset` | Operator bearer token on every `/api/*` route except `/api/health` (which returns only `{"status":"healthy"}`) | `backend/security.py`, router dependency in `backend/main.py` | `tests/test_security.py`, ADV-01..04, 12 |
| Guessable or default credentials | No default tokens; unset or empty token rejects everything; the only fallback is explicit `ENVIRONMENT=dev` or `test` | `security.configured_token` | `test_fail_closed_when_tokens_unset`, `test_explicit_test_environment_override`, ADV-11, 13, 14 |
| Timing attacks on token compare | `hmac.compare_digest` on bytes | `security.token_matches` | `test_token_compare_is_constant_time` (checks the call is used, not timing itself) |
| A4 uses one token on the other API | Two separate tokens | `require_operator`, `require_internal` | `test_operator_routes_reject_wrong_and_internal_token`, ADV-04, 05 |
| Cross-origin abuse from a browser | CORS allow-list from `CORS_ALLOWED_ORIGINS`; wildcard dropped; credentials disabled; methods and headers narrowed | `parse_cors_origins`, middleware in `main.py` | `test_cors_*`, ADV-15 |
| A1/A2 claims an identity the backend never checked | The backend compares the answer (last 4 of card) with seed data; free-form `verified` is rejected with 422 | `RecoveryStateMachine.verify_identity`, `IdentityRequest` | `tests/test_identity.py`, ADV-16..25 |
| A1 brute-forces the 4-digit answer | At most 3 comparisons per call, counted by an atomic SQL increment before comparing, then the call locks | `Database.claim_identity_attempt` | `test_retry_limit_locks_call_even_for_correct_answer`, ADV-19, 20 |
| A2 unlocks a locked call | Locks are one-way: wrong person, cancel, decline and identity lock-out are only ever set to true | `record_intent`, `mark_wrong_person`, `identity` route | `test_wrong_person_lock_cannot_be_undone_by_correct_answer`, ADV-22, 50, 51 |
| A2 acts after cancel/decline, before identity, or after hang-up | Guard order `CALL_LOCKED` -> `CALL_FINALIZED` -> `IDENTITY_NOT_VERIFIED` -> `NOT_RETRYABLE` -> `RETRY_LIMIT_REACHED` | `RecoveryStateMachine.guard` | `tests/test_recovery_unit.py`, ADV-40..53 |
| A2 targets another customer | Tools carry no customer id. The customer is looked up from the call row; the agent worker learns the customer from the backend and ignores participant metadata | `main.py` routes, `agent/agent.py`, `agent/tools.py` | `tests/test_agent_entrypoint.py`, ADV-45 |
| A2 repeats charges | Retry is idempotent once recovered and capped at 2 attempts per customer | `payments.retry_payment`, `guard` | `test_retry_is_call_bound_and_idempotent`, ADV-41..44 |
| A2/A1 injection through tool arguments | Strict schemas: intent and identity result are enums, answer is 4 digits, `scheduled_time` is an ISO datetime that must be in the future and within 90 days, lengths capped, unknown fields rejected. All DB access is through SQLAlchemy bound parameters | `backend/models.py` | `tests/test_security.py`, ADV-23..39 |
| LLM invents the outcome | Outcome is derived by the backend from recorded events (`finalize`); the customer record is updated from that outcome | `RecoveryStateMachine.finalize` | `test_finalize_decision_table`, `test_finalize_syncs_customer_status` |
| Card data spoken on a call | Detection only: transcript text sent to `/internal/calls/{id}/transcript` is regex-scanned; a flag event is stored without the text; `finalize` reports `sensitive_data_flagged` | `backend/events.py`, `main.py` | `tests/test_transcript.py`, `run_evals.py` (12/12 patterns), ADV-54, 55 |
| Outbound dialing abuse | No dialing code exists. `mode=sip` returns 403 (no trunk) or 501 | `create_call` | `test_sip_*`, ADV-57 |
| A5 finds secrets in the repo | `.env` is gitignored, `.env.example` holds blanks, hardcoded LiveKit host and default tokens removed, `scripts/check_livekit.py` no longer prints the key. The repository has no commits yet, so there is no history to leak | `.gitignore` | manual review |
| Tests destroy real data | Tests and offline evals run on a temp SQLite file (`AUTOPAY_DB_PATH`) | `tests/conftest.py`, `evals/_env.py` | `test_tests_use_isolated_database` |

## 5. Residual risks (not mitigated)

1. **The LLM can still say anything.** Tools gate actions, not words. There is no output filter, so the model could speak a wrong amount from its own context, disclose something it was told in the prompt, or ignore the "AI disclosure" instruction. The only defences are the prompt and the fact that real facts come from tools. The live Gemini eval measured this once, before the current identity design; it was not re-run.
2. **Last-4 of a card is a weak factor.** Anyone with a receipt or a statement knows it. DOB, an OTP to the phone on file, or a signed link would be stronger.
3. **Attempt limits are per call, not per customer.** A holder of both tokens can open many calls and keep guessing. Retry limits are per customer; identity limits are not.
4. **The dashboard token is public.** `NEXT_PUBLIC_OPERATOR_TOKEN` is compiled into the browser bundle. Anyone who can load the dashboard can read it. A real deployment needs user login or a server-side proxy. There are no per-operator identities, no roles and no audit of who pressed reset.
5. **Sensitive-data scanning is after the fact and heuristic.** By the time text reaches the backend it has already passed through the speech and LLM providers. The regex will have false positives (long digit strings) and false negatives (digits spoken as words).
6. **No rate limiting, no lockout on bad tokens, no request size limit at the server level** (only field limits). Brute-forcing a strong token is impractical, but the API is easy to flood.
7. **No TLS, no secret manager.** Tokens travel in cleartext unless you terminate TLS in front. Tokens are never rotated by the code.
8. **The event log is append-only by convention** (the Python API has no update/delete), not by database permission. Anyone with the SQLite file can edit it, and `POST /api/customers/reset` deletes call and event history by design.
9. **Voice path unproven.** The worker, the transcript hook and the room-to-call binding have not been exercised against a live LiveKit session. Nothing dispatches the worker. A deployer who wires dispatch must set `job.metadata` to a call id created by the backend.
10. **Compliance is a design target, not a property.** See README. No calling-hours control, consent or do-not-call check, recording disclosure, retention policy, data-subject-rights handling or encryption at rest exists.
11. **Dependency and image security** (CVE scanning, base-image pinning, SBOM) is not done.

## 6. How to re-verify

```
python -m pytest -q
python evals/run_evals.py
python evals/run_offline_adversarial.py
```

The adversarial suite was written by the author of the guards, so its block rate shows protection against known attack shapes and regression safety, not an independent audit.
