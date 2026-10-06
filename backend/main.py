"""Operator API (/api/*, operator token) and call-bound internal tool API (/internal/*, internal token).

Auth and CORS are configured in backend/security.py (fail closed, no default tokens).
"""
import os, time
from fastapi import APIRouter, Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from .database import db
from .customers import customer_service
from .payments import payment_service
from .recovery import recovery_machine
from .events import scan_transcript
from .security import envelope, parse_cors_origins, require_internal, require_operator
from .models import CallInitiateRequest, IdentityRequest, IntentRequest, ScheduleRetryRequest, TranscriptRequest

app = FastAPI(title='Autopay Recovery Voice Agent', version='2.1.0')
# Bearer-header auth, no cookies: credentials are not allowed cross-origin and no wildcard is ever honoured.
app.add_middleware(
    CORSMiddleware,
    allow_origins=parse_cors_origins(os.getenv('CORS_ALLOWED_ORIGINS')),
    allow_credentials=False,
    allow_methods=['GET', 'POST', 'OPTIONS'],
    allow_headers=['Authorization', 'Content-Type'],
)
operator_api = APIRouter(prefix='/api', dependencies=[Depends(require_operator)])
internal_api = APIRouter(prefix='/internal/calls', dependencies=[Depends(require_internal)])


def sip_trunk_id():
    return os.getenv('LIVEKIT_SIP_TRUNK_ID') or os.getenv('SIP_TRUNK_ID')


def call(cid):
    c = db.get_call(cid)
    if not c:
        raise HTTPException(404, detail=envelope('CALL_NOT_FOUND'))
    return c


def guard(cid, action):
    c = call(cid)
    code = recovery_machine.guard(c, action)
    if code:
        raise HTTPException(403, detail=envelope(code))
    return c


@app.get('/api/health')
def health():
    return {'status': 'healthy'}


# ---------------------------------------------------------------- operator routes
@operator_api.get('/customers')
def customers(status: str | None = None):
    return customer_service.list_customers(status[:32] if status else None)


@operator_api.get('/customers/{cid}')
def customer(cid: str):
    c = db.get_customer(cid)
    if not c:
        raise HTTPException(404, 'Customer not found')
    return c


@operator_api.post('/customers/reset')
def reset():
    return db.reset_to_seed()


@operator_api.get('/stats')
def stats():
    return db.get_stats()


def generate_livekit_token(room_name: str, identity: str) -> str | None:
    key, secret = os.getenv('LIVEKIT_API_KEY'), os.getenv('LIVEKIT_API_SECRET')
    if not (key and secret):
        return None
    try:
        from livekit.api import AccessToken, VideoGrants
        return AccessToken(key, secret).with_grants(VideoGrants(room=room_name, room_join=True)).with_identity(identity).to_jwt()
    except Exception:
        return None


@operator_api.post('/calls')
@operator_api.post('/calls/initiate')
def create_call(req: CallInitiateRequest):
    c = db.get_customer(req.customer_id)
    if not c:
        raise HTTPException(404, 'Customer not found')
    if req.mode == 'sip':
        if not sip_trunk_id():
            raise HTTPException(403, detail='CARRIER_TRUNK_NOT_CONFIGURED')
        # No code in this repo places an outbound SIP call; refuse rather than pretend.
        raise HTTPException(501, detail='SIP_DIAL_NOT_IMPLEMENTED')
    cid = db.create_call(c.customer_id, req.mode)
    db.update_customer(c.customer_id, current_state='CONTACTING', status='in_progress')
    room = f'recovery_{cid}'
    token = generate_livekit_token(room, f'operator_{cid}')
    return {'call_id': cid, 'customer_id': c.customer_id, 'customer_name': c.name, 'mode': req.mode, 'room_name': room,
            'token': token, 'livekit_url': os.getenv('LIVEKIT_URL') or None, 'status': 'initiated',
            'message': 'Call session created. No voice agent is dispatched automatically.'}


# ---------------------------------------------------------------- internal (agent tool) routes
@internal_api.get('/{cid}')
def context(cid: str):
    c = call(cid)
    cust = db.get_customer(c.customer_id)
    return envelope('OK', {'call_id': c.call_id, 'customer_name': cust.name if cust else '',
                           'identity_verified': c.identity_verified, 'locked': c.locked})


@internal_api.post('/{cid}/identity')
def identity(cid: str, body: IdentityRequest):
    c = call(cid)
    if c.locked:
        raise HTTPException(403, detail=envelope('CALL_LOCKED'))
    if c.finalized_at:
        raise HTTPException(403, detail=envelope('CALL_FINALIZED'))
    if body.result == 'wrong_person':
        recovery_machine.mark_wrong_person(cid)
        return envelope('OK', {'identity_verified': False})
    code, data = recovery_machine.verify_identity(cid, body.answer)
    if code == 'CALL_LOCKED':
        raise HTTPException(403, detail=envelope(code))
    return envelope(code, data)


@internal_api.post('/{cid}/intent')
def intent(cid: str, body: IntentRequest):
    c = call(cid)
    if c.finalized_at:
        raise HTTPException(403, detail=envelope('CALL_FINALIZED'))
    recovery_machine.record_intent(cid, body.intent)
    return envelope('OK', {'recorded': body.intent})


@internal_api.post('/{cid}/transcript')
def transcript(cid: str, body: TranscriptRequest):
    c = call(cid)
    if c.finalized_at:
        raise HTTPException(403, detail=envelope('CALL_FINALIZED'))
    return envelope('OK', {'flagged': scan_transcript(cid, body.text)})


@internal_api.get('/{cid}/payment')
def payment(cid: str):
    c = guard(cid, 'payment_details')
    return envelope('OK', payment_service.get_payment_details(c.customer_id))


@internal_api.post('/{cid}/retry')
def retry(cid: str):
    c = guard(cid, 'retry_payment')
    start = time.monotonic()
    r = payment_service.retry_payment(c.customer_id).model_dump()
    db.add_event(cid, 'retry_payment', r, int((time.monotonic() - start) * 1000))
    return envelope('OK', r)


@internal_api.post('/{cid}/payment-link')
def link(cid: str):
    c = guard(cid, 'generate_payment_link')
    r = payment_service.generate_payment_link(c.customer_id).model_dump()
    db.add_event(cid, 'payment_link', r)
    return envelope('OK', r)


@internal_api.post('/{cid}/schedule')
def schedule(cid: str, body: ScheduleRetryRequest):
    c = guard(cid, 'schedule_retry')
    r = payment_service.schedule_retry(c.customer_id, body.scheduled_time.isoformat(), body.notes).model_dump()
    db.add_event(cid, 'schedule_retry', r)
    return envelope('OK', r)


@internal_api.post('/{cid}/voicemail')
def voicemail(cid: str):
    c = call(cid)
    if c.locked or c.finalized_at:
        raise HTTPException(403, detail=envelope('CALL_LOCKED' if c.locked else 'CALL_FINALIZED'))
    db.add_event(cid, 'voicemail', {})
    return envelope('OK')


@internal_api.post('/{cid}/finalize')
def finalize(cid: str):
    r = recovery_machine.finalize(cid)
    if not r:
        raise HTTPException(404, detail=envelope('CALL_NOT_FOUND'))
    return envelope('OK', r)


app.include_router(operator_api)
app.include_router(internal_api)
