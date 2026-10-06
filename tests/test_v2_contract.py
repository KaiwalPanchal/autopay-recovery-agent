"""Core contract: paise money, call-bound tools, identity boundary, derived outcomes."""
from backend.database import DB_PATH, db


def test_tests_use_isolated_database():
    assert "autopay-tests-" in str(DB_PATH)
    assert DB_PATH.name != "app.db"


def test_paise_seed_and_identity_boundary(client, operator, internal, new_call):
    assert client.get("/api/customers/cus_001", headers=operator).json()["amount_paise"] == 129900
    cid = new_call()
    r = client.get(f"/internal/calls/{cid}/payment", headers=internal)
    assert r.status_code == 403 and r.json()["detail"]["code"] == "IDENTITY_NOT_VERIFIED"


def test_internal_token_required(client, new_call):
    assert client.get(f"/internal/calls/{new_call()}/payment").status_code == 401


def test_retry_is_call_bound_and_idempotent(client, internal, new_call, verify):
    cid = new_call(); verify(cid)
    one = client.post(f"/internal/calls/{cid}/retry", headers=internal).json()["data"]
    two = client.post(f"/internal/calls/{cid}/retry", headers=internal).json()["data"]
    assert one["amount_charged_paise"] == 129900
    assert two["status"] == "ALREADY_PAID"


def test_cancel_locks_payment_tools_and_derives_outcome(client, internal, new_call, verify):
    cid = new_call(); verify(cid)
    client.post(f"/internal/calls/{cid}/intent", headers=internal, json={"intent": "cancel_subscription"})
    assert client.post(f"/internal/calls/{cid}/retry", headers=internal).json()["detail"]["code"] == "CALL_LOCKED"
    assert client.post(f"/internal/calls/{cid}/finalize", headers=internal).json()["data"]["outcome"] == "CANCEL_REQUESTED"


def test_wrong_person_is_locked_and_derived(client, internal, new_call):
    cid = new_call()
    client.post(f"/internal/calls/{cid}/identity", headers=internal, json={"result": "wrong_person"})
    assert client.get(f"/internal/calls/{cid}/payment", headers=internal).json()["detail"]["code"] == "CALL_LOCKED"
    assert client.post(f"/internal/calls/{cid}/finalize", headers=internal).json()["data"]["outcome"] == "WRONG_PERSON"


def test_non_retryable_and_limit_guards(client, internal, new_call, verify):
    cid = new_call("cus_002"); verify(cid, "cus_002")
    assert client.post(f"/internal/calls/{cid}/retry", headers=internal).json()["detail"]["code"] == "NOT_RETRYABLE"
    cid = new_call("cus_003"); verify(cid, "cus_003"); db.update_customer("cus_003", retry_count=2)
    assert client.post(f"/internal/calls/{cid}/retry", headers=internal).json()["detail"]["code"] == "RETRY_LIMIT_REACHED"


def test_sip_dial_guard_independent_of_environment(client, operator, monkeypatch):
    # Result must not depend on whatever the developer has exported.
    monkeypatch.delenv("LIVEKIT_SIP_TRUNK_ID", raising=False)
    monkeypatch.delenv("SIP_TRUNK_ID", raising=False)
    r = client.post("/api/calls", headers=operator,
                    json={"customer_id": "cus_001", "mode": "sip", "phone_number_override": "+910000000000"})
    assert r.status_code == 403


def test_sip_with_trunk_is_explicitly_not_implemented(client, operator, monkeypatch):
    monkeypatch.setenv("LIVEKIT_SIP_TRUNK_ID", "ST_fake")
    r = client.post("/api/calls", headers=operator, json={"customer_id": "cus_001", "mode": "sip"})
    assert r.status_code == 501


def test_no_hardcoded_livekit_host(client, operator, monkeypatch):
    monkeypatch.delenv("LIVEKIT_URL", raising=False)
    body = client.post("/api/calls", headers=operator, json={"customer_id": "cus_001"}).json()
    assert body["livekit_url"] is None


def test_finalize_updates_customer_status(client, internal, new_call, verify):
    cid = new_call(); verify(cid)
    client.post(f"/internal/calls/{cid}/intent", headers=internal, json={"intent": "decline"})
    client.post(f"/internal/calls/{cid}/finalize", headers=internal)
    assert db.get_customer("cus_001").status == "declined"


def test_actions_rejected_after_finalize(client, internal, new_call, verify):
    cid = new_call(); verify(cid)
    client.post(f"/internal/calls/{cid}/finalize", headers=internal)
    r = client.post(f"/internal/calls/{cid}/retry", headers=internal)
    assert r.status_code == 403 and r.json()["detail"]["code"] == "CALL_FINALIZED"
