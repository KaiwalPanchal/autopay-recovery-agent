"""Deterministic, idempotent simulated payment processor."""
import uuid
from datetime import datetime, timezone, timedelta
from .database import db
from .models import RetryPaymentResponse, PaymentLinkResponse, ScheduleRetryResponse
class PaymentService:
 def get_payment_details(self,cid):
  c=db.get_customer(cid)
  return {"error":"NOT_FOUND"} if not c else {"customer_id":c.customer_id,"amount_due_paise":c.amount_paise,"currency":c.currency,"status":c.status,"failure_reason":c.failure_reason,"retry_count":c.retry_count}
 def retry_payment(self,cid):
  c=db.get_customer(cid)
  if not c:return RetryPaymentResponse(customer_id=cid,status='NOT_FOUND',message='Customer not found.',amount_charged_paise=0,currency='INR')
  if c.status=='recovered':return RetryPaymentResponse(customer_id=cid,status='ALREADY_PAID',message='Payment has already settled.',amount_charged_paise=c.amount_paise,currency=c.currency,transaction_id=f'txn_settled_{cid}')
  count=c.retry_count+1; outcome=c.simulated_outcome; success=outcome=='SUCCESS_ON_RETRY' or (outcome=='FAIL_THEN_SUCCEED' and count>=2)
  if success:
   txn='txn_sim_'+uuid.uuid4().hex[:10];db.update_customer(cid,retry_count=count,status='recovered',current_state='RECOVERED');db.add_payment(cid,c.amount_paise,'SUCCESS',txn)
   return RetryPaymentResponse(customer_id=cid,status='SUCCESS',message='Payment retry succeeded.',amount_charged_paise=c.amount_paise,currency=c.currency,transaction_id=txn)
  status={'CARD_EXPIRED':'CARD_EXPIRED','BANK_DECLINED':'BANK_DECLINED','NEEDS_PAYMENT_METHOD':'NEEDS_PAYMENT_METHOD'}.get(outcome,'FAILED');db.update_customer(cid,retry_count=count);db.add_payment(cid,0,status)
  return RetryPaymentResponse(customer_id=cid,status=status,message='Payment retry was not successful.',amount_charged_paise=0,currency=c.currency)
 def generate_payment_link(self,cid):
  c=db.get_customer(cid)
  if not c:return PaymentLinkResponse(customer_id=cid,payment_link='',expires_at='',amount_paise=0,currency='INR',status='NOT_FOUND',message='Customer not found.')
  link=f'https://pay.apexcloud.io/recovery/pay_{uuid.uuid4().hex[:12]}';expires=(datetime.now(timezone.utc)+timedelta(hours=48)).isoformat();db.update_customer(cid,recovery_link=link,status='payment_link_sent',current_state='PAYMENT_LINK_SENT')
  return PaymentLinkResponse(customer_id=cid,payment_link=link,expires_at=expires,amount_paise=c.amount_paise,currency=c.currency,message='Secure payment link generated.')
 def schedule_retry(self,cid,when,notes=None):
  c=db.get_customer(cid)
  if not c:return ScheduleRetryResponse(customer_id=cid,scheduled_time=when,status='NOT_FOUND',message='Customer not found.')
  db.update_customer(cid,scheduled_at=when,notes=notes,status='scheduled',current_state='SCHEDULED');return ScheduleRetryResponse(customer_id=cid,scheduled_time=when,message='Retry scheduled.')
payment_service=PaymentService()
