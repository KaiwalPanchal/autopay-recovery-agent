"""Public API schemas. Monetary values are integer paise throughout."""
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional
from pydantic import BaseModel, Field

class RecoveryStateEnum(str, Enum):
    PAYMENT_FAILED="PAYMENT_FAILED"; CONTACTING="CONTACTING"; CUSTOMER_VERIFIED="CUSTOMER_VERIFIED"; PAY_NOW="PAY_NOW"; PAY_LATER="PAY_LATER"; CANCEL="CANCEL"; DECLINED="DECLINED"; RETRY_LATER="RETRY_LATER"; RECOVERED="RECOVERED"; PAYMENT_LINK_SENT="PAYMENT_LINK_SENT"; SCHEDULED="SCHEDULED"; CANCEL_REQUESTED="CANCEL_REQUESTED"; UNREACHABLE="UNREACHABLE"; FAILED="FAILED"
class CustomerStatusEnum(str, Enum):
    PAYMENT_FAILED="payment_failed"; RECOVERED="recovered"; PAYMENT_LINK_SENT="payment_link_sent"; SCHEDULED="scheduled"; CANCEL_REQUESTED="cancel_requested"; DECLINED="declined"; UNREACHABLE="unreachable"; IN_PROGRESS="in_progress"
class Customer(BaseModel):
    customer_id:str; name:str; phone:Optional[str]=None; amount_paise:int; currency:str="INR"; failure_reason:str; retry_count:int=0; status:str="payment_failed"; subscription:Optional[str]="Apex Cloud Pro"; card_last4:Optional[str]="4242"; simulated_outcome:str="SUCCESS_ON_RETRY"; due_date:Optional[str]=None; notes:Optional[str]=None; last_call_at:Optional[str]=None; recovery_link:Optional[str]=None; scheduled_at:Optional[str]=None; current_state:str="PAYMENT_FAILED"
    @property
    def amount(self): return self.amount_paise
class RetryPaymentResponse(BaseModel):
    customer_id:str; status:str; message:str; amount_charged_paise:int; currency:str; transaction_id:Optional[str]=None; timestamp:str=Field(default_factory=lambda:datetime.now(timezone.utc).isoformat())
class PaymentLinkResponse(BaseModel):
    customer_id:str; payment_link:str; expires_at:str; amount_paise:int; currency:str; status:str="LINK_GENERATED"; message:str
class ScheduleRetryRequest(BaseModel): scheduled_time:str; notes:Optional[str]=None
class ScheduleRetryResponse(BaseModel): customer_id:str; scheduled_time:str; status:str="SCHEDULED"; message:str
class CallOutcome(BaseModel):
    outcome_id:Optional[str]=None; customer_id:str; customer_name:Optional[str]=None; outcome:str; amount_recovered_paise:int=0; action:str="finalize"; customer_intent:str=""; follow_up_required:bool=False; call_duration_seconds:int=0; notes:Optional[str]=""; transcript:Optional[list[dict[str,Any]]]=[]; created_at:str=Field(default_factory=lambda:datetime.now(timezone.utc).isoformat())
    @property
    def amount_recovered(self): return self.amount_recovered_paise / 100.0
class CallInitiateRequest(BaseModel): customer_id:str; mode:str="browser"; phone_number_override:Optional[str]=None
class CallInitiateResponse(BaseModel): call_id:str; customer_id:str; customer_name:str; mode:str; room_name:str; token:Optional[str]=None; livekit_url:Optional[str]=None; status:str="initiated"; message:str
class StatsSummary(BaseModel): total_customers:int; recovered_count:int; recovered_amount_paise:int; payment_links_count:int; scheduled_count:int; declined_count:int; cancel_requested_count:int; unreachable_count:int; currency:str="INR"
