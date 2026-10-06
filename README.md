# Autopay Recovery Voice Agent

> **Autonomous conversational AI voice agent for recurring/autopay payment recovery built on LiveKit Agents, FastAPI, and deterministic financial safeguards.**

---

## 1. Project Overview

The **Autopay Recovery Voice Agent** is a full-stack applied AI system designed to resolve failed recurring/autopay subscription payments from customers with zero financial hallucinations and strict compliance guardrails.

### What the System Delivers:
1. **10 Fictional Customer Dataset:** Pre-configured failed payments with distinct failure reasons (insufficient funds, card expired, bank declined, etc.).
2. **Deterministic Fake Payment Processor:** Simulates payment retries and returns deterministic outcomes without processing real money.
3. **Recovery State Machine:** Enforces valid progression (`PAYMENT_FAILED` &rarr; `CONTACTING` &rarr; `CUSTOMER_VERIFIED` &rarr; `PAY_NOW` / `PAY_LATER` / `CANCEL` / `DECLINED`).
4. **LiveKit Voice Agent:** Low-latency conversational turn-taking, speech-to-text, LLM function calling, and text-to-speech.
5. **Operator Dashboard (Next.js):** Real-time monitoring of recovery rates, customer cards, state machine visualizer, and an interactive call console with WebRTC and SIP modes.
6. **Structured Audit Trail:** Automatically logs machine-readable outcomes, detected intents, tool actions, and call durations to disk.

---

## 2. Core Design Principle

The system is architected around a strict separation of concerns:

```
┌─────────────────────────────────────────────────────────────┐
│              THE CORE SEPARATION PRINCIPLE                  │
├──────────────────────────────┬──────────────────────────────┤
│    LLM / Voice Agent         │    Backend / Application     │
│                              │                              │
│ • Interprets customer intent │ • Enforces business logic    │
│ • Maintains empathy & tone   │ • Validates state machine    │
│ • Chooses tool to invoke     │ • Executes simulated charge  │
│                              │ • Owns all financial truth   │
└──────────────────────────────┴──────────────────────────────┘
```

> **The model never invents payment amounts, transaction results, payment statuses, or recovery outcomes.**

If the customer says:
> *"Yeah, try the payment again."*

The LLM determines:
```text
customer_intent = "pay_now"
tool = retry_payment(customer_id="cus_001")
```
The backend determines whether `retry_payment` is legally and operationally permitted in the customer's current state, performs the simulated charge, and returns the result (`SUCCESS` or `DECLINED`).

---

## 3. High-Level Architecture

```text
                         ┌───────────────────────┐
                         │   Operator Dashboard  │
                         │    Next.js + Tailwind │
                         └───────────┬───────────┘
                                     │ HTTP / SSE
                                     ▼
                         ┌───────────────────────┐
                         │    FastAPI Backend    │
                         │                       │
                         │ • State Machine       │
                         │ • Payment Simulator   │
                         │ • Outcomes Logger     │
                         └───────────┬───────────┘
                                     │
                 ┌───────────────────┼───────────────────┐
                 │                   │                   │
                 ▼                   ▼                   ▼
         ┌───────────────┐   ┌───────────────┐   ┌───────────────┐
         │ Customers DB  │   │  Payments Svc │   │ Call Outcomes │
         │ (10 Accounts) │   │ (Deterministic│   │ (Audit Trail) │
         └───────────────┘   └───────────────┘   └───────────────┘
                                     ▲
                                     │ Tool Calls
                                     │
                         ┌───────────┴───────────┐
                         │   LiveKit Voice Agent │
                         │                       │
                         │   STT → LLM → TTS     │
                         │  (Sub-700ms Pipeline) │
                         └───────────┬───────────┘
                                     │
                     ┌───────────────┴───────────────┐
                     │                               │
                     ▼ WebRTC                        ▼ SIP Trunk
              Browser Client                    Telephony Provider
             (Testing Console)                       │
                                                     ▼
                                            Authorized Phone Number
```

---

## 4. The 10 Fictional Customers

All accounts are completely fictional. For testing and demonstration, any account can dial your authorized test telephone number.

| ID | Name | Amount Due | Plan | Failure Reason | Deterministic Simulation Gate |
|---|---|---|---|---|---|
| `cus_001` | **Maya Shah** | ₹1,299 | Apex Cloud Pro | Insufficient Funds | `SUCCESS` (Primary Happy Path) |
| `cus_002` | **Arjun Mehta** | ₹2,499 | Apex Cloud Business | Card Expired | `CARD_EXPIRED` (Payment Link) |
| `cus_003` | **Riya Patel** | ₹799 | Apex Cloud Starter | Bank Declined | `BANK_DECLINED` (Schedule Callback) |
| `cus_004` | **Rohan Verma** | ₹3,499 | Apex Cloud Enterprise | Insufficient Funds | `SUCCESS` (Cancel Test) |
| `cus_005` | **Priya Sharma** | ₹1,499 | Apex Cloud Pro Plus | Card Expired | `NEEDS_PAYMENT_METHOD` (Decline Test)|
| `cus_006` | **Vikram Singh** | ₹4,999 | Apex Enterprise Suite | Temporary Hold | `SUCCESS` |
| `cus_007` | **Ananya Iyer** | ₹899 | Apex Cloud Starter | Network Timeout | `ALREADY_PAID` |
| `cus_008` | **Rahul Nair** | ₹1,999 | Apex Cloud Business | Limit Exceeded | `FAILED` |
| `cus_009` | **Kavita Joshi** | ₹2,899 | Apex Business Plus | Bank Declined | `BANK_DECLINED` |
| `cus_010` | **Amit Desai** | ₹649 | Apex Cloud Lite | Insufficient Funds | `SUCCESS` |

---

## 5. Recovery State Machine

The recovery lifecycle is modeled as an explicit state machine in `backend/recovery.py`:

```text
                    PAYMENT_FAILED
                          │
                          ▼
                     CONTACTING
                          │
             ┌────────────┴────────────┐
             │                         │
        unreachable                 answered
             │                         │
             ▼                         ▼
       RETRY_LATER              CUSTOMER_VERIFIED
                                       │
                         ┌─────────────┼──────────────┐
                         │             │              │
                         ▼             ▼              ▼
                      PAY_NOW      PAY_LATER       CANCEL
                         │             │              │
                         ▼             ▼              ▼
                   RETRY_PAYMENT    SCHEDULED      DECLINED
                         │
                  ┌──────┴───────┐
                  │              │
                  ▼              ▼
              SUCCESS         FAILURE
                  │              │
                  ▼              ▼
              RECOVERED    PAYMENT_LINK
```

### Safety Transitions:
- If a customer says *"I want to cancel"*, state moves to `CANCEL_REQUESTED`. **All future payment actions are strictly blocked**.
- If a customer says *"Not interested"*, state moves to `DECLINED`.
- The agent **cannot retry payment without prior customer verification**.

---

## 6. Conversation Branches & Tools

| Branch | Customer Says | Agent Behavior | Backend Tool Invoked | Final State |
|---|---|---|---|---|
| **A: Retry** | *"Try the charge again, salary came in."* | Acknowledges, calls retry, reports outcome. | `retry_payment(customer_id)` | `RECOVERED` |
| **B: Expired Card** | *"My card expired last month."* | Never asks for card number. Sends SMS link. | `generate_payment_link(customer_id)` | `PAYMENT_LINK_SENT` |
| **C: Pay Later** | *"I'm in a meeting, call Friday."* | Confirms time, queues follow-up. | `schedule_retry(customer_id, time)` | `SCHEDULED` |
| **D: Cancel** | *"Cancel my subscription."* | Respects choice immediately. No hard-sell. | `log_call_outcome(..., outcome='cancel_requested')` | `CANCEL_REQUESTED` |
| **E: Decline** | *"Stop calling, not interested."* | Apologizes, removes from queue. | `log_call_outcome(..., outcome='declined')` | `DECLINED` |

---

## 7. Quickstart Guide

### Prerequisites
- Python 3.10+
- Node.js 18+ and npm

### 1. Setup & Run Backend
```bash
cd autopay-recovery-agent
python -m pip install -r requirements.txt # or pip install fastapi uvicorn httpx pydantic pytest
python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload
```
API Documentation is available at: `http://localhost:8000/docs`

### 2. Run Test Suite
```bash
python -m pytest tests -v
```
Verifies all 18 unit and integration tests across payments, state machine, and tool calls.

### 3. Run Conversation Scenarios (CLI Simulation)
You can simulate all 5 branches in your terminal immediately:
```bash
# Branch A: Retry payment (Maya Shah) -> SUCCESS -> RECOVERED
python -m agent.simulate_call --customer cus_001 --scenario retry

# Branch B: Card expired (Arjun Mehta) -> PAYMENT_LINK_SENT
python -m agent.simulate_call --customer cus_002 --scenario expired

# Branch C: Pay later (Riya Patel) -> SCHEDULED
python -m agent.simulate_call --customer cus_003 --scenario later

# Branch D: Cancel (Rohan Verma) -> CANCEL_REQUESTED
python -m agent.simulate_call --customer cus_004 --scenario cancel

# Branch E: Decline (Priya Sharma) -> DECLINED
python -m agent.simulate_call --customer cus_005 --scenario decline
```

### 4. Setup & Run Operator Dashboard
```bash
cd frontend
npm install
npm run dev
```
Open `http://localhost:3000` in your browser.

---

## 8. Demonstration Walkthrough

### Demo 1 — Successful Recovery (Maya Shah)
1. Open the dashboard at `http://localhost:3000`.
2. Locate **Maya Shah** (`cus_001`, Amount: `₹1,299`, Reason: `Insufficient Funds`).
3. Click **Call** &rarr; Select **Branch A: Retry Payment**.
4. Agent opens with friendly identity verification:
   > *"Hi, is this Maya Shah? I'm an automated payment assistant calling on behalf of Apex Cloud..."*
5. Customer states: *"Yes, speaking. My salary just came in today, go ahead and try the payment again."*
6. Agent invokes `retry_payment('cus_001')`.
7. Fake processor returns `SUCCESS` with transaction ID `txn_sim_xxxx`.
8. Agent confirms: *"Great, that payment went through successfully! Your account is completely up to date."*
9. Call finishes &rarr; Dashboard immediately updates:
   - Status: `✓ RECOVERED`
   - Total Recovered KPI increments by `₹1,299`.

### Demo 2 — Card Expired / Payment Link (Arjun Mehta)
1. Locate **Arjun Mehta** (`cus_002`, Amount: `₹2,499`, Reason: `Card Expired`).
2. Click **Call** &rarr; Select **Branch B: Card Expired**.
3. Customer states: *"My old credit card expired last month."*
4. Safety constraint kicks in: Agent **does not ask for card digits**.
5. Agent invokes `generate_payment_link('cus_002')`.
6. Simulated SMS link generated: `https://pay.apexcloud.io/recovery/pay_xxxx?cid=cus_002`.
7. Dashboard updates:
   - Status: `→ LINK SENT`
   - Payment Links KPI increments by 1.

---

## 9. Telephony & Outbound SIP Setup

To connect the agent to an outbound phone call:

1. Configure a LiveKit Cloud project or self-hosted server in `.env`:
   ```env
   LIVEKIT_URL=wss://your-project.livekit.cloud
   LIVEKIT_API_KEY=your_key
   LIVEKIT_API_SECRET=your_secret
   LIVEKIT_SIP_TRUNK_ID=ST_your_sip_trunk_id  # Optional carrier trunk
   ```
2. Create an Outbound SIP Trunk in your LiveKit Cloud dashboard (with Twilio or Telnyx).
3. Start the LiveKit agent worker:
   ```bash
   python -m agent.agent dev
   ```
4. For browser evaluation, use the **LiveKit WebRTC Audio Session** tab. If a carrier trunk is configured, outbound PSTN calls can be routed through that trunk.

---

## 10. Privacy & Safety Commitments

- **No Card Data Collection:** The agent is programmatically restricted from capturing card numbers, CVVs, or OTPs.
- **Deterministic Discretion:** The LLM cannot negotiate unauthorized discounts or waive fees.
- **TCPA / FDCPA / RBI Compliance-by-Design:** Strict time-of-day controls, limited-content openings, zero third-party disclosure, and instant cessation upon cancellation or decline.

---

## 11. Verified Evaluation Scorecard & Test Status

The system includes automated deterministic contract testing, safety evals, and adversarial stress testing against the live Google Gemini engine:

- **Contract Tests (`tests/test_v2_contract.py`):** **7/7 PASSED (100%)**
- **Safety & Scenario Tests (`evals/run_evals.py`):** **16/16 Scenarios, 12/12 Safety Checks PASSED (100%)**
- **Adversarial Stress Test Suite (`evals/run_adversarial_evals.py`):** **12/12 Scenarios PASSED (100%)**
  - Prompt Injection & DAN Jailbreak Resistance (100% Secure)
  - Credential Baiting Refusal for Card PAN, CVV, OTP (100% Secure)
  - Third-Party Roommate Debt Withholding (100% Secure)
  - Phantom UPI Payment Gaslighting Defense (100% Secure)
  - Abusive Persona De-escalation & Wrong Number Exit (100% Secure)

Run the full adversarial evaluation suite:
```bash
python evals/run_adversarial_evals.py
```

---

## 12. Next Frontier Roadmap: Indian Languages & S2S Voice

For full architectural deep dive on the next evolution of this platform, see:
👉 **[`docs/NEXT_FRONTIER_INDIAN_VOICE_ROADMAP.md`](docs/NEXT_FRONTIER_INDIAN_VOICE_ROADMAP.md)**

### Key Roadmap Priorities:
1. **Native Multimodal Speech-to-Speech (S2S):** Direct audio-in / audio-out via Gemini Multimodal Live API with native tool calling, dropping voice-to-ear latency to **~250ms – 300ms**.
2. **Local `faster-whisper` (CTranslate2):** Self-hosted GPU transcription for zero-cloud latency and 100% DPDP Act compliance.
3. **Hyper-Realistic Indian Voice (Sarvam AI / Bulbul / Saarathi):** Conversational code-switching (**Hinglish**), authentic Indian English/Hindi prosody, respectful honorifics (*"-ji"*), and ambient noise suppression for real Indian telephony.

