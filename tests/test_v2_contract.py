import pytest
from fastapi.testclient import TestClient
from backend.database import db
from backend.main import app

client=TestClient(app); headers={'Authorization':'Bearer dev-internal-token'}
@pytest.fixture(autouse=True)
def seed(): db.reset_to_seed()
def call(customer='cus_001'):
 return client.post('/api/calls',json={'customer_id':customer,'mode':'browser'}).json()['call_id']
def verify(cid): assert client.post(f'/internal/calls/{cid}/identity',headers=headers,json={'result':'verified'}).status_code==200
def test_paise_seed_and_identity_boundary():
 assert client.get('/api/customers/cus_001').json()['amount_paise']==129900
 cid=call(); r=client.get(f'/internal/calls/{cid}/payment',headers=headers);assert r.status_code==403;assert r.json()['detail']['code']=='IDENTITY_NOT_VERIFIED'
def test_internal_token_required(): assert client.get(f'/internal/calls/{call()}/payment').status_code==401
def test_retry_is_call_bound_and_idempotent():
 cid=call();verify(cid);one=client.post(f'/internal/calls/{cid}/retry',headers=headers).json()['data'];two=client.post(f'/internal/calls/{cid}/retry',headers=headers).json()['data'];assert one['amount_charged_paise']==129900;assert two['status']=='ALREADY_PAID'
def test_cancel_locks_payment_tools_and_derives_outcome():
 cid=call();verify(cid);client.post(f'/internal/calls/{cid}/intent',headers=headers,json={'intent':'cancel_subscription'});assert client.post(f'/internal/calls/{cid}/retry',headers=headers).json()['detail']['code']=='CALL_LOCKED';assert client.post(f'/internal/calls/{cid}/finalize',headers=headers).json()['data']['outcome']=='CANCEL_REQUESTED'
def test_wrong_person_is_locked_and_derived():
 cid=call();client.post(f'/internal/calls/{cid}/identity',headers=headers,json={'result':'wrong_person'});assert client.get(f'/internal/calls/{cid}/payment',headers=headers).json()['detail']['code']=='CALL_LOCKED';assert client.post(f'/internal/calls/{cid}/finalize',headers=headers).json()['data']['outcome']=='WRONG_PERSON'
def test_non_retryable_and_limit_guards():
 cid=call('cus_002');verify(cid);assert client.post(f'/internal/calls/{cid}/retry',headers=headers).json()['detail']['code']=='NOT_RETRYABLE'
 cid=call('cus_003');verify(cid);db.update_customer('cus_003',retry_count=2);assert client.post(f'/internal/calls/{cid}/retry',headers=headers).json()['detail']['code']=='RETRY_LIMIT_REACHED'
def test_sip_dial_guard(): assert client.post('/api/calls',json={'customer_id':'cus_001','mode':'sip','phone_number_override':'+910000000000'}).status_code==403
