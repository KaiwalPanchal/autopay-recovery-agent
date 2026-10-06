"""Public API schemas. Monetary values are integer paise throughout."""
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Any, Literal, Optional
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

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
MAX_SCHEDULE_DAYS=90
class ScheduleRetryRequest(BaseModel):
    model_config=ConfigDict(extra='forbid')
    scheduled_time:datetime; notes:Optional[str]=Field(default=None,max_length=500)
    @field_validator('scheduled_time',mode='before')
    @classmethod
    def _iso_string_only(cls,v):
        if not isinstance(v,str) or not (8<=len(v)<=40): raise ValueError('scheduled_time must be an ISO-8601 datetime string')
        return v
    @field_validator('scheduled_time')
    @classmethod
    def _future_window(cls,v):
        if v.tzinfo is None: v=v.replace(tzinfo=timezone.utc)  # naive input is treated as UTC
        v=v.astimezone(timezone.utc); t=datetime.now(timezone.utc)
        if v<=t: raise ValueError('scheduled_time must be in the future')
        if v>t+timedelta(days=MAX_SCHEDULE_DAYS): raise ValueError(f'scheduled_time must be within {MAX_SCHEDULE_DAYS} days')
        return v
class ScheduleRetryResponse(BaseModel): customer_id:str; scheduled_time:str; status:str="SCHEDULED"; message:str
class CallOutcome(BaseModel):
    outcome_id:Optional[str]=None; customer_id:str; customer_name:Optional[str]=None; outcome:str; amount_recovered_paise:int=0; action:str="finalize"; customer_intent:str=""; follow_up_required:bool=False; call_duration_seconds:int=0; notes:Optional[str]=""; transcript:Optional[list[dict[str,Any]]]=[]; created_at:str=Field(default_factory=lambda:datetime.now(timezone.utc).isoformat())
    @property
    def amount_recovered(self): return self.amount_recovered_paise / 100.0
class CallInitiateRequest(BaseModel):
    model_config=ConfigDict(extra='forbid')
    customer_id:str=Field(max_length=64); mode:Literal['browser','sip']='browser'
    phone_number_override:Optional[str]=Field(default=None,pattern=r'^\+[1-9][0-9]{7,14}$')
IntentLiteral=Literal['pay_now','pay_later','cancel_subscription','decline','request_human','dispute_amount']
class IntentRequest(BaseModel):
    model_config=ConfigDict(extra='forbid')
    intent:IntentLiteral
class IdentityRequest(BaseModel):
    """``challenge_answer`` carries the customer's answer (last 4 of the card on file); ``wrong_person`` ends the call.
    The old free-form ``verified`` result is gone: only the backend decides who is verified."""
    model_config=ConfigDict(extra='forbid')
    result:Literal['challenge_answer','wrong_person']; answer:Optional[str]=Field(default=None,max_length=4,pattern=r'^[0-9]{4}$')
    @model_validator(mode='after')
    def _answer_required(self):
        if self.result=='challenge_answer' and self.answer is None: raise ValueError('answer is required for challenge_answer')
        return self
class TranscriptRequest(BaseModel):
    model_config=ConfigDict(extra='forbid')
    speaker:Literal['customer','agent']; text:str=Field(max_length=4000)
class CallInitiateResponse(BaseModel): call_id:str; customer_id:str; customer_name:str; mode:str; room_name:str; token:Optional[str]=None; livekit_url:Optional[str]=None; status:str="initiated"; message:str
class StatsSummary(BaseModel): total_customers:int; recovered_count:int; recovered_amount_paise:int; payment_links_count:int; scheduled_count:int; declined_count:int; cancel_requested_count:int; unreachable_count:int; currency:str="INR"
