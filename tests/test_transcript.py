"""scan_transcript is wired into the live call path via the transcript endpoint."""
from backend.database import db


def post(client, internal, cid, text, speaker="customer"):
    return client.post(f"/internal/calls/{cid}/transcript", headers=internal, json={"speaker": speaker, "text": text})


def test_card_number_in_transcript_is_flagged_and_surfaced_on_finalize(client, internal, new_call):
    cid = new_call()
    r = post(client, internal, cid, "sure my card is 4111 1111 1111 1111")
    assert r.status_code == 200 and r.json()["data"]["flagged"] is True
    assert "SENSITIVE_DATA_FLAG" in [t for t, _ in db.events(cid)]
    assert "4111" not in str(db.events(cid))  # raw text is never stored
    assert client.post(f"/internal/calls/{cid}/finalize", headers=internal).json()["data"]["sensitive_data_flagged"] is True


def test_clean_transcript_is_not_flagged(client, internal, new_call):
    cid = new_call()
    assert post(client, internal, cid, "yes please try again").json()["data"]["flagged"] is False
    assert client.post(f"/internal/calls/{cid}/finalize", headers=internal).json()["data"]["sensitive_data_flagged"] is False


def test_transcript_requires_token_and_validates_size(client, internal, new_call):
    cid = new_call()
    assert client.post(f"/internal/calls/{cid}/transcript", json={"speaker": "customer", "text": "hi"}).status_code == 401
    assert post(client, internal, cid, "x" * 5000).status_code == 422
    assert post(client, internal, cid, "hi", speaker="root").status_code == 422
