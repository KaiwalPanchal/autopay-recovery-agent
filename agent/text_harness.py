"""Text-only runner exercising the same deterministic call lifecycle (no HTTP, no LLM)."""
from datetime import datetime, timedelta, timezone
from backend.database import db
from backend.payments import payment_service
from backend.recovery import recovery_machine
def run(customer_id, identity='verified', intent=None, action=None):
 """identity='verified' answers the backend challenge with the customer's real last-4;
 'wrong_person' marks a wrong-number call. Verification is decided by the backend either way."""
 call_id=db.create_call(customer_id,'text');verified=False
 if identity=='wrong_person': recovery_machine.mark_wrong_person(call_id)
 elif identity=='verified': verified=recovery_machine.verify_identity(call_id,db.get_customer(customer_id).card_last4)[0]=='OK'
 if intent: recovery_machine.record_intent(call_id,intent)
 result=None;call=db.get_call(call_id);ok=verified and not call.locked
 if action=='retry_payment' and ok and not recovery_machine.guard(call,'retry_payment'): result=payment_service.retry_payment(customer_id).model_dump();db.add_event(call_id,'retry_payment',result)
 if action=='payment_link' and ok and not recovery_machine.guard(call,'generate_payment_link'): result=payment_service.generate_payment_link(customer_id).model_dump();db.add_event(call_id,'payment_link',result)
 if action=='schedule_retry' and ok and not recovery_machine.guard(call,'schedule_retry'): result=payment_service.schedule_retry(customer_id,(datetime.now(timezone.utc)+timedelta(days=2)).isoformat()).model_dump();db.add_event(call_id,'schedule_retry',result)
 return {'call_id':call_id,'result':result,'final':recovery_machine.finalize(call_id)}
