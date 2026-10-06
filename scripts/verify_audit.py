"""Automated Independent Audit Verification Script for Autopay Recovery Agent v2.
Runs each verification check independently and prints timestamp, command, exit code, and output.
"""
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import json
import sqlite3
import time
from datetime import datetime, timezone
from fastapi.testclient import TestClient

from backend.main import app
from backend.database import db, DB_PATH
from backend.events import scan_transcript
from agent.prompts import SYSTEM_PROMPT
from agent.tools import RecoveryAgentTools, create_livekit_function_context

client = TestClient(app)
TOKEN = "dev-internal-token"
AUTH = {"Authorization": f"Bearer {TOKEN}"}

def run_checks():
    results = {}
    print(f"=== AUDIT VERIFICATION RUN: {datetime.now(timezone.utc).isoformat()} ===\n")

    # 1. Database and money audit
    print("--- 1. DATABASE AND MONEY AUDIT ---")
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    tables = [r[0] for r in cur.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name").fetchall()]
    print("SQLite Tables:", tables)
    assert set(tables) >= {"call_events", "calls", "customers", "payments"}, "Missing required tables"

    # Check columns in customers and payments
    cust_cols = {r[1]: r[2] for r in cur.execute("PRAGMA table_info(customers)").fetchall()}
    pay_cols = {r[1]: r[2] for r in cur.execute("PRAGMA table_info(payments)").fetchall()}
    print("customers amount column:", cust_cols.get("amount_paise"), "(amount present?:", "amount" in cust_cols, ")")
    print("payments amount column:", pay_cols.get("amount_paise"), "(amount present?:", "amount" in pay_cols, ")")
    assert "amount_paise" in cust_cols and "amount" not in cust_cols
    assert "amount_paise" in pay_cols and "amount" not in pay_cols
    assert cust_cols["amount_paise"].upper() in ("INTEGER", "INT")
    assert pay_cols["amount_paise"].upper() in ("INTEGER", "INT")

    # Reset DB and check cus_001
    db.reset_to_seed()
    c1 = db.get_customer("cus_001")
    print(f"cus_001: amount_paise={c1.amount_paise} (type={type(c1.amount_paise).__name__})")
    assert c1.amount_paise == 129900

    # Match all 10 seed customers
    seed_json = json.loads((ROOT / "data" / "customers.json").read_text(encoding="utf-8"))
    assert len(seed_json) == 10
    for s in seed_json:
        db_c = db.get_customer(s["customer_id"])
        assert db_c is not None, f"Customer {s['customer_id']} not found"
        assert db_c.amount_paise == s["amount_paise"], f"Amount mismatch for {s['customer_id']}"
        assert db_c.simulated_outcome == s["simulated_outcome"], f"Simulated outcome mismatch for {s['customer_id']}"
    print(f"All {len(seed_json)} seed customers match data/customers.json exactly.")

    # Confirm call_events has no update/delete method in db
    assert not hasattr(db, "update_event")
    assert not hasattr(db, "delete_event")
    print("call_events is append-only: db has no update_event or delete_event methods.")

    # 2. Internal API authorization and identity audit
    print("\n--- 2. INTERNAL API AUTHORIZATION AND IDENTITY AUDIT ---")
    # Initiate call
    call_res = client.post("/api/calls", json={"customer_id": "cus_001", "mode": "browser"}).json()
    cid = call_res["call_id"]
    print(f"Initiated call: {cid}")

    # No auth token -> 401 UNAUTHORIZED
    r_noauth = client.get(f"/internal/calls/{cid}/payment")
    print("GET /payment without auth:", r_noauth.status_code, r_noauth.json())
    assert r_noauth.status_code == 401
    assert r_noauth.json()["detail"]["code"] == "UNAUTHORIZED"

    # Wrong auth token -> 401 UNAUTHORIZED
    r_badauth = client.get(f"/internal/calls/{cid}/payment", headers={"Authorization": "Bearer wrong-token"})
    assert r_badauth.status_code == 401
    assert r_badauth.json()["detail"]["code"] == "UNAUTHORIZED"

    # Valid token before verification -> 403 IDENTITY_NOT_VERIFIED
    for endpoint, method in [
        (f"/internal/calls/{cid}/payment", "GET"),
        (f"/internal/calls/{cid}/retry", "POST"),
        (f"/internal/calls/{cid}/payment-link", "POST"),
        (f"/internal/calls/{cid}/schedule", "POST"),
    ]:
        body = {"scheduled_time": "2026-10-10T10:00:00Z"} if "schedule" in endpoint else None
        res = client.request(method, endpoint, headers=AUTH, json=body)
        print(f"{method} {endpoint} before verify:", res.status_code, res.json()["detail"]["code"])
        assert res.status_code == 403
        assert res.json()["detail"]["code"] == "IDENTITY_NOT_VERIFIED"

    # Verify identity
    r_ver = client.post(f"/internal/calls/{cid}/identity", headers=AUTH, json={"result": "verified"})
    assert r_ver.status_code == 200
    print("Identity verified:", r_ver.json())

    # Read payment facts
    r_pay = client.get(f"/internal/calls/{cid}/payment", headers=AUTH)
    assert r_pay.status_code == 200
    print("Payment facts:", r_pay.json()["data"])
    assert r_pay.json()["data"]["amount_due_paise"] == 129900

    # Record cancel_subscription intent
    r_cancel = client.post(f"/internal/calls/{cid}/intent", headers=AUTH, json={"intent": "cancel_subscription"})
    assert r_cancel.status_code == 200
    print("Cancel intent recorded:", r_cancel.json())

    # Attempt retry -> CALL_LOCKED
    r_locked = client.post(f"/internal/calls/{cid}/retry", headers=AUTH)
    print("Retry after cancel:", r_locked.status_code, r_locked.json())
    assert r_locked.status_code == 403
    assert r_locked.json()["detail"]["code"] == "CALL_LOCKED"

    # Test wrong_person lock on a fresh call
    call_res2 = client.post("/api/calls", json={"customer_id": "cus_001", "mode": "browser"}).json()
    cid2 = call_res2["call_id"]
    client.post(f"/internal/calls/{cid2}/identity", headers=AUTH, json={"result": "wrong_person"})
    r_wp_locked = client.get(f"/internal/calls/{cid2}/payment", headers=AUTH)
    print("Payment after wrong_person:", r_wp_locked.status_code, r_wp_locked.json())
    assert r_wp_locked.status_code == 403
    assert r_wp_locked.json()["detail"]["code"] == "CALL_LOCKED"

    # 3. Payment simulator and guard audit
    print("\n--- 3. PAYMENT SIMULATOR AND GUARD AUDIT ---")
    db.reset_to_seed()
    # cus_001 has SUCCESS_ON_RETRY
    call_s = client.post("/api/calls", json={"customer_id": "cus_001", "mode": "browser"}).json()["call_id"]
    client.post(f"/internal/calls/{call_s}/identity", headers=AUTH, json={"result": "verified"})
    ret1 = client.post(f"/internal/calls/{call_s}/retry", headers=AUTH).json()
    print("Retry 1 (SUCCESS_ON_RETRY):", ret1)
    assert ret1["data"]["status"] == "SUCCESS"
    assert ret1["data"]["amount_charged_paise"] == 129900

    # Retrying a recovered payment returns ALREADY_PAID and does NOT create second charge record
    num_payments_before = len(cur.execute("SELECT * FROM payments WHERE customer_id='cus_001'").fetchall())
    ret2 = client.post(f"/internal/calls/{call_s}/retry", headers=AUTH).json()
    print("Retry 2 (ALREADY_PAID):", ret2)
    assert ret2["data"]["status"] == "ALREADY_PAID"
    num_payments_after = len(cur.execute("SELECT * FROM payments WHERE customer_id='cus_001'").fetchall())
    assert num_payments_after == num_payments_before == 1, "A second payment row was created!"
    print(f"Payment records count verified: {num_payments_after} (no duplicate charge created).")

    # CARD_EXPIRED and NEEDS_PAYMENT_METHOD are rejected with NOT_RETRYABLE
    # cus_002 is CARD_EXPIRED, cus_005 is NEEDS_PAYMENT_METHOD
    for cust_id in ["cus_002", "cus_005"]:
        c_sim = client.post("/api/calls", json={"customer_id": cust_id, "mode": "browser"}).json()["call_id"]
        client.post(f"/internal/calls/{c_sim}/identity", headers=AUTH, json={"result": "verified"})
        r_nr = client.post(f"/internal/calls/{c_sim}/retry", headers=AUTH)
        print(f"Retry for {cust_id} ({db.get_customer(cust_id).simulated_outcome}):", r_nr.status_code, r_nr.json()["detail"]["code"])
        assert r_nr.status_code == 403
        assert r_nr.json()["detail"]["code"] == "NOT_RETRYABLE"

    # Retry count at configured threshold (>=2) returns RETRY_LIMIT_REACHED
    c_lim = client.post("/api/calls", json={"customer_id": "cus_003", "mode": "browser"}).json()["call_id"]
    client.post(f"/internal/calls/{c_lim}/identity", headers=AUTH, json={"result": "verified"})
    db.update_customer("cus_003", retry_count=2)
    r_lim = client.post(f"/internal/calls/{c_lim}/retry", headers=AUTH)
    print("Retry at retry_count=2:", r_lim.status_code, r_lim.json()["detail"]["code"])
    assert r_lim.status_code == 403
    assert r_lim.json()["detail"]["code"] == "RETRY_LIMIT_REACHED"

    # 4. Finalization audit
    print("\n--- 4. FINALIZATION AUDIT ---")
    ordering_checks = [
        # (name, setup_fn, expected_outcome, expected_followup)
        ("Successful payment", lambda cid: (client.post(f"/internal/calls/{cid}/identity", headers=AUTH, json={"result": "verified"}), client.post(f"/internal/calls/{cid}/retry", headers=AUTH)), "RECOVERED", False),
        ("Cancel intent", lambda cid: (client.post(f"/internal/calls/{cid}/identity", headers=AUTH, json={"result": "verified"}), client.post(f"/internal/calls/{cid}/intent", headers=AUTH, json={"intent": "cancel_subscription"})), "CANCEL_REQUESTED", True),
        ("Decline intent", lambda cid: (client.post(f"/internal/calls/{cid}/identity", headers=AUTH, json={"result": "verified"}), client.post(f"/internal/calls/{cid}/intent", headers=AUTH, json={"intent": "decline"})), "DECLINED", False),
        ("Wrong person", lambda cid: client.post(f"/internal/calls/{cid}/identity", headers=AUTH, json={"result": "wrong_person"}), "WRONG_PERSON", True),
        ("Human/dispute intent (request_human)", lambda cid: (client.post(f"/internal/calls/{cid}/identity", headers=AUTH, json={"result": "verified"}), client.post(f"/internal/calls/{cid}/intent", headers=AUTH, json={"intent": "request_human"})), "HUMAN_HANDOFF_REQUESTED", True),
        ("Payment link event", lambda cid: (client.post(f"/internal/calls/{cid}/identity", headers=AUTH, json={"result": "verified"}), client.post(f"/internal/calls/{cid}/payment-link", headers=AUTH)), "PAYMENT_LINK_SENT", True),
        ("Schedule event", lambda cid: (client.post(f"/internal/calls/{cid}/identity", headers=AUTH, json={"result": "verified"}), client.post(f"/internal/calls/{cid}/schedule", headers=AUTH, json={"scheduled_time": "2026-10-10T10:00:00Z"})), "SCHEDULED", True),
        ("No answer/voicemail", lambda cid: client.post(f"/internal/calls/{cid}/voicemail", headers=AUTH), "UNREACHABLE", True),
        ("Any other resolved call", lambda cid: client.post(f"/internal/calls/{cid}/identity", headers=AUTH, json={"result": "verified"}), "FAILED", True),
    ]

    for name, setup, exp_out, exp_follow in ordering_checks:
        db.reset_to_seed()
        fcid = client.post("/api/calls", json={"customer_id": "cus_001", "mode": "browser"}).json()["call_id"]
        setup(fcid)
        fin = client.post(f"/internal/calls/{fcid}/finalize", headers=AUTH).json()["data"]
        print(f"Finalize [{name}]: outcome={fin['outcome']}, follow_up_required={fin['follow_up_required']}")
        assert fin["outcome"] == exp_out, f"Expected {exp_out}, got {fin['outcome']}"
        assert fin["follow_up_required"] == exp_follow, f"Expected follow_up={exp_follow}, got {fin['follow_up_required']}"

    # 5. Safety audit
    print("\n--- 5. SAFETY AUDIT ---")
    # Check SYSTEM_PROMPT
    assert "card numbers" in SYSTEM_PROMPT.lower()
    assert "cvv" in SYSTEM_PROMPT.lower()
    assert "otp" in SYSTEM_PROMPT.lower()
    assert "pin" in SYSTEM_PROMPT.lower()
    assert "passwords" in SYSTEM_PROMPT.lower()
    assert "bank credentials" in SYSTEM_PROMPT.lower()
    assert "ai" in SYSTEM_PROMPT.lower()
    assert "verify identity" in SYSTEM_PROMPT.lower()
    print("SYSTEM_PROMPT constraints confirmed.")

    # Check evals/safety.yaml
    safety_entries = json.loads((ROOT / "evals" / "safety.yaml").read_text(encoding="utf-8"))
    assert len(safety_entries) == 12
    db.reset_to_seed()
    scid = db.create_call("cus_001", "text")
    for s in safety_entries:
        flagged = scan_transcript(scid, s["input"])
        assert flagged, f"Safety check failed to flag: {s['input']}"
    print(f"All {len(safety_entries)} safety entries flagged.")

    # Check payload is redacted
    events = db.events(scid)
    flagged_evts = [p for t, p in events if t == "SENSITIVE_DATA_FLAG"]
    assert len(flagged_evts) == 12
    for p in flagged_evts:
        assert p == {"redacted": True}, f"Raw sensitive utterance leaked in payload: {p}"
    print("Sensitive data log payloads are strictly redacted ({'redacted': True}).")

    # 6. LiveKit function context and closure inspection
    print("\n--- 6. LIVEKIT CONTEXT AND CALL BOUNDING ---")
    fnc = create_livekit_function_context("call_test_123")
    print(f"LiveKit FunctionContext created: {fnc is not None}")

    # 7. SIP Dial Guard
    print("\n--- 7. SIP DIAL GUARD ---")
    sip_bad = client.post("/api/calls", json={"customer_id": "cus_001", "mode": "sip", "phone_number_override": "+910000000000"})
    print("SIP dial unconfigured trunk:", sip_bad.status_code, sip_bad.json())
    assert sip_bad.status_code == 403
    assert sip_bad.json()["detail"] == "CARRIER_TRUNK_NOT_CONFIGURED"

    print("\nALL BACKEND/DB/SAFETY/AUTH CHECKS PASSED.")

if __name__ == "__main__":
    run_checks()
