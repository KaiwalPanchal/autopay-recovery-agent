"""Operator API and authenticated call-bound internal tool API."""
import os, time
from fastapi import FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from .database import db
from .customers import customer_service
from .payments import payment_service
from .recovery import recovery_machine
from .models import CallInitiateRequest
app=FastAPI(title='Autopay Recovery Voice Agent',version='2.0.0')
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
TOKEN=os.getenv('INTERNAL_API_TOKEN','dev-internal-token'); SIP_TRUNK_ID=os.getenv('LIVEKIT_SIP_TRUNK_ID') or os.getenv('SIP_TRUNK_ID')
def envelope(code,data=None,actions=None): return {'ok':code=='OK','code':code,'data':data or {},'allowed_next_actions':actions or []}
def internal(a):
 if a != f'Bearer {TOKEN}':raise HTTPException(401,detail=envelope('UNAUTHORIZED'))
def call(cid):
 c=db.get_call(cid)
 if not c:raise HTTPException(404,detail=envelope('CALL_NOT_FOUND'))
 return c
def guard(cid,action):
 c=call(cid);code=recovery_machine.guard(c,action)
 if code:raise HTTPException(403,detail=envelope(code))
 return c
@app.get('/api/health')
def health():return {'status':'healthy','customers_loaded':len(db.get_all_customers())}
@app.get('/api/customers')
def customers(status=None):return customer_service.list_customers(status)
@app.get('/api/customers/{cid}')
def customer(cid):
 c=db.get_customer(cid)
 if not c:raise HTTPException(404,'Customer not found')
 return c
@app.post('/api/customers/reset')
def reset():return db.reset_to_seed()
@app.get('/api/stats')
def stats():return db.get_stats()
LK_URL=os.getenv('LIVEKIT_URL','wss://your-project.livekit.cloud'); LK_KEY=os.getenv('LIVEKIT_API_KEY'); LK_SECRET=os.getenv('LIVEKIT_API_SECRET')
def generate_livekit_token(room_name:str,identity:str)->str|None:
 if not (LK_KEY and LK_SECRET): return None
 try:
  from livekit.api import AccessToken, VideoGrants
  return AccessToken(LK_KEY,LK_SECRET).with_grants(VideoGrants(room=room_name,room_join=True)).with_identity(identity).to_jwt()
 except Exception: return None

@app.post('/api/calls')
@app.post('/api/calls/initiate')
def create_call(req:CallInitiateRequest):
 c=db.get_customer(req.customer_id)
 if not c:raise HTTPException(404,'Customer not found')
 if req.mode=='sip':
  if not SIP_TRUNK_ID:
   raise HTTPException(403,detail='CARRIER_TRUNK_NOT_CONFIGURED')
 cid=db.create_call(c.customer_id,req.mode);db.update_customer(c.customer_id,current_state='CONTACTING',status='in_progress')
 room=f'recovery_{cid}';token=generate_livekit_token(room,f'operator_{cid}')
 return {'call_id':cid,'customer_id':c.customer_id,'customer_name':c.name,'mode':req.mode,'room_name':room,'token':token,'livekit_url':LK_URL,'status':'initiated','message':'Call session created.'}
@app.get('/internal/calls/{cid}')
def context(cid,authorization:str|None=Header(None)):
 internal(authorization);c=call(cid);return envelope('OK',{'call_id':c.call_id,'identity_verified':c.identity_verified,'locked':c.locked})
class Identity(BaseModel): result:str
@app.post('/internal/calls/{cid}/identity')
def identity(cid,body:Identity,authorization:str|None=Header(None)):
 internal(authorization);call(cid);wrong=body.result=='wrong_person';db.update_call(cid,identity_verified=body.result=='verified',answered=True,locked=wrong);db.add_event(cid,'wrong_person' if wrong else 'identity',body.model_dump());return envelope('OK',{'identity_verified':body.result=='verified'})
class Intent(BaseModel): intent:str
@app.post('/internal/calls/{cid}/intent')
def intent(cid,body:Intent,authorization:str|None=Header(None)):
 internal(authorization);call(cid);db.update_call(cid,locked=body.intent in {'cancel_subscription','decline'});db.add_event(cid,'INTENT',body.model_dump());return envelope('OK',{'recorded':body.intent})
@app.get('/internal/calls/{cid}/payment')
def payment(cid,authorization:str|None=Header(None)):
 internal(authorization);c=guard(cid,'payment_details');return envelope('OK',payment_service.get_payment_details(c.customer_id))
@app.post('/internal/calls/{cid}/retry')
def retry(cid,authorization:str|None=Header(None)):
 internal(authorization);c=guard(cid,'retry_payment');start=time.monotonic();r=payment_service.retry_payment(c.customer_id).model_dump();db.add_event(cid,'retry_payment',r,int((time.monotonic()-start)*1000));return envelope('OK',r)
@app.post('/internal/calls/{cid}/payment-link')
def link(cid,authorization:str|None=Header(None)):
 internal(authorization);c=guard(cid,'generate_payment_link');r=payment_service.generate_payment_link(c.customer_id).model_dump();db.add_event(cid,'payment_link',r);return envelope('OK',r)
class Schedule(BaseModel): scheduled_time:str; notes:str|None=None
@app.post('/internal/calls/{cid}/schedule')
def schedule(cid,body:Schedule,authorization:str|None=Header(None)):
 internal(authorization);c=guard(cid,'schedule_retry');r=payment_service.schedule_retry(c.customer_id,body.scheduled_time,body.notes).model_dump();db.add_event(cid,'schedule_retry',r);return envelope('OK',r)
@app.post('/internal/calls/{cid}/voicemail')
def voicemail(cid,authorization:str|None=Header(None)):
 internal(authorization);call(cid);db.add_event(cid,'voicemail',{});return envelope('OK')
@app.post('/internal/calls/{cid}/finalize')
def finalize(cid,authorization:str|None=Header(None)):
 internal(authorization);r=recovery_machine.finalize(cid)
 if not r:raise HTTPException(404,detail=envelope('CALL_NOT_FOUND'))
 return envelope('OK',r)
