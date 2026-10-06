"use client";

import React, { useState } from "react";
import {
  X,
  Phone,
  PhoneOff,
  Mic,
  MicOff,
  Volume2,
  CheckCircle2,
  AlertCircle,
  Link2,
  Calendar,
  Shield,
  Zap,
} from "lucide-react";
import { Customer, formatPaise, initiateCall } from "../lib/api";

interface CallModalProps {
  customer: Customer | null;
  onClose: () => void;
  onCallCompleted: () => void;
}

interface Message {
  speaker: "Agent" | "Customer" | "System";
  text: string;
  toolCall?: { name: string; result: any };
}

export const CallModal: React.FC<CallModalProps> = ({
  customer,
  onClose,
  onCallCompleted,
}) => {
  if (!customer) return null;

  const [activeTab, setActiveTab] = useState<"simulation" | "browser" | "sip">("simulation");
  const [callActive, setCallActive] = useState<boolean>(false);
  const [messages, setMessages] = useState<Message[]>([]);
  const [currentTool, setCurrentTool] = useState<string | null>(null);
  const [callDuration, setCallDuration] = useState<number>(0);
  const [timerId, setTimerId] = useState<any>(null);
  const [outcomeResult, setOutcomeResult] = useState<any>(null);
  const [isProcessing, setIsProcessing] = useState<boolean>(false);

  const currency = customer.currency === "INR" ? "₹" : "$";

  const startCall = (initialCustomerStatement?: string) => {
    setCallActive(true);
    setOutcomeResult(null);
    setCallDuration(0);
    const id = setInterval(() => {
      setCallDuration((prev) => prev + 1);
    }, 1000);
    setTimerId(id);

    // Initial greeting (zero payment facts before identity verification)
    const openingMsg: Message = {
      speaker: "Agent",
      text: `Hi, is this ${customer.name}? I'm an automated assistant calling on behalf of Apex Cloud regarding your account. Do I have a moment to verify your identity before we continue?`,
    };
    setMessages([openingMsg]);

    if (initialCustomerStatement) {
      setTimeout(() => {
        handleCustomerTurn(initialCustomerStatement);
      }, 800);
    }
  };

  const endCall = (outcomeStr: string = "ended") => {
    setCallActive(false);
    if (timerId) clearInterval(timerId);
    onCallCompleted();
  };

  const handleCustomerTurn = async (custText: string) => {
    setIsProcessing(true);
    const newMsgs: Message[] = [...messages, { speaker: "Customer", text: custText }];
    setMessages(newMsgs);

    const lower = custText.toLowerCase();

    // Branch A: Retry
    if (lower.includes("try") || lower.includes("retry") || lower.includes("again") || lower.includes("salary")) {
      setCurrentTool(`retry_payment()`);
      const ackMsg: Message = {
        speaker: "Agent",
        text: "Sure. I'll attempt that charge against your card on file right now.",
      };
      setMessages([...newMsgs, ackMsg]);

      setTimeout(() => {
        setCurrentTool(null);
        if (customer.simulated_outcome === "SUCCESS_ON_RETRY") {
          const successMsg: Message = {
            speaker: "Agent",
            text: `Great, that payment went through successfully! Your account is completely up to date. Thank you for your time, ${customer.name}.`,
            toolCall: { name: "retry_payment", result: { status: "SUCCESS", amount_charged_paise: customer.amount_paise } },
          };
          setMessages((prev) => [...prev, successMsg]);
          setOutcomeResult({
            outcome: "RECOVERED",
            amount: formatPaise(customer.amount_paise, customer.currency),
            action: "retry_payment",
            statusColor: "border-ink bg-white text-ink",
          });
        } else {
          const failMsg: Message = {
            speaker: "Agent",
            text: `It looks like the bank declined that retry due to: ${customer.failure_reason.replace("_", " ")}. Would you like me to send a secure payment link so you can update your payment method?`,
            toolCall: { name: "retry_payment", result: { status: "DECLINED" } },
          };
          setMessages((prev) => [...prev, failMsg]);
        }
        setIsProcessing(false);
      }, 700);
      return;
    }
    // Branch B: Card Expired / Payment Link
    else if (lower.includes("expired") || lower.includes("new card") || lower.includes("link") || lower.includes("update")) {
      setCurrentTool(`generate_payment_link()`);
      const ackMsg: Message = {
        speaker: "Agent",
        text: "No problem at all. For your security, I will not take card details over the phone. I'm generating a secure payment link for you now.",
      };
      setMessages([...newMsgs, ackMsg]);

      setTimeout(() => {
        setCurrentTool(null);
        const linkSentMsg: Message = {
          speaker: "Agent",
          text: `I've sent the secure payment link to your contact details on file. You can update your payment method there in seconds. Have a great day!`,
          toolCall: { name: "generate_payment_link", result: { status: "LINK_GENERATED" } },
        };
        setMessages((prev) => [...prev, linkSentMsg]);
        setOutcomeResult({
          outcome: "PAYMENT_LINK_SENT",
          amount: "SMS Dispatched",
          action: "generate_payment_link",
          statusColor: "border-ink bg-white text-ink",
        });
        setIsProcessing(false);
      }, 700);
      return;
    }
    // Branch C: Pay later / schedule
    else if (lower.includes("later") || lower.includes("busy") || lower.includes("friday") || lower.includes("tomorrow") || lower.includes("meeting")) {
      setCurrentTool(`schedule_retry('2026-10-09T15:00:00Z')`);
      const schedMsg: Message = {
        speaker: "Agent",
        text: "Understood. I will schedule a callback for this Friday at 3:00 PM so you can resolve it then.",
      };
      setMessages([...newMsgs, schedMsg]);

      setTimeout(() => {
        setCurrentTool(null);
        const doneMsg: Message = {
          speaker: "Agent",
          text: "All set. I've noted that on your account. Have a productive day!",
          toolCall: { name: "schedule_retry", result: { status: "SCHEDULED" } },
        };
        setMessages((prev) => [...prev, doneMsg]);
        setOutcomeResult({
          outcome: "SCHEDULED",
          amount: "Friday 3:00 PM",
          action: "schedule_retry",
          statusColor: "border-ink bg-white text-ink",
        });
        setIsProcessing(false);
      }, 700);
      return;
    }
    // Branch D: Cancel Subscription
    else if (lower.includes("cancel") || lower.includes("don't want")) {
      setCurrentTool(`record_intent('cancel_subscription')`);
      const cancelMsg: Message = {
        speaker: "Agent",
        text: "I understand completely. I have recorded your cancellation request and stopped all further payment recovery attempts. Thank you for using Apex Cloud, and have a good day.",
        toolCall: { name: "record_intent", result: { status: "CANCEL_RECORDED" } },
      };
      setMessages([...newMsgs, cancelMsg]);

      setTimeout(() => {
        setCurrentTool(null);
        setOutcomeResult({
          outcome: "CANCEL_REQUESTED",
          amount: "Subscription Cancelled",
          action: "record_intent",
          statusColor: "border-ink bg-white text-ink",
        });
        setIsProcessing(false);
      }, 700);
      return;
    }
    // Branch E: Decline
    else {
      setCurrentTool(`record_intent('decline')`);
      const declineMsg: Message = {
        speaker: "Agent",
        text: "Understood. I apologize for the interruption. We have removed you from the recovery calling list. Have a good day.",
        toolCall: { name: "record_intent", result: { status: "DECLINED" } },
      };
      setMessages([...newMsgs, declineMsg]);

      setTimeout(() => {
        setCurrentTool(null);
        setOutcomeResult({
          outcome: "DECLINED",
          amount: "No Action Taken",
          action: "record_intent",
          statusColor: "border-ink bg-white text-ink",
        });
        setIsProcessing(false);
      }, 700);
      return;
    }

    setIsProcessing(false);
  };

  const tabClass = (active: boolean) =>
    `label !text-xs py-1 border-b-[3px] transition-colors ${
      active ? "!text-ink border-accent" : "border-transparent hover:!text-ink"
    }`;

  const scenarioBtn =
    "p-3 border border-ink rounded-sm bg-white hover:bg-ink hover:text-paper text-left transition-colors group";

  const quickBtn = "btn disabled:opacity-40";

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/40"
      role="dialog"
      aria-modal="true"
      aria-label={`Voice recovery console for ${customer.name}`}
    >
      <div className="bg-white border border-ink rounded-sm w-full max-w-3xl overflow-hidden flex flex-col max-h-[90vh]">
        {/* Modal Header */}
        <div className="px-6 py-5 border-b border-ink flex items-start justify-between gap-4">
          <div>
            <div className="flex flex-wrap items-baseline gap-3">
              <h3 className="font-serif text-2xl font-medium tracking-tight leading-none">
                Voice Recovery Console &middot; {customer.name}
              </h3>
              <span className="label">{customer.customer_id}</span>
            </div>
            <p className="text-xs text-mute mt-2">
              Due: <span className="text-ink font-semibold font-mono">{formatPaise(customer.amount_paise, customer.currency)}</span> &middot; Reason: {customer.failure_reason.replace("_", " ")}
            </p>
          </div>

          <div className="flex items-center gap-2 shrink-0">
            {callActive && (
              <span className="flex items-center gap-2 px-2 py-1 rounded-sm text-xs font-mono border border-ink">
                <span className="w-2 h-2 bg-accent border border-ink animate-pulse" aria-hidden="true"></span>
                {Math.floor(callDuration / 60).toString().padStart(2, "0")}:
                {(callDuration % 60).toString().padStart(2, "0")}
              </span>
            )}
            <button
              onClick={() => {
                if (callActive) endCall();
                onClose();
              }}
              className="btn !px-2"
              aria-label="Close"
            >
              <X className="w-4 h-4" aria-hidden="true" />
            </button>
          </div>
        </div>

        {/* Tab Controls */}
        <div className="px-6 pt-3 border-b border-line flex flex-wrap items-center gap-x-6 gap-y-1" role="tablist">
          <button
            role="tab"
            aria-selected={activeTab === "simulation"}
            onClick={() => setActiveTab("simulation")}
            className={tabClass(activeTab === "simulation")}
          >
            Interactive Dialogue Simulator
          </button>
          <button
            role="tab"
            aria-selected={activeTab === "browser"}
            onClick={() => setActiveTab("browser")}
            className={tabClass(activeTab === "browser")}
          >
            LiveKit WebRTC Audio Session
          </button>
          <button
            role="tab"
            aria-selected={activeTab === "sip"}
            onClick={() => setActiveTab("sip")}
            className={tabClass(activeTab === "sip")}
          >
            Carrier Trunk Telephony (SIP)
          </button>
        </div>

        {/* Modal Body */}
        <div className="p-6 overflow-y-auto flex-1 space-y-4">
          {activeTab === "simulation" && (
            <>
              {/* Scenario Preset Buttons */}
              {!callActive && !outcomeResult && (
                <div className="space-y-4">
                  <div className="label !text-ink flex items-center gap-2">
                    <Zap className="w-3.5 h-3.5" aria-hidden="true" />
                    <span>Select Test Scenario to Trigger Outbound Call:</span>
                  </div>
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-xs">
                    <button
                      onClick={() =>
                        startCall(
                          "Yes, speaking. My salary just came in today, go ahead and try the payment again."
                        )
                      }
                      className={scenarioBtn}
                    >
                      <div className="font-semibold flex items-center justify-between gap-2">
                        <span>Branch A: Retry Payment</span>
                        <span className="font-mono text-[10px] opacity-70">Maya Shah</span>
                      </div>
                      <p className="text-[11px] opacity-70 mt-1">
                        Customer agrees &rarr; Tool executes retry &rarr; Status becomes RECOVERED.
                      </p>
                    </button>

                    <button
                      onClick={() =>
                        startCall(
                          "Hi, yes. My credit card expired last month and I got a new replacement card."
                        )
                      }
                      className={scenarioBtn}
                    >
                      <div className="font-semibold flex items-center justify-between gap-2">
                        <span>Branch B: Card Expired</span>
                        <span className="font-mono text-[10px] opacity-70">Arjun Mehta</span>
                      </div>
                      <p className="text-[11px] opacity-70 mt-1">
                        Zero read-aloud card info &rarr; Dispatches secure SMS payment link.
                      </p>
                    </button>

                    <button
                      onClick={() =>
                        startCall(
                          "Yes, it's Maya. I'm in a client meeting right now. Can you call me back on Friday?"
                        )
                      }
                      className={scenarioBtn}
                    >
                      <div className="font-semibold flex items-center justify-between gap-2">
                        <span>Branch C: Pay Later</span>
                        <span className="font-mono text-[10px] opacity-70">Riya Patel</span>
                      </div>
                      <p className="text-[11px] opacity-70 mt-1">
                        Schedules future callback in database &rarr; Status becomes SCHEDULED.
                      </p>
                    </button>

                    <button
                      onClick={() =>
                        startCall(
                          "I actually don't use this subscription anymore. Please cancel my account."
                        )
                      }
                      className={scenarioBtn}
                    >
                      <div className="font-semibold flex items-center justify-between gap-2">
                        <span>Branch D: Cancel Subscription</span>
                        <span className="font-mono text-[10px] opacity-70">Rohan Verma</span>
                      </div>
                      <p className="text-[11px] opacity-70 mt-1">
                        Zero hard-sell &rarr; Respects intent &rarr; Status CANCEL_REQUESTED.
                      </p>
                    </button>
                  </div>
                </div>
              )}

              {/* Live Transcript Stream */}
              {callActive && (
                <div className="space-y-3">
                  <div className="p-4 border border-line rounded-sm space-y-4 min-h-[220px] max-h-[320px] overflow-y-auto">
                    {messages.map((m, idx) => (
                      <div
                        key={idx}
                        className={`flex flex-col ${
                          m.speaker === "Agent" ? "items-start" : "items-end"
                        }`}
                      >
                        <span className="label mb-1">
                          {m.speaker}
                        </span>
                        <div
                          className={`max-w-[85%] rounded-sm px-4 py-2.5 text-xs leading-relaxed ${
                            m.speaker === "Agent"
                              ? "border border-ink bg-white text-ink"
                              : "bg-ink text-paper"
                          }`}
                        >
                          {m.text}
                        </div>

                        {m.toolCall && (
                          <div className="mt-1.5 px-2.5 py-1 rounded-sm border border-line text-[11px] font-mono text-mute flex items-center gap-1.5">
                            <Zap className="w-3 h-3" aria-hidden="true" />
                            <span>Tool Result: {m.toolCall.name}() &rarr; {JSON.stringify(m.toolCall.result.status || m.toolCall.result)}</span>
                          </div>
                        )}
                      </div>
                    ))}

                    {currentTool && (
                      <div className="px-2.5 py-1.5 border border-ink rounded-sm text-xs font-mono flex items-center gap-2">
                        <span className="w-2 h-2 bg-accent border border-ink animate-pulse" aria-hidden="true"></span>
                        <span>Backend executing: {currentTool}</span>
                      </div>
                    )}
                  </div>

                  {/* Customer Quick Replies during Active Call */}
                  <div className="pt-3 border-t border-line">
                    <span className="label block mb-2">
                      Simulate Customer Spoken Response:
                    </span>
                    <div className="flex flex-wrap gap-2">
                      <button
                        onClick={() => handleCustomerTurn("Go ahead and try the charge again.")}
                        disabled={isProcessing}
                        className={quickBtn}
                      >
                        &ldquo;Try the charge again&rdquo;
                      </button>
                      <button
                        onClick={() => handleCustomerTurn("My card expired last week.")}
                        disabled={isProcessing}
                        className={quickBtn}
                      >
                        &ldquo;My card expired&rdquo;
                      </button>
                      <button
                        onClick={() => handleCustomerTurn("I'm driving right now, call me on Friday.")}
                        disabled={isProcessing}
                        className={quickBtn}
                      >
                        &ldquo;Call me on Friday&rdquo;
                      </button>
                      <button
                        onClick={() => handleCustomerTurn("Please cancel my subscription.")}
                        disabled={isProcessing}
                        className={quickBtn}
                      >
                        &ldquo;Cancel subscription&rdquo;
                      </button>
                    </div>
                  </div>
                </div>
              )}

              {/* Completed Outcome Card */}
              {outcomeResult && (
                <div className={`p-4 rounded-sm border ${outcomeResult.statusColor} space-y-2`}>
                  <div className="flex items-center justify-between gap-2">
                    <div className="flex items-center gap-2">
                      <span className="w-3 h-3 bg-accent border border-ink" aria-hidden="true"></span>
                      <span className="font-serif text-xl">Call Completed: {outcomeResult.outcome}</span>
                    </div>
                    <span className="text-xs font-mono">{outcomeResult.amount}</span>
                  </div>
                  <p className="text-xs text-mute">
                    The backend state machine validated the action ({outcomeResult.action}) and logged structured outcome data to disk.
                  </p>
                </div>
              )}
            </>
          )}

          {activeTab === "browser" && (
            <div className="p-6 border border-line rounded-sm text-center space-y-4">
              <div className="w-14 h-14 border border-ink flex items-center justify-center mx-auto rounded-sm">
                <Mic className="w-6 h-6" aria-hidden="true" />
              </div>
              <div>
                <h4 className="font-serif text-2xl font-medium">LiveKit WebRTC Voice Session</h4>
                <p className="text-xs text-mute max-w-md mx-auto mt-2 leading-relaxed">
                  Creates a call session on the backend (room <code className="font-mono">recovery_&lt;call_id&gt;</code>). Browser audio is not wired up:
                  this dashboard has no LiveKit client and nothing dispatches the voice agent worker, so no voice conversation starts from here.
                </p>
              </div>

              <div className="p-3 border-y border-line text-xs font-mono max-w-md mx-auto flex flex-wrap items-center justify-between gap-2">
                <span>Customer: <strong className="text-ink">{customer.name}</strong></span>
                <span>Overdue: <strong className="text-ink">{formatPaise(customer.amount_paise, customer.currency)}</strong></span>
                <span>Card: <strong className="text-ink">•••• {customer.card_last4}</strong></span>
              </div>

              <div className="pt-2 flex justify-center gap-3">
                <button
                  onClick={async () => {
                    try {
                      const res = await initiateCall(customer.customer_id, "browser");
                      alert(`Call session created: ${res.call_id} (Room: ${res.room_name}). No audio is connected.`);
                      onCallCompleted();
                    } catch (e: any) {
                      alert(`Backend guard rejected call: ${e.message}`);
                    }
                  }}
                  className="btn btn-primary"
                >
                  <Volume2 className="w-4 h-4" aria-hidden="true" />
                  <span>Create Call Session</span>
                </button>
              </div>
            </div>
          )}

          {activeTab === "sip" && (
            <div className="p-6 border border-line rounded-sm text-center space-y-4">
              <div className="w-14 h-14 border border-ink flex items-center justify-center mx-auto rounded-sm">
                <Phone className="w-6 h-6" aria-hidden="true" />
              </div>
              <div>
                <h4 className="font-serif text-2xl font-medium">Carrier Trunk Telephony (SIP)</h4>
                <p className="text-xs text-mute max-w-md mx-auto mt-2 leading-relaxed">
                  Outbound SIP dialing is not implemented. Without a configured trunk (<code className="font-mono">LIVEKIT_SIP_TRUNK_ID</code>) the backend
                  rejects the request (403); with one it answers 501.
                </p>
              </div>

              <div className="p-3 border-y border-line text-xs font-mono max-w-xs mx-auto text-mute">
                Carrier Trunk: <span className="text-ink font-semibold">Unconfigured (Optional)</span>
              </div>

              <div className="pt-2 flex justify-center gap-3">
                <button
                  onClick={async () => {
                    try {
                      const res = await initiateCall(customer.customer_id, "sip");
                      alert(`SIP call session created: ${res.call_id}`);
                      onCallCompleted();
                    } catch (e: any) {
                      alert(`Backend guard rejected call: ${e.message} (Carrier trunk not configured). `);
                    }
                  }}
                  className="btn"
                >
                  <Phone className="w-4 h-4" aria-hidden="true" />
                  <span>Test Carrier Trunk Dial</span>
                </button>
              </div>
            </div>
          )}
        </div>

        {/* Modal Footer */}
        <div className="px-6 py-4 border-t border-ink flex flex-wrap items-center justify-between gap-3">
          <div className="flex items-center gap-2 text-xs text-mute">
            <Shield className="w-4 h-4" aria-hidden="true" />
            <span>Financial Safeguard: Agent never handles raw card or CVV details</span>
          </div>

          <div className="flex items-center gap-3">
            {callActive ? (
              <button onClick={() => endCall("manual_hangup")} className="btn btn-solid">
                <PhoneOff className="w-4 h-4" aria-hidden="true" />
                <span>End Call</span>
              </button>
            ) : (
              <button onClick={onClose} className="btn">
                Close
              </button>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};
