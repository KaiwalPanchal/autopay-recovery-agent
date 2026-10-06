"""SQLite persistence; events are append-only and money is stored in paise."""
import json, os, uuid
from pathlib import Path
from datetime import datetime, timezone
from sqlalchemy import create_engine, text, update, String, Integer, Text, Boolean, ForeignKey, select, delete
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker
from .models import Customer, StatsSummary
BASE_DIR=Path(__file__).resolve().parent.parent; DATA_DIR=BASE_DIR/'data'; DB_PATH=Path(os.getenv('AUTOPAY_DB_PATH') or DATA_DIR/'app.db')
class Base(DeclarativeBase): pass
class CustomerRow(Base):
 __tablename__='customers'; customer_id:Mapped[str]=mapped_column(String,primary_key=True); name:Mapped[str]=mapped_column(String); phone:Mapped[str|None]=mapped_column(String,nullable=True,default=None); amount_paise:Mapped[int]=mapped_column(Integer); currency:Mapped[str]=mapped_column(String); failure_reason:Mapped[str]=mapped_column(String); retry_count:Mapped[int]=mapped_column(Integer,default=0); status:Mapped[str]=mapped_column(String); subscription:Mapped[str|None]=mapped_column(String,nullable=True); card_last4:Mapped[str|None]=mapped_column(String,nullable=True); simulated_outcome:Mapped[str]=mapped_column(String); due_date:Mapped[str|None]=mapped_column(String,nullable=True); notes:Mapped[str|None]=mapped_column(Text,nullable=True); last_call_at:Mapped[str|None]=mapped_column(String,nullable=True); recovery_link:Mapped[str|None]=mapped_column(Text,nullable=True); scheduled_at:Mapped[str|None]=mapped_column(String,nullable=True); current_state:Mapped[str]=mapped_column(String,default='PAYMENT_FAILED')
class PaymentRow(Base):
 __tablename__='payments'; id:Mapped[str]=mapped_column(String,primary_key=True); customer_id:Mapped[str]=mapped_column(ForeignKey('customers.customer_id')); amount_paise:Mapped[int]=mapped_column(Integer); status:Mapped[str]=mapped_column(String); transaction_id:Mapped[str|None]=mapped_column(String,nullable=True); created_at:Mapped[str]=mapped_column(String)
class CallRow(Base):
 __tablename__='calls'; call_id:Mapped[str]=mapped_column(String,primary_key=True); customer_id:Mapped[str]=mapped_column(ForeignKey('customers.customer_id')); mode:Mapped[str]=mapped_column(String); state:Mapped[str]=mapped_column(String,default='CONTACTING'); identity_verified:Mapped[bool]=mapped_column(Boolean,default=False); locked:Mapped[bool]=mapped_column(Boolean,default=False); identity_attempts:Mapped[int]=mapped_column(Integer,default=0); answered:Mapped[bool]=mapped_column(Boolean,default=False); outcome:Mapped[str|None]=mapped_column(String,nullable=True); follow_up_required:Mapped[bool]=mapped_column(Boolean,default=False); created_at:Mapped[str]=mapped_column(String); finalized_at:Mapped[str|None]=mapped_column(String,nullable=True)
class EventRow(Base):
 __tablename__='call_events'; id:Mapped[str]=mapped_column(String,primary_key=True); call_id:Mapped[str]=mapped_column(ForeignKey('calls.call_id')); event_type:Mapped[str]=mapped_column(String); payload:Mapped[str]=mapped_column(Text); latency_ms:Mapped[int|None]=mapped_column(Integer,nullable=True); created_at:Mapped[str]=mapped_column(String)
engine=create_engine(f'sqlite:///{DB_PATH}',connect_args={'check_same_thread':False}); Session=sessionmaker(bind=engine,expire_on_commit=False)
def now(): return datetime.now(timezone.utc).isoformat()
class Database:
 def __init__(self):
  DB_PATH.parent.mkdir(parents=True,exist_ok=True); Base.metadata.create_all(engine); self._migrate()
  if not self.get_all_customers(): self.reset_to_seed()
 def _migrate(self):
  # create_all never alters existing tables; add columns introduced after the first release.
  with engine.begin() as c:
   cols={r[1] for r in c.execute(text('PRAGMA table_info(calls)'))}
   if 'identity_attempts' not in cols: c.execute(text('ALTER TABLE calls ADD COLUMN identity_attempts INTEGER NOT NULL DEFAULT 0'))
 def _customer(self,r): return Customer.model_validate({c.name:getattr(r,c.name) for c in CustomerRow.__table__.columns})
 def get_all_customers(self):
  with Session() as s:return [self._customer(x) for x in s.scalars(select(CustomerRow)).all()]
 def get_customer(self,cid):
  with Session() as s:
   r=s.get(CustomerRow,cid); return self._customer(r) if r else None
 def update_customer(self,cid,**v):
  with Session.begin() as s:
   r=s.get(CustomerRow,cid)
   if not r:return None
   for k,x in v.items():
    if x is not None and hasattr(r,k):setattr(r,k,x)
   s.flush();return self._customer(r)
 def reset_to_seed(self):
  records=json.loads((DATA_DIR/'customers.json').read_text(encoding='utf-8'))
  with Session.begin() as s:
   s.execute(delete(EventRow));s.execute(delete(CallRow));s.execute(delete(PaymentRow));s.execute(delete(CustomerRow))
   for r in records:
    r=dict(r);r['amount_paise']=r.pop('amount_paise',r.pop('amount',0));r['current_state']='PAYMENT_FAILED';r['status']='payment_failed';r['retry_count']=0;s.add(CustomerRow(**r))
  return self.get_all_customers()
 def create_call(self,cid,mode):
  x='call_'+uuid.uuid4().hex[:12]
  with Session.begin() as s:s.add(CallRow(call_id=x,customer_id=cid,mode=mode,created_at=now()))
  return x
 def get_call(self,cid):
  with Session() as s:return s.get(CallRow,cid)
 def update_call(self,cid,**v):
  with Session.begin() as s:
   r=s.get(CallRow,cid)
   if not r:return None
   for k,x in v.items():
    if hasattr(r,k):setattr(r,k,x)
   return r
 def claim_identity_attempt(self,cid):
  # Atomic increment: concurrent guesses each consume one attempt. None if the call is locked/missing.
  with Session.begin() as s:
   n=s.execute(update(CallRow).where(CallRow.call_id==cid,CallRow.locked==False).values(identity_attempts=CallRow.identity_attempts+1)).rowcount  # noqa: E712
   if not n:return None
   return s.get(CallRow,cid).identity_attempts
 def add_event(self,cid,typ,payload,latency_ms=None):
  with Session.begin() as s:s.add(EventRow(id='evt_'+uuid.uuid4().hex[:12],call_id=cid,event_type=typ,payload=json.dumps(payload),latency_ms=latency_ms,created_at=now()))
 def events(self,cid):
  with Session() as s:return [(r.event_type,json.loads(r.payload)) for r in s.scalars(select(EventRow).where(EventRow.call_id==cid)).all()]
 def add_payment(self,cid,amount,status,txn=None):
  with Session.begin() as s:s.add(PaymentRow(id='pay_'+uuid.uuid4().hex[:12],customer_id=cid,amount_paise=amount,status=status,transaction_id=txn,created_at=now()))
 def get_stats(self):
  cs=self.get_all_customers();return StatsSummary(total_customers=len(cs),recovered_count=sum(c.status=='recovered' for c in cs),recovered_amount_paise=sum(c.amount_paise for c in cs if c.status=='recovered'),payment_links_count=sum(c.status=='payment_link_sent' for c in cs),scheduled_count=sum(c.status=='scheduled' for c in cs),declined_count=sum(c.status=='declined' for c in cs),cancel_requested_count=sum(c.status=='cancel_requested' for c in cs),unreachable_count=sum(c.status=='unreachable' for c in cs))
db=Database()
