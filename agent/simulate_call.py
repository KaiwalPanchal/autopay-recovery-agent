"""Interactive & Scripted Conversation Simulation Runner.

Enables immediate verification of the 5 recovery conversation branches
without needing a live SIP trunk or active LiveKit server.
"""

import argparse
import sys
import time
from typing import Dict, Any, List

if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
if sys.stderr and hasattr(sys.stderr, "reconfigure"):
    try:
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
from backend.database import db
from backend.models import RecoveryStateEnum, CustomerStatusEnum
from backend.recovery import recovery_machine
from backend.payments import payment_service
from agent.prompts import get_system_prompt
from agent.state import AgentCallState


def run_scenario(customer_id: str, scenario_type: str) -> Dict[str, Any]:
    """Executes a complete simulated conversation branch, exercising state machine and tools."""
    customer = db.get_customer(customer_id)
    if not customer:
        print(f"❌ Customer {customer_id} not found.")
        return {}

    state = AgentCallState(customer_id=customer.customer_id, customer_name=customer.name)
    currency_symbol = "₹" if customer.currency == "INR" else "$"
    amount_inr = customer.amount_paise / 100.0
    formatted_amount = f"{currency_symbol}{amount_inr:,.2f}"

    print("\n" + "=" * 70)
    print(f"📞 OUTBOUND CALL INITIATED -> {customer.name} [Account: {customer.customer_id}]")
    print(f"💼 Plan: {customer.subscription} | Amount: {formatted_amount} | Reason: {customer.failure_reason}")
    print(f"🎭 Scenario: {scenario_type.upper()}")
    print("=" * 70)

    # 1. State: PAYMENT_FAILED -> CONTACTING
    recovery_machine.transition(customer.customer_id, RecoveryStateEnum.CONTACTING.value)
    state.current_state = RecoveryStateEnum.CONTACTING.value

    # Opening Verification
    agent_opening = (
        f"Hi, is this {customer.name}? I'm an automated payment assistant calling on behalf "
        f"of Apex Cloud. I'm calling because a recent payment of {formatted_amount} "
        f"didn't go through. Is now a good time to help get that sorted?"
    )
    print(f"\n🤖 AGENT: \"{agent_opening}\"")
    state.add_transcript("Agent", agent_opening)

    if scenario_type == "retry":
        # Customer confirms and requests retry
        cust_msg = "Yes, speaking. Yeah, my salary just arrived today, go ahead and try the payment again."
        print(f"👤 CUSTOMER: \"{cust_msg}\"")
        state.add_transcript("Customer", cust_msg)
        state.verified_customer = True

        # State transition: CUSTOMER_VERIFIED -> PAY_NOW
        recovery_machine.transition(customer.customer_id, RecoveryStateEnum.CUSTOMER_VERIFIED.value)
        recovery_machine.transition(customer.customer_id, RecoveryStateEnum.PAY_NOW.value)
        state.intent_detected = "pay_now"

        agent_ack = "Sure. I'll attempt that charge against your card on file right now."
        print(f"\n🤖 AGENT: \"{agent_ack}\"")
        state.add_transcript("Agent", agent_ack)

        # Tool Invocation
        print(f"\n⚙️  [TOOL INVOKED] retry_payment('{customer.customer_id}')")
        retry_res = payment_service.retry_payment(customer.customer_id).model_dump()
        state.record_action("retry_payment", retry_res)
        print(f"📥 [BACKEND RESPONSE] Status: {retry_res.get('status')} | Txn: {retry_res.get('transaction_id')}")

        if retry_res.get("status") == "SUCCESS":
            agent_closing = f"Great, that payment went through successfully! Your account is completely up to date. Thank you for your time, {customer.name}."
            print(f"\n🤖 AGENT: \"{agent_closing}\"")
            state.add_transcript("Agent", agent_closing)
            outcome = state.finalize(
                outcome="recovered",
                action="retry_payment",
                intent="pay_now",
                notes="Customer confirmed payment retry. Transaction settled successfully.",
                amount_recovered=amount_inr,
            )

        elif retry_res.get("status") in {"CARD_EXPIRED", "FAILED", "BANK_DECLINED"}:
            agent_fail = "It looks like the bank declined that attempt. Would you like me to send a secure link so you can update your payment method?"
            print(f"\n🤖 AGENT: \"{agent_fail}\"")
            state.add_transcript("Agent", agent_fail)

    elif scenario_type == "expired" or scenario_type == "payment_link":
        cust_msg = "Hi, yes. My old credit card expired last month and I got a replacement."
        print(f"👤 CUSTOMER: \"{cust_msg}\"")
        state.add_transcript("Customer", cust_msg)
        state.verified_customer = True

        recovery_machine.transition(customer.customer_id, RecoveryStateEnum.CUSTOMER_VERIFIED.value)
        state.intent_detected = "update_payment_method"

        agent_ack = "No problem at all. For your security, I will not take card details over the phone. I'm sending a secure payment link to your registered contact on file."
        print(f"\n🤖 AGENT: \"{agent_ack}\"")
        state.add_transcript("Agent", agent_ack)

        print(f"\n⚙️  [TOOL INVOKED] generate_payment_link('{customer.customer_id}')")
        link_res = payment_service.generate_payment_link(customer.customer_id).model_dump()
        state.record_action("generate_payment_link", link_res)
        print(f"📥 [BACKEND RESPONSE] Link: {link_res.get('payment_link')}")

        agent_closing = "The link has been sent. You can update your payment method whenever convenient today. Have a great day!"
        print(f"\n🤖 AGENT: \"{agent_closing}\"")
        state.add_transcript("Agent", agent_closing)

        outcome = state.finalize(
            outcome="payment_link_sent",
            action="generate_payment_link",
            intent="update_payment_method",
            notes=f"Sent self-serve payment link: {link_res.get('payment_link')}",
            amount_recovered=0.0,
        )

    elif scenario_type == "later" or scenario_type == "schedule":
        cust_msg = "Yes, it's Maya. I'm in the middle of a meeting right now. Can you call me back on Friday afternoon?"
        print(f"👤 CUSTOMER: \"{cust_msg}\"")
        state.add_transcript("Customer", cust_msg)
        state.verified_customer = True

        recovery_machine.transition(customer.customer_id, RecoveryStateEnum.CUSTOMER_VERIFIED.value)
        recovery_machine.transition(customer.customer_id, RecoveryStateEnum.PAY_LATER.value)
        state.intent_detected = "pay_later"

        agent_ack = "Understood. I will schedule a callback for this Friday at 3:00 PM."
        print(f"\n🤖 AGENT: \"{agent_ack}\"")
        state.add_transcript("Agent", agent_ack)

        print(f"\n⚙️  [TOOL INVOKED] schedule_retry('{customer.customer_id}', scheduled_time='2026-10-09T15:00:00Z')")
        sched_res = payment_service.schedule_retry(customer.customer_id, "2026-10-09T15:00:00Z", "Friday 3 PM meeting").model_dump()
        state.record_action("schedule_retry", sched_res)
        print(f"📥 [BACKEND RESPONSE] Status: {sched_res.get('status')}")

        agent_closing = "All set. I've noted that on your account. Have a productive meeting!"
        print(f"\n🤖 AGENT: \"{agent_closing}\"")
        state.add_transcript("Agent", agent_closing)

        outcome = state.finalize(
            outcome="scheduled",
            action="schedule_retry",
            intent="pay_later",
            notes="Customer requested callback Friday afternoon",
        )

    elif scenario_type == "cancel":
        cust_msg = "Yeah, hi. I actually don't want this subscription anymore. Please cancel my account."
        print(f"👤 CUSTOMER: \"{cust_msg}\"")
        state.add_transcript("Customer", cust_msg)
        state.verified_customer = True

        recovery_machine.transition(customer.customer_id, RecoveryStateEnum.CUSTOMER_VERIFIED.value)
        recovery_machine.transition(customer.customer_id, RecoveryStateEnum.CANCEL.value)
        recovery_machine.transition(customer.customer_id, RecoveryStateEnum.CANCEL_REQUESTED.value)
        state.intent_detected = "cancel"

        agent_closing = "I completely understand. I have recorded your cancellation request and stopped all further payment attempts. Thank you for using Apex Cloud, and have a good day."
        print(f"\n🤖 AGENT: \"{agent_closing}\"")
        state.add_transcript("Agent", agent_closing)

        print(f"\n⚙️  [TOOL INVOKED] cancel_subscription('{customer.customer_id}')")
        outcome = state.finalize(
            outcome="cancel_requested",
            action="cancel_subscription",
            intent="cancel",
            notes="Customer expressed explicit desire to cancel subscription. Recovery halted.",
        )

    elif scenario_type == "decline":
        cust_msg = "No, I'm not interested in this. Stop calling."
        print(f"👤 CUSTOMER: \"{cust_msg}\"")
        state.add_transcript("Customer", cust_msg)

        recovery_machine.transition(customer.customer_id, RecoveryStateEnum.CUSTOMER_VERIFIED.value)
        recovery_machine.transition(customer.customer_id, RecoveryStateEnum.DECLINED.value)
        state.intent_detected = "decline"

        agent_closing = "Understood. I apologize for the interruption. We have removed you from the recovery calling list. Have a good day."
        print(f"\n🤖 AGENT: \"{agent_closing}\"")
        state.add_transcript("Agent", agent_closing)

        print(f"\n⚙️  [TOOL INVOKED] polite_hangup('{customer.customer_id}')")
        outcome = state.finalize(
            outcome="declined",
            action="polite_hangup",
            intent="decline",
            notes="Customer declined and requested no further calls.",
        )

    print("\n" + "=" * 70)
    print("📊 CALL COMPLETED - STRUCTURED OUTCOME RECORD:")
    print(f"Customer:    {customer.name} ({customer.customer_id})")
    print(f"Outcome:     {state.final_outcome.outcome.upper()}")
    print(f"Action:      {state.final_outcome.action}")
    print(f"Intent:      {state.final_outcome.customer_intent}")
    print(f"Recovered:   {currency_symbol}{state.final_outcome.amount_recovered:,.2f}")
    print(f"Duration:    {state.final_outcome.call_duration_seconds}s")
    print(f"New DB State:{db.get_customer(customer.customer_id).status}")
    print("=" * 70 + "\n")

    return state.final_outcome.model_dump()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Simulate Autopay Recovery Voice Conversation")
    parser.add_argument("--customer", default="cus_001", help="Customer ID (e.g. cus_001, cus_002)")
    parser.add_argument(
        "--scenario",
        default="retry",
        choices=["retry", "expired", "payment_link", "later", "schedule", "cancel", "decline"],
        help="Conversation scenario branch to simulate",
    )
    args = parser.parse_args()
    run_scenario(args.customer, args.scenario)
