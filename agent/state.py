"""Call session state tracking for LiveKit Voice Agent."""

from datetime import datetime, timezone
from typing import Dict, List, Any, Optional
from backend.models import RecoveryStateEnum, CallOutcome


class AgentCallState:
    """Encapsulates in-call state, detected intent, tool history, and transcript."""

    def __init__(self, customer_id: str, customer_name: str = ""):
        self.customer_id = customer_id
        self.customer_name = customer_name
        self.verified_customer: bool = False
        self.current_state: str = RecoveryStateEnum.CONTACTING.value
        self.intent_detected: Optional[str] = None
        self.actions_taken: List[Dict[str, Any]] = []
        self.start_time: datetime = datetime.now(timezone.utc)
        self.end_time: Optional[datetime] = None
        self.transcript: List[Dict[str, str]] = []
        self.outcome_logged: bool = False
        self.final_outcome: Optional[CallOutcome] = None

    def add_transcript(self, speaker: str, text: str):
        self.transcript.append({
            "speaker": speaker,
            "text": text,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })

    def record_action(self, action_name: str, result: Any):
        self.actions_taken.append({
            "action": action_name,
            "result": result,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })

    @property
    def duration_seconds(self) -> int:
        current = self.end_time or datetime.now(timezone.utc)
        return int((current - self.start_time).total_seconds())

    def finalize(self, outcome: str, action: str, intent: str, notes: str = "", amount_recovered: float = 0.0, amount_recovered_paise: int = 0) -> CallOutcome:
        self.end_time = datetime.now(timezone.utc)
        self.outcome_logged = True
        paise = amount_recovered_paise if amount_recovered_paise else int(amount_recovered * 100)
        self.final_outcome = CallOutcome(
            customer_id=self.customer_id,
            customer_name=self.customer_name,
            outcome=outcome,
            amount_recovered_paise=paise,
            action=action,
            customer_intent=intent,
            follow_up_required=outcome in {"scheduled", "payment_link_sent"},
            call_duration_seconds=self.duration_seconds,
            notes=notes,
            transcript=self.transcript,
        )
        return self.final_outcome
