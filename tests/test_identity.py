"""Backend-verified identity challenge (last 4 digits of the card on file)."""
from backend.database import db
from backend.recovery import MAX_IDENTITY_ATTEMPTS


def answer(client, internal, cid, value):
    return client.post(f"/internal/calls/{cid}/identity", headers=internal,
                       json={"result": "challenge_answer", "answer": value})


def test_correct_answer_verifies(client, internal, new_call):
    cid = new_call()
    r = answer(client, internal, cid, "4242")
    assert r.status_code == 200 and r.json()["code"] == "OK" and r.json()["data"]["identity_verified"] is True
    assert client.get(f"/internal/calls/{cid}/payment", headers=internal).status_code == 200


def test_wrong_answer_does_not_verify_and_counts_down(client, internal, new_call):
    cid = new_call()
    r = answer(client, internal, cid, "0000").json()
    assert r["ok"] is False and r["code"] == "IDENTITY_MISMATCH"
    assert r["data"]["identity_verified"] is False and r["data"]["attempts_remaining"] == MAX_IDENTITY_ATTEMPTS - 1
    assert client.get(f"/internal/calls/{cid}/payment", headers=internal).json()["detail"]["code"] == "IDENTITY_NOT_VERIFIED"


def test_answer_for_another_customers_card_fails(client, internal, new_call):
    cid = new_call("cus_001")
    assert answer(client, internal, cid, db.get_customer("cus_002").card_last4).json()["code"] == "IDENTITY_MISMATCH"


def test_retry_limit_locks_call_even_for_correct_answer(client, internal, new_call):
    cid = new_call()
    codes = [answer(client, internal, cid, "0001").json()["code"] for _ in range(MAX_IDENTITY_ATTEMPTS)]
    assert codes[-1] == "IDENTITY_LOCKED"
    r = answer(client, internal, cid, "4242")
    assert r.status_code == 403 and r.json()["detail"]["code"] == "CALL_LOCKED"
    assert client.get(f"/internal/calls/{cid}/payment", headers=internal).status_code == 403
    assert db.get_call(cid).identity_verified is False
    out = client.post(f"/internal/calls/{cid}/finalize", headers=internal).json()["data"]
    assert out["outcome"] == "IDENTITY_FAILED"


def test_free_form_verified_string_rejected(client, internal, new_call):
    cid = new_call()
    r = client.post(f"/internal/calls/{cid}/identity", headers=internal, json={"result": "verified"})
    assert r.status_code == 422
    assert db.get_call(cid).identity_verified is False


def test_challenge_answer_requires_four_digits(client, internal, new_call):
    cid = new_call()
    for bad in ("", "42", "42424", "abcd", "42 42", "4242; DROP TABLE x", "9" * 10000):
        assert answer(client, internal, cid, bad).status_code == 422
    assert client.post(f"/internal/calls/{cid}/identity", headers=internal,
                       json={"result": "challenge_answer"}).status_code == 422
    assert db.get_call(cid).identity_attempts == 0


def test_wrong_person_lock_cannot_be_undone_by_correct_answer(client, internal, new_call):
    cid = new_call()
    client.post(f"/internal/calls/{cid}/identity", headers=internal, json={"result": "wrong_person"})
    assert answer(client, internal, cid, "4242").status_code == 403
    assert db.get_call(cid).locked is True and db.get_call(cid).identity_verified is False


def test_answer_is_not_stored_in_events(client, internal, new_call):
    cid = new_call()
    answer(client, internal, cid, "1234")
    assert "1234" not in str(db.events(cid))


def test_call_context_exposes_name_not_card(client, internal, new_call):
    cid = new_call()
    d = client.get(f"/internal/calls/{cid}", headers=internal).json()["data"]
    assert d["customer_name"] == "Maya Shah" and "4242" not in str(d)
