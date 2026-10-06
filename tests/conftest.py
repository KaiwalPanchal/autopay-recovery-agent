"""Test isolation: every test run uses a throwaway SQLite file and fixed test tokens.

These assignments run at import time, before any ``backend`` module is imported, so
the tests can never touch ``data/app.db`` or depend on the developer's own env/.env.
"""
import os
import pathlib
import tempfile

_TMP = tempfile.mkdtemp(prefix="autopay-tests-")
os.environ["AUTOPAY_DB_PATH"] = str(pathlib.Path(_TMP) / "test.db")
os.environ["INTERNAL_API_TOKEN"] = "test-internal-token-0123456789"
os.environ["OPERATOR_API_TOKEN"] = "test-operator-token-9876543210"
for _name in ("ENVIRONMENT", "LIVEKIT_SIP_TRUNK_ID", "SIP_TRUNK_ID", "CORS_ALLOWED_ORIGINS", "LIVEKIT_URL"):
    os.environ.pop(_name, None)

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from backend.database import db  # noqa: E402
from backend.main import app  # noqa: E402


@pytest.fixture(autouse=True)
def seed():
    db.reset_to_seed()
    yield


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def internal():
    return {"Authorization": f"Bearer {os.environ['INTERNAL_API_TOKEN']}"}


@pytest.fixture
def operator():
    return {"Authorization": f"Bearer {os.environ['OPERATOR_API_TOKEN']}"}


@pytest.fixture
def new_call(client, operator):
    def _new(customer="cus_001"):
        r = client.post("/api/calls", headers=operator, json={"customer_id": customer, "mode": "browser"})
        assert r.status_code == 200, r.text
        return r.json()["call_id"]
    return _new


@pytest.fixture
def verify(client, internal):
    """Complete the identity challenge with the real card last-4 from the seed data."""
    def _verify(cid, customer="cus_001"):
        answer = db.get_customer(customer).card_last4
        r = client.post(f"/internal/calls/{cid}/identity", headers=internal,
                        json={"result": "challenge_answer", "answer": answer})
        assert r.status_code == 200 and r.json()["data"]["identity_verified"] is True, r.text
    return _verify
