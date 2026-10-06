"""Operator auth, fail-closed token config, CORS and input validation."""
import pytest

from backend.database import db

OPERATOR_ROUTES = [
    ("get", "/api/customers"), ("get", "/api/customers/cus_001"), ("get", "/api/stats"),
    ("post", "/api/customers/reset"), ("post", "/api/calls"), ("post", "/api/calls/initiate"),
]


@pytest.mark.parametrize("method,path", OPERATOR_ROUTES)
def test_operator_routes_require_token(client, method, path):
    assert getattr(client, method)(path).status_code == 401


@pytest.mark.parametrize("method,path", OPERATOR_ROUTES)
def test_operator_routes_reject_wrong_and_internal_token(client, internal, method, path):
    assert getattr(client, method)(path, headers={"Authorization": "Bearer nope"}).status_code == 401
    assert getattr(client, method)(path, headers=internal).status_code == 401


def test_reset_without_token_does_not_wipe(client, operator):
    db.update_customer("cus_001", status="recovered")
    assert client.post("/api/customers/reset").status_code == 401
    assert db.get_customer("cus_001").status == "recovered"
    assert client.post("/api/customers/reset", headers=operator).status_code == 200
    assert db.get_customer("cus_001").status == "payment_failed"


def test_operator_token_does_not_open_internal_routes(client, operator, new_call):
    assert client.get(f"/internal/calls/{new_call()}", headers=operator).status_code == 401


def test_health_is_public_and_minimal(client):
    r = client.get("/api/health")
    assert r.status_code == 200 and r.json() == {"status": "healthy"}


def test_fail_closed_when_tokens_unset(client, operator, new_call, monkeypatch):
    cid = new_call()
    monkeypatch.delenv("OPERATOR_API_TOKEN")
    monkeypatch.delenv("INTERNAL_API_TOKEN")
    monkeypatch.delenv("ENVIRONMENT", raising=False)
    assert client.get("/api/customers", headers=operator).status_code == 401
    for tok in ("dev-internal-token", "dev-operator-token", "", "None"):
        assert client.get(f"/internal/calls/{cid}", headers={"Authorization": f"Bearer {tok}"}).status_code == 401
        assert client.get("/api/customers", headers={"Authorization": f"Bearer {tok}"}).status_code == 401


def test_empty_token_env_is_treated_as_unset(client, monkeypatch):
    monkeypatch.setenv("OPERATOR_API_TOKEN", "")
    assert client.get("/api/customers", headers={"Authorization": "Bearer "}).status_code == 401


def test_explicit_test_environment_override(client, monkeypatch):
    monkeypatch.delenv("OPERATOR_API_TOKEN"); monkeypatch.delenv("INTERNAL_API_TOKEN")
    monkeypatch.setenv("ENVIRONMENT", "test")
    assert client.get("/api/customers", headers={"Authorization": "Bearer dev-operator-token"}).status_code == 200
    monkeypatch.setenv("ENVIRONMENT", "production")
    assert client.get("/api/customers", headers={"Authorization": "Bearer dev-operator-token"}).status_code == 401


def test_token_compare_is_constant_time():
    import inspect
    from backend import security
    assert "compare_digest" in inspect.getsource(security)


def test_cors_blocks_unlisted_origin_and_never_wildcard(client):
    r = client.options("/api/customers", headers={"Origin": "https://evil.example",
                                                  "Access-Control-Request-Method": "GET"})
    assert "access-control-allow-origin" not in r.headers
    ok = client.options("/api/customers", headers={"Origin": "http://localhost:3000",
                                                   "Access-Control-Request-Method": "GET"})
    assert ok.headers.get("access-control-allow-origin") == "http://localhost:3000"
    assert ok.headers.get("access-control-allow-credentials") != "true"


def test_cors_origin_parser_drops_wildcard():
    from backend.security import parse_cors_origins
    assert parse_cors_origins("*, https://a.example ,") == ["https://a.example"]
    assert "*" not in parse_cors_origins(None)


@pytest.mark.parametrize("bad", ["", "rm -rf /", "'; DROP TABLE customers;--", "PAY_NOW", "x" * 5000, 5, ["decline"], None])
def test_intent_is_enum_validated(client, internal, new_call, bad):
    cid = new_call()
    assert client.post(f"/internal/calls/{cid}/intent", headers=internal, json={"intent": bad}).status_code == 422


@pytest.mark.parametrize("good", ["pay_now", "pay_later", "cancel_subscription", "decline", "request_human", "dispute_amount"])
def test_valid_intents_accepted(client, internal, new_call, good):
    assert client.post(f"/internal/calls/{new_call()}/intent", headers=internal, json={"intent": good}).status_code == 200


@pytest.mark.parametrize("bad", ["verified", "VERIFIED", "ok", "", "wrong_person'; --", 1])
def test_identity_result_is_enum_validated(client, internal, new_call, bad):
    r = client.post(f"/internal/calls/{new_call()}/identity", headers=internal, json={"result": bad, "answer": "4242"})
    assert r.status_code == 422


@pytest.mark.parametrize("bad", ["tomorrow", "2026-13-45", "", "1700000000", 1700000000, "2020-01-01T00:00:00Z", "'; DROP--"])
def test_scheduled_time_must_be_future_datetime(client, internal, new_call, verify, bad):
    cid = new_call(); verify(cid)
    assert client.post(f"/internal/calls/{cid}/schedule", headers=internal, json={"scheduled_time": bad}).status_code == 422


def test_scheduled_time_valid_and_oversize_notes(client, internal, new_call, verify):
    from datetime import datetime, timedelta, timezone
    cid = new_call(); verify(cid)
    when = (datetime.now(timezone.utc) + timedelta(days=2)).isoformat()
    assert client.post(f"/internal/calls/{cid}/schedule", headers=internal,
                       json={"scheduled_time": when, "notes": "x" * 501}).status_code == 422
    assert client.post(f"/internal/calls/{cid}/schedule", headers=internal,
                       json={"scheduled_time": when, "notes": "Friday"}).status_code == 200


def test_call_request_validation(client, operator):
    assert client.post("/api/calls", headers=operator, json={"customer_id": "cus_001", "mode": "carrier-pigeon"}).status_code == 422
    assert client.post("/api/calls", headers=operator, json={"customer_id": "x" * 500}).status_code == 422
    assert client.post("/api/calls", headers=operator, json={"customer_id": "cus_001' OR '1'='1"}).status_code in (404, 422)
    assert client.post("/api/calls", headers=operator, json={"customer_id": "cus_001", "mode": "sip",
                                                            "phone_number_override": "abc"}).status_code == 422
