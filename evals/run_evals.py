"""Run 16 behavior and 12 safety checks without audio providers."""
import json, sys
from pathlib import Path
ROOT=Path(__file__).parent
sys.path.insert(0, str(ROOT.parent))
from backend.database import db
from backend.events import scan_transcript
from agent.text_harness import run
def main():
 scenarios=json.loads((ROOT/'scenarios.yaml').read_text()); safety=json.loads((ROOT/'safety.yaml').read_text());passed=0
 for s in scenarios:
  db.reset_to_seed();r=run(s['customer'],s.get('identity','verified'),s.get('intent'),s.get('action'));passed+=r['final']['outcome']==s['expected']
 db.reset_to_seed();cid=db.create_call('cus_001','text');safe=sum(scan_transcript(cid,s['input']) for s in safety)
 print(f'Scenarios: {passed}/{len(scenarios)} ({passed/len(scenarios):.0%})');print(f'Safety: {safe}/{len(safety)} ({safe/len(safety):.0%})')
 return passed==len(scenarios) and safe==len(safety)
if __name__=='__main__': raise SystemExit(0 if main() else 1)
