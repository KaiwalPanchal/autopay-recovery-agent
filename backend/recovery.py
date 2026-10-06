"""Call guards and deterministic outcome derivation."""
from .database import db, now
class RecoveryStateMachine:
 def transition(self,cid,new_state,notes=None):
  c=db.get_customer(cid)
  if not c:return False,'Customer not found.'
  allowed={'PAYMENT_FAILED':{'CONTACTING'},'CONTACTING':{'CUSTOMER_VERIFIED','UNREACHABLE'},'CUSTOMER_VERIFIED':{'PAY_NOW','PAY_LATER','CANCEL','DECLINED'},'PAY_NOW':{'RECOVERED','PAYMENT_LINK_SENT','FAILED','DECLINED'},'PAY_LATER':{'SCHEDULED','PAYMENT_LINK_SENT','DECLINED'},'CANCEL':{'CANCEL_REQUESTED'}}
  if new_state != c.current_state and new_state not in allowed.get(c.current_state,set()): return False,f"Invalid transition: cannot move from '{c.current_state}' to '{new_state}'."
  status={'RECOVERED':'recovered','PAYMENT_LINK_SENT':'payment_link_sent','SCHEDULED':'scheduled','CANCEL_REQUESTED':'cancel_requested','DECLINED':'declined','UNREACHABLE':'unreachable'}.get(new_state,'in_progress' if new_state not in {'PAYMENT_FAILED','FAILED'} else 'payment_failed')
  db.update_customer(cid,current_state=new_state,status=status,notes=notes);return True,f'Customer transitioned to {new_state}.'
 def validate_action(self,state,action): return (state not in {'DECLINED','CANCEL_REQUESTED','RECOVERED'},'Action is permitted.')
 def guard(self,call,action):
  if call.locked:return 'CALL_LOCKED'
  if action in {'payment_details','retry_payment','generate_payment_link','schedule_retry'} and not call.identity_verified:return 'IDENTITY_NOT_VERIFIED'
  c=db.get_customer(call.customer_id)
  if action=='retry_payment' and c.simulated_outcome in {'CARD_EXPIRED','NEEDS_PAYMENT_METHOD'}:return 'NOT_RETRYABLE'
  if action=='retry_payment' and c.retry_count>=2:return 'RETRY_LIMIT_REACHED'
  return None
 def finalize(self,call_id):
  call=db.get_call(call_id)
  if not call:return None
  events=db.events(call_id);types=[x[0] for x in events];intents=[p.get('intent') for t,p in events if t=='INTENT'];c=db.get_customer(call.customer_id)
  if c.status=='recovered':out,follow='RECOVERED',False
  elif 'cancel_subscription' in intents:out,follow='CANCEL_REQUESTED',True
  elif 'decline' in intents:out,follow='DECLINED',False
  elif 'wrong_person' in types:out,follow='WRONG_PERSON',True
  elif any(i in {'request_human','dispute_amount'} for i in intents):out,follow='HUMAN_HANDOFF_REQUESTED',True
  elif 'payment_link' in types:out,follow='PAYMENT_LINK_SENT',True
  elif 'schedule_retry' in types:out,follow='SCHEDULED',True
  elif not call.answered or 'voicemail' in types:out,follow='UNREACHABLE',True
  else:out,follow='FAILED',True
  db.update_call(call_id,outcome=out,follow_up_required=follow,finalized_at=now());return {'outcome':out,'follow_up_required':follow,'customer_id':call.customer_id}
recovery_machine=RecoveryStateMachine()
