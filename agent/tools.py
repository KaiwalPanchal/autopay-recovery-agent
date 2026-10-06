"""Session-bound agent tools: LLM schemas never include customer IDs."""
import os, httpx
BACKEND_API_URL=os.getenv('BACKEND_API_URL','http://127.0.0.1:8000'); TOKEN=os.getenv('INTERNAL_API_TOKEN','dev-internal-token')
class RecoveryAgentTools:
 def __init__(self,call_id,base_url=BACKEND_API_URL,token=TOKEN):self.call_id=call_id;self.base_url=base_url;self.headers={'Authorization':f'Bearer {token}'}
 def _call(self,method,path,body=None):
  with httpx.Client(base_url=self.base_url,headers=self.headers,timeout=8) as c:
   r=c.request(method,f'/internal/calls/{self.call_id}/{path}',json=body);return r.json()
 def verify_identity(self,result):return self._call('POST','identity',{'result':result})
 def record_intent(self,intent):return self._call('POST','intent',{'intent':intent})
 def get_payment_details(self):return self._call('GET','payment')
 def retry_payment(self):return self._call('POST','retry')
 def generate_payment_link(self):return self._call('POST','payment-link')
 def schedule_retry(self,scheduled_time,notes=''):return self._call('POST','schedule',{'scheduled_time':scheduled_time,'notes':notes})
 def finalize(self):return self._call('POST','finalize')
def create_livekit_function_context(call_id):
 try:
  from livekit.agents import llm
  tools=RecoveryAgentTools(call_id)
  if hasattr(llm, 'function_tool'):
   @llm.function_tool(description='Record identity verification result.')
   def verify_identity(result:str)->dict: return tools.verify_identity(result)
   @llm.function_tool(description='Fetch payment facts after verification.')
   def get_payment_details()->dict: return tools.get_payment_details()
   @llm.function_tool(description='Retry the method on file after consent.')
   def retry_payment()->dict: return tools.retry_payment()
   @llm.function_tool(description='Generate a secure payment link.')
   def generate_payment_link()->dict: return tools.generate_payment_link()
   @llm.function_tool(description='Schedule a future retry.')
   def schedule_retry(scheduled_time:str,notes:str='')->dict: return tools.schedule_retry(scheduled_time,notes)
   @llm.function_tool(description='Record an intent, including decline or cancel_subscription.')
   def record_intent(intent:str)->dict: return tools.record_intent(intent)
   return [verify_identity, get_payment_details, retry_payment, generate_payment_link, schedule_retry, record_intent]
  elif hasattr(llm, 'FunctionContext'):
   class BoundTools(llm.FunctionContext):
    @llm.ai_callable(description='Record identity verification result.')
    def verify_identity(self,result:str)->dict:return tools.verify_identity(result)
    @llm.ai_callable(description='Fetch payment facts after verification.')
    def get_payment_details(self)->dict:return tools.get_payment_details()
    @llm.ai_callable(description='Retry the method on file after consent.')
    def retry_payment(self)->dict:return tools.retry_payment()
    @llm.ai_callable(description='Generate a secure payment link.')
    def generate_payment_link(self)->dict:return tools.generate_payment_link()
    @llm.ai_callable(description='Schedule a future retry.')
    def schedule_retry(self,scheduled_time:str,notes:str='')->dict:return tools.schedule_retry(scheduled_time,notes)
    @llm.ai_callable(description='Record an intent, including decline or cancel_subscription.')
    def record_intent(self,intent:str)->dict:return tools.record_intent(intent)
   return BoundTools()
  return tools
 except Exception:
  return None
