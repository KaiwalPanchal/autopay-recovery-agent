"""Text-only runner exercising the same deterministic call lifecycle."""
from backend.database import db
from backend.payments import payment_service
from backend.recovery import recovery_machine
def run(customer_id, identity='verified', intent=None, action=None):
 call_id=db.create_call(customer_id,'text');db.update_call(call_id,answered=True,identity_verified=identity=='verified',locked=identity=='wrong_person');db.add_event(call_id,'wrong_person' if identity=='wrong_person' else 'identity',{'result':identity})
 if intent: db.update_call(call_id,locked=intent in {'cancel_subscription','decline'});db.add_event(call_id,'INTENT',{'intent':intent})
 result=None
 if action=='retry_payment' and identity=='verified' and not intent: result=payment_service.retry_payment(customer_id).model_dump();db.add_event(call_id,'retry_payment',result)
 if action=='payment_link' and identity=='verified' and not intent: result=payment_service.generate_payment_link(customer_id).model_dump();db.add_event(call_id,'payment_link',result)
 if action=='schedule_retry' and identity=='verified' and not intent: result=payment_service.schedule_retry(customer_id,'2026-10-10T09:00:00Z').model_dump();db.add_event(call_id,'schedule_retry',result)
 return {'call_id':call_id,'result':result,'final':recovery_machine.finalize(call_id)}
