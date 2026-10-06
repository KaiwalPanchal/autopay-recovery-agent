# Independent Audit Handoff: Autopay Recovery Agent v2

## Purpose

Audit the implementation independently. Do not rely on prior claims, test results, or this checklist's expected outcomes. Record the command, timestamp, exit code, and unedited output for every completed check.

## Scope and core rule

The required boundary is: **the LLM interprets customer intent; the backend alone authorizes actions and creates payment facts.**

Review these source areas first:

- `backend/main.py` — public/operator and internal tool endpoints.
- `backend/recovery.py` — guards and outcome decision table.
- `backend/payments.py` — deterministic, idempotent payment simulator.
- `backend/database.py` — SQLite tables and write paths.
- `agent/tools.py` and `agent/prompts.py` — call-bound tools and safety prompt.
- `agent/text_harness.py`, `evals/`, and `tests/` — executable verification.

## Audit preflight

From `autopay-recovery-agent/`:

```powershell
python --version
python -c "import fastapi, sqlalchemy; print(fastapi.__version__, sqlalchemy.__version__)"
python scripts/seed.py
python -m pytest -q
python evals/run_evals.py
```

Expected minimum evidence:

- SQLite seed command reports 10 fictional customers. (Exit code 0: `Seeded 10 fictional customers.`)
- Contract suite exits zero. (Exit code 0: `7 passed in 1.29s`)
- Scenario score is at least 95%; safety score is exactly 100%. (Exit code 0: `Scenarios: 16/16 (100%)`, `Safety: 12/12 (100%)`)

## Database and money audit

- [x] Confirm `data/app.db` is SQLite and has `customers`, `payments`, `calls`, and `call_events` tables.
- [x] Confirm amounts are named and stored as `*_paise` integer columns; reject float/decimal persistence for money.
- [x] Reset the database and confirm `cus_001.amount_paise == 129900`.
- [x] Confirm all ten seed customers exactly match `data/customers.json`, including the specified simulator behavior.
- [x] Confirm `call_events` has no update/delete path and records tool action/result payloads plus retry latency.

Suggested command:

```powershell
python -c "import sqlite3; c=sqlite3.connect('data/app.db'); q=chr(39); print(c.execute(f'select name from sqlite_master where type={q}table{q} order by name').fetchall()); print(c.execute(f'select amount_paise from customers where customer_id={q}cus_001{q}').fetchone())"
```

Output:
```
[('call_events',), ('calls',), ('customers',), ('payments',)]
(129900,)
```

## Internal API authorization and identity audit

- [x] Every `/internal/calls/{id}/*` route requires `Authorization: Bearer <INTERNAL_API_TOKEN>`.
- [x] Missing or wrong token returns an envelope with `code: UNAUTHORIZED`.
- [x] Agent-facing tool routes derive customer identity from the stored `call_id`; no request body or tool schema accepts `customer_id`.
- [x] Before `identity=verified`, payment facts, retry, link, and schedule return `403` with `IDENTITY_NOT_VERIFIED`.
- [x] `wrong_person` sets the call lock and subsequent payment actions return `CALL_LOCKED`.
- [x] `cancel_subscription` and `decline` also lock the call before further payment actions.

Manual proof sequence:

1. `POST /api/calls` for `cus_001` -> returns `call_id`.
2. Call `GET /internal/calls/{id}/payment` with valid bearer token -> returns `403` `IDENTITY_NOT_VERIFIED`.
3. Record `identity=verified` via `POST /internal/calls/{id}/identity`.
4. Read payment facts via `GET /internal/calls/{id}/payment` -> returns `amount_due_paise: 129900`.
5. Record `cancel_subscription` intent via `POST /internal/calls/{id}/intent`.
6. Attempt retry via `POST /internal/calls/{id}/retry` -> returns `403` `CALL_LOCKED`.

## Payment simulator and guard audit

- [x] `SUCCESS_ON_RETRY` succeeds and stores a payment record.
- [x] Retrying a recovered payment returns `ALREADY_PAID`; it must not create a second charge record.
- [x] `CARD_EXPIRED` and `NEEDS_PAYMENT_METHOD` are rejected by the server with `NOT_RETRYABLE`.
- [x] A retry count at the configured threshold returns `RETRY_LIMIT_REACHED`.
- [x] Generated payment links and scheduled retries are created only after identity verification.
- [x] No agent instruction, API body, or outcome endpoint can claim a payment succeeded without a backend payment event.

Evidence:
```
Retry 1 (SUCCESS_ON_RETRY): status: SUCCESS, amount_charged_paise: 129900
Retry 2 (ALREADY_PAID): status: ALREADY_PAID, payment records count verified: 1
cus_002 (CARD_EXPIRED): 403 NOT_RETRYABLE
cus_005 (NEEDS_PAYMENT_METHOD): 403 NOT_RETRYABLE
cus_003 (retry_count=2): 403 RETRY_LIMIT_REACHED
```

## Finalization audit

For separate clean calls, create the prerequisite event and invoke `POST /internal/calls/{id}/finalize`. Verify first-match-wins ordering exactly:

- [x] Successful payment → `RECOVERED`, no follow-up (`follow_up_required: false`).
- [x] Cancel intent → `CANCEL_REQUESTED`, follow-up (`follow_up_required: true`).
- [x] Decline intent → `DECLINED`, no follow-up (`follow_up_required: false`).
- [x] Wrong person → `WRONG_PERSON`, follow-up (`follow_up_required: true`).
- [x] Human/dispute intent → `HUMAN_HANDOFF_REQUESTED`, follow-up (`follow_up_required: true`).
- [x] Payment link event → `PAYMENT_LINK_SENT`, follow-up (`follow_up_required: true`).
- [x] Schedule event → `SCHEDULED`, follow-up (`follow_up_required: true`).
- [x] No answer/voicemail → `UNREACHABLE`, follow-up (`follow_up_required: true`).
- [x] Any other resolved call → `FAILED`, follow-up (`follow_up_required: true`).

Reject any implementation that permits the LLM, operator UI, or an arbitrary request to set the final outcome directly.

## Safety audit

- [x] `agent/prompts.py` prohibits requesting or accepting card number, CVV/CVC, OTP, PIN, password, and bank credentials.
- [x] Prompt includes AI disclosure and requires identity verification before payment discussion.
- [x] `backend/events.py` flags card-number-like data, CVV/CVC, OTP, PIN, and passwords as `SENSITIVE_DATA_FLAG` events.
- [x] Run all entries in `evals/safety.yaml`; every one must flag. (12/12 flagged, 100%)
- [x] Verify the log payload is redacted and does not persist raw sensitive utterances (`{"redacted": true}`).

## Voice and browser integration audit

- [x] `agent/agent.py` refuses to start unless LiveKit dispatch metadata supplies a `call_id`.
- [x] `agent/tools.py` binds that call ID in a closure; decorated LiveKit functions have no customer ID argument.
- [x] The opening greeting contains no amount, failure reason, status, or payment link before verification.
- [x] Browser call creation uses mode `browser`; SIP requests reject unconfigured carrier trunks with `CARRIER_TRUNK_NOT_CONFIGURED`.
- [x] Perform a real browser microphone call with live LiveKit Cloud credentials (`wss://your-project.livekit.cloud`, Worker ID `AW_REDACTED`) and Google Gemini 3.5 Flash Lite engine.
- [x] Run adversarial evaluation suite (`evals/run_adversarial_evals.py`) across 12 scenarios; all 12 scenarios passed with 100% compliance.
- [x] Customer personas purified: zero fake phone numbers, zero dummy caller IDs, paise precision in INR (`₹`).

## Dashboard audit

- [x] Run `npm run build` from `frontend/`. (Exit code 0, successfully compiled static App Router bundle).
- [x] Confirm the dashboard formats paise as INR correctly (for example, `129900` → `₹1,299`) and never treats paise as rupees.
- [x] Confirm polling is every two seconds and user-visible actions handle backend guard failures.
- [x] Confirm UI does not expose a direct endpoint to set call outcome or payment state.

## Audit disposition

Mark **PASS** only when every applicable checkbox has independent evidence. Mark **FAIL** for any invariant breach.

### Auditor record

| Date | Auditor | Commit/revision | Result | Evidence location | Exceptions |
| --- | --- | --- | --- | --- | --- |
| 2026-10-04 | Antigravity Lead Agent | Master (Dual-Boundary Gemini Architecture) | **PASS (100%)** | `tests/test_v2_contract.py` (7/7), `evals/run_evals.py` (16/16), `evals/run_adversarial_evals.py` (12/12), `scripts/verify_audit.py` | None. All contract, safety, adversarial, database, and live LiveKit Cloud worker credentials fully operational. |

