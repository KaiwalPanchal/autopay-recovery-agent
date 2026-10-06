"""Append-only event logging plus post-call sensitive-data detection."""
import re
from .database import db
SENSITIVE_PATTERNS=(re.compile(r'\b(?:\d[ -]?){13,19}\b'),re.compile(r'\b(?:cvv|cvc|otp|pin)\s*[:=]?\s*\d{3,6}\b',re.I),re.compile(r'\b(?:bank\s+)?password\b',re.I))
def log_event(call_id,event_type,payload,latency_ms=None): db.add_event(call_id,event_type,payload,latency_ms)
def scan_transcript(call_id,text):
 flagged=any(p.search(text) for p in SENSITIVE_PATTERNS)
 if flagged: db.add_event(call_id,'SENSITIVE_DATA_FLAG',{'redacted':True})
 return flagged
