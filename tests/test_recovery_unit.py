"""Unit tests for RecoveryStateMachine.guard / finalize / transition (no HTTP layer)."""
import pytest

from backend.database import db
from backend.recovery import recovery_machine as rm


def mkcall(customer="cus_001", **flags):
    cid = db.create_call(customer, "text")
    if flags:
        db.update_call(cid, **flags)
    return db.get_call(cid)


# ---- guard: order is locked -> finalized -> identity -> retryability -> retry limit
def test_guard_locked_wins_over_everything():
    c = mkcall(locked=True, identity_verified=True)
    assert rm.guard(c, "retry_payment") == "CALL_LOCKED"


def test_guard_finalized_before_identity():
    c = mkcall(finalized_at="2026-01-01T00:00:00+00:00")
    assert rm.guard(c, "payment_details") == "CALL_FINALIZED"


@pytest.mark.parametrize("action", ["payment_details", "retry_payment", "generate_payment_link", "schedule_retry"])
def test_guard_requires_identity(action):
    assert rm.guard(mkcall(), action) == "IDENTITY_NOT_VERIFIED"
    assert rm.guard(mkcall(identity_verified=True), action) is None


def test_guard_not_retryable_before_limit():
    db.update_customer("cus_002", retry_count=5)
    assert rm.guard(mkcall("cus_002", identity_verified=True), "retry_payment") == "NOT_RETRYABLE"


def test_guard_retry_limit():
    db.update_customer("cus_003", retry_count=2)
    assert rm.guard(mkcall("cus_003", identity_verified=True), "retry_payment") == "RETRY_LIMIT_REACHED"
    assert rm.guard(mkcall("cus_003", identity_verified=True), "generate_payment_link") is None


# ---- finalize: decision-table priority
def finalize_with(events, customer="cus_001", **flags):
    c = mkcall(customer, answered=True, **flags)
    for typ, payload in events:
        db.add_event(c.call_id, typ, payload)
    return rm.finalize(c.call_id)


@pytest.mark.parametrize("events,expected", [
    ([("INTENT", {"intent": "cancel_subscription"})], "CANCEL_REQUESTED"),
    ([("INTENT", {"intent": "decline"})], "DECLINED"),
    ([("wrong_person", {})], "WRONG_PERSON"),
    ([("identity_lockout", {})], "IDENTITY_FAILED"),
    ([("INTENT", {"intent": "request_human"})], "HUMAN_HANDOFF_REQUESTED"),
    ([("INTENT", {"intent": "dispute_amount"})], "HUMAN_HANDOFF_REQUESTED"),
    ([("payment_link", {})], "PAYMENT_LINK_SENT"),
    ([("schedule_retry", {})], "SCHEDULED"),
    ([("voicemail", {})], "UNREACHABLE"),
    ([], "FAILED"),
])
def test_finalize_decision_table(events, expected):
    assert finalize_with(events)["outcome"] == expected


def test_finalize_cancel_beats_decline_and_link():
    r = finalize_with([("payment_link", {}), ("INTENT", {"intent": "decline"}), ("INTENT", {"intent": "cancel_subscription"})])
    assert r["outcome"] == "CANCEL_REQUESTED"


def test_finalize_recovered_wins_and_no_follow_up():
    db.update_customer("cus_001", status="recovered")
    r = finalize_with([("INTENT", {"intent": "decline"})])
    assert r == {"outcome": "RECOVERED", "follow_up_required": False, "customer_id": "cus_001",
                 "sensitive_data_flagged": False}


def test_finalize_unanswered_is_unreachable_and_unknown_call_is_none():
    c = mkcall()
    assert rm.finalize(c.call_id)["outcome"] == "UNREACHABLE"
    assert rm.finalize("call_does_not_exist") is None


def test_finalize_is_idempotent_and_persists():
    c = mkcall(answered=True)
    db.add_event(c.call_id, "INTENT", {"intent": "decline"})
    first, second = rm.finalize(c.call_id), rm.finalize(c.call_id)
    assert first == second
    assert db.get_call(c.call_id).outcome == "DECLINED"


@pytest.mark.parametrize("events,status,state", [
    ([("INTENT", {"intent": "cancel_subscription"})], "cancel_requested", "CANCEL_REQUESTED"),
    ([("INTENT", {"intent": "decline"})], "declined", "DECLINED"),
    ([("voicemail", {})], "unreachable", "UNREACHABLE"),
    ([("wrong_person", {})], "payment_failed", "PAYMENT_FAILED"),
])
def test_finalize_syncs_customer_status(events, status, state):
    db.update_customer("cus_001", status="in_progress", current_state="CONTACTING")
    finalize_with(events)
    c = db.get_customer("cus_001")
    assert (c.status, c.current_state) == (status, state)


# ---- transition: used by the simulate_call CLI, not by the live HTTP path
def test_transition_valid_path_and_status_mapping():
    for s in ("CONTACTING", "CUSTOMER_VERIFIED", "PAY_NOW", "RECOVERED"):
        ok, _ = rm.transition("cus_001", s)
        assert ok
    c = db.get_customer("cus_001")
    assert (c.current_state, c.status) == ("RECOVERED", "recovered")


def test_transition_rejects_skips_and_unknown_customer():
    ok, msg = rm.transition("cus_001", "RECOVERED")
    assert not ok and "Invalid transition" in msg
    assert db.get_customer("cus_001").current_state == "PAYMENT_FAILED"
    assert rm.transition("cus_nope", "CONTACTING") == (False, "Customer not found.")


def test_transition_terminal_states_have_no_exit():
    rm.transition("cus_001", "CONTACTING"); rm.transition("cus_001", "CUSTOMER_VERIFIED")
    rm.transition("cus_001", "CANCEL"); rm.transition("cus_001", "CANCEL_REQUESTED")
    ok, _ = rm.transition("cus_001", "PAY_NOW")
    assert not ok
