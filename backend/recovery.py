"""Call guards, identity verification and deterministic outcome derivation.

Everything that authorizes an action lives here, not in the LLM. Locks are
one-way: once a call is locked (wrong person, cancel/decline, identity
lock-out) nothing in this module unlocks it.
"""
import hmac
from .database import db, now

MAX_IDENTITY_ATTEMPTS = 3
LOCKING_INTENTS = {'cancel_subscription', 'decline'}
PAYMENT_ACTIONS = {'payment_details', 'retry_payment', 'generate_payment_link', 'schedule_retry'}
# Customer record to leave behind per outcome. Outcomes not listed leave the status alone
# (RECOVERED / PAYMENT_LINK_SENT / SCHEDULED were already written by the payment service).
_OUTCOME_STATUS = {
    'CANCEL_REQUESTED': ('cancel_requested', 'CANCEL_REQUESTED'),
    'DECLINED': ('declined', 'DECLINED'),
    'UNREACHABLE': ('unreachable', 'UNREACHABLE'),
}
_BACK_TO_QUEUE = {'WRONG_PERSON', 'IDENTITY_FAILED', 'HUMAN_HANDOFF_REQUESTED', 'FAILED'}


class RecoveryStateMachine:
    def transition(self, cid, new_state, notes=None):
        """Customer-level state change. Used by the simulate_call CLI; the live HTTP path
        records state through the payment service and finalize() instead."""
        c = db.get_customer(cid)
        if not c:
            return False, 'Customer not found.'
        allowed = {'PAYMENT_FAILED': {'CONTACTING'}, 'CONTACTING': {'CUSTOMER_VERIFIED', 'UNREACHABLE'},
                   'CUSTOMER_VERIFIED': {'PAY_NOW', 'PAY_LATER', 'CANCEL', 'DECLINED'},
                   'PAY_NOW': {'RECOVERED', 'PAYMENT_LINK_SENT', 'FAILED', 'DECLINED'},
                   'PAY_LATER': {'SCHEDULED', 'PAYMENT_LINK_SENT', 'DECLINED'}, 'CANCEL': {'CANCEL_REQUESTED'}}
        if new_state != c.current_state and new_state not in allowed.get(c.current_state, set()):
            return False, f"Invalid transition: cannot move from '{c.current_state}' to '{new_state}'."
        status = {'RECOVERED': 'recovered', 'PAYMENT_LINK_SENT': 'payment_link_sent', 'SCHEDULED': 'scheduled',
                  'CANCEL_REQUESTED': 'cancel_requested', 'DECLINED': 'declined',
                  'UNREACHABLE': 'unreachable'}.get(new_state, 'in_progress' if new_state not in {'PAYMENT_FAILED', 'FAILED'} else 'payment_failed')
        db.update_customer(cid, current_state=new_state, status=status, notes=notes)
        return True, f'Customer transitioned to {new_state}.'

    def guard(self, call, action):
        if call.locked:
            return 'CALL_LOCKED'
        if call.finalized_at:
            return 'CALL_FINALIZED'
        if action in PAYMENT_ACTIONS and not call.identity_verified:
            return 'IDENTITY_NOT_VERIFIED'
        c = db.get_customer(call.customer_id)
        if c is None:
            return 'CUSTOMER_NOT_FOUND'
        if action == 'retry_payment' and c.simulated_outcome in {'CARD_EXPIRED', 'NEEDS_PAYMENT_METHOD'}:
            return 'NOT_RETRYABLE'
        if action == 'retry_payment' and c.retry_count >= 2:
            return 'RETRY_LIMIT_REACHED'
        return None

    # ---- identity -------------------------------------------------------------------
    def mark_wrong_person(self, cid):
        db.update_call(cid, answered=True, locked=True)
        db.add_event(cid, 'wrong_person', {'result': 'wrong_person'})

    def verify_identity(self, cid, answer):
        """Check the customer's answer (last 4 of the card on file) against seed data.

        Returns (code, data). Attempts are counted atomically *before* comparing, so
        concurrent guesses cannot exceed MAX_IDENTITY_ATTEMPTS comparisons. The answer
        itself is never written to the event log.
        """
        call = db.get_call(cid)
        if call.identity_verified:
            return 'OK', {'identity_verified': True}
        attempt = db.claim_identity_attempt(cid)
        if attempt is None or attempt > MAX_IDENTITY_ATTEMPTS:
            return 'CALL_LOCKED', {'identity_verified': False}
        customer = db.get_customer(call.customer_id)
        expected = (customer.card_last4 or '') if customer else ''
        matched = bool(expected) and hmac.compare_digest(answer.encode(), expected.encode())
        db.update_call(cid, answered=True)
        if matched:
            db.update_call(cid, identity_verified=True)
            db.add_event(cid, 'identity', {'result': 'challenge_answer', 'matched': True, 'attempt': attempt})
            return 'OK', {'identity_verified': True}
        remaining = MAX_IDENTITY_ATTEMPTS - attempt
        db.add_event(cid, 'identity', {'result': 'challenge_answer', 'matched': False, 'attempt': attempt})
        if remaining <= 0:
            db.update_call(cid, locked=True)
            db.add_event(cid, 'identity_lockout', {'attempts': attempt})
            return 'IDENTITY_LOCKED', {'identity_verified': False, 'attempts_remaining': 0}
        return 'IDENTITY_MISMATCH', {'identity_verified': False, 'attempts_remaining': remaining}

    def record_intent(self, cid, intent):
        if intent in LOCKING_INTENTS:
            db.update_call(cid, locked=True)  # never set back to False
        db.add_event(cid, 'INTENT', {'intent': intent})

    # ---- outcome --------------------------------------------------------------------
    def finalize(self, call_id):
        call = db.get_call(call_id)
        if not call:
            return None
        events = db.events(call_id)
        types = [x[0] for x in events]
        intents = [p.get('intent') for t, p in events if t == 'INTENT']
        c = db.get_customer(call.customer_id)
        if c.status == 'recovered':
            out, follow = 'RECOVERED', False
        elif 'cancel_subscription' in intents:
            out, follow = 'CANCEL_REQUESTED', True
        elif 'decline' in intents:
            out, follow = 'DECLINED', False
        elif 'wrong_person' in types:
            out, follow = 'WRONG_PERSON', True
        elif 'identity_lockout' in types:
            out, follow = 'IDENTITY_FAILED', True
        elif any(i in {'request_human', 'dispute_amount'} for i in intents):
            out, follow = 'HUMAN_HANDOFF_REQUESTED', True
        elif 'payment_link' in types:
            out, follow = 'PAYMENT_LINK_SENT', True
        elif 'schedule_retry' in types:
            out, follow = 'SCHEDULED', True
        elif not call.answered or 'voicemail' in types:
            out, follow = 'UNREACHABLE', True
        else:
            out, follow = 'FAILED', True
        if out in _OUTCOME_STATUS:
            status, state = _OUTCOME_STATUS[out]
            db.update_customer(call.customer_id, status=status, current_state=state)
        elif out in _BACK_TO_QUEUE and c.status == 'in_progress':
            db.update_customer(call.customer_id, status='payment_failed', current_state='PAYMENT_FAILED')
        db.update_call(call_id, outcome=out, follow_up_required=follow, finalized_at=call.finalized_at or now())
        return {'outcome': out, 'follow_up_required': follow, 'customer_id': call.customer_id,
                'sensitive_data_flagged': 'SENSITIVE_DATA_FLAG' in types}


recovery_machine = RecoveryStateMachine()
