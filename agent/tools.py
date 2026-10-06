"""Session-bound agent tools: LLM schemas never include customer IDs."""
import os, httpx
from typing import Literal
BACKEND_API_URL=os.getenv('BACKEND_API_URL','http://127.0.0.1:8000')
class RecoveryAgentTools:
 def __init__(self,call_id,base_url=None,token=None):
  token=token or os.getenv('INTERNAL_API_TOKEN')
  if not token:raise RuntimeError('INTERNAL_API_TOKEN must be set; there is no default token.')
  self.call_id=call_id;self.base_url=base_url or os.getenv('BACKEND_API_URL',BACKEND_API_URL);self.headers={'Authorization':f'Bearer {token}'}
 def _call(self,method,path,body=None):
  with httpx.Client(base_url=self.base_url,headers=self.headers,timeout=8) as c:
   r=c.request(method,f'/internal/calls/{self.call_id}'+(f'/{path}' if path else ''),json=body);return r.json()
 def context(self):return self._call('GET','')
 def check_identity(self,answer):return self._call('POST','identity',{'result':'challenge_answer','answer':answer})
 def wrong_person(self):return self._call('POST','identity',{'result':'wrong_person'})
 def record_transcript(self,speaker,text):return self._call('POST','transcript',{'speaker':speaker,'text':text[:4000]})
 def record_intent(self,intent):return self._call('POST','intent',{'intent':intent})
 def get_payment_details(self):return self._call('GET','payment')
 def retry_payment(self):return self._call('POST','retry')
 def generate_payment_link(self):return self._call('POST','payment-link')
 def schedule_retry(self,scheduled_time,notes=''):return self._call('POST','schedule',{'scheduled_time':scheduled_time,'notes':notes})
 def finalize(self):return self._call('POST','finalize')
def create_livekit_function_context(call_id):
 tools=RecoveryAgentTools(call_id)  # raises if INTERNAL_API_TOKEN is missing; must not be swallowed below
 try:
  from livekit.agents import llm
  if hasattr(llm, 'function_tool'):
   @llm.function_tool(description='Submit the customer answer to the identity challenge: the last 4 digits of the card on file. The backend decides whether it matches.')
   def check_identity(answer:str)->dict: return tools.check_identity(answer)
   @llm.function_tool(description='Call this if the person says they are not the account holder.')
   def wrong_person()->dict: return tools.wrong_person()
   @llm.function_tool(description='Fetch payment facts after verification.')
   def get_payment_details()->dict: return tools.get_payment_details()
   @llm.function_tool(description='Retry the method on file after consent.')
   def retry_payment()->dict: return tools.retry_payment()
   @llm.function_tool(description='Generate a secure payment link.')
   def generate_payment_link()->dict: return tools.generate_payment_link()
   @llm.function_tool(description='Schedule a future retry.')
   def schedule_retry(scheduled_time:str,notes:str='')->dict: return tools.schedule_retry(scheduled_time,notes)
   @llm.function_tool(description='Record an intent: pay_now, pay_later, cancel_subscription, decline, request_human or dispute_amount.')
   def record_intent(intent:Literal['pay_now','pay_later','cancel_subscription','decline','request_human','dispute_amount'])->dict: return tools.record_intent(intent)
   return [check_identity, wrong_person, get_payment_details, retry_payment, generate_payment_link, schedule_retry, record_intent]
  elif hasattr(llm, 'FunctionContext'):
   class BoundTools(llm.FunctionContext):
    @llm.ai_callable(description='Submit the customer answer to the identity challenge: last 4 digits of the card on file.')
    def check_identity(self,answer:str)->dict:return tools.check_identity(answer)
    @llm.ai_callable(description='Call this if the person says they are not the account holder.')
    def wrong_person(self)->dict:return tools.wrong_person()
    @llm.ai_callable(description='Fetch payment facts after verification.')
    def get_payment_details(self)->dict:return tools.get_payment_details()
    @llm.ai_callable(description='Retry the method on file after consent.')
    def retry_payment(self)->dict:return tools.retry_payment()
    @llm.ai_callable(description='Generate a secure payment link.')
    def generate_payment_link(self)->dict:return tools.generate_payment_link()
    @llm.ai_callable(description='Schedule a future retry.')
    def schedule_retry(self,scheduled_time:str,notes:str='')->dict:return tools.schedule_retry(scheduled_time,notes)
    @llm.ai_callable(description='Record an intent: pay_now, pay_later, cancel_subscription, decline, request_human or dispute_amount.')
    def record_intent(self,intent:Literal['pay_now','pay_later','cancel_subscription','decline','request_human','dispute_amount'])->dict:return tools.record_intent(intent)
   return BoundTools()
  return tools
 except Exception:
  return None
