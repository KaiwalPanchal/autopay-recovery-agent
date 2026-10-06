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
            statusColor: "text-emerald-400 bg-emerald-500/10 border-emerald-500/30",
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
          statusColor: "text-blue-400 bg-blue-500/10 border-blue-500/30",
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
          statusColor: "text-purple-400 bg-purple-500/10 border-purple-500/30",
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
          statusColor: "text-slate-400 bg-slate-500/10 border-slate-500/30",
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
          statusColor: "text-amber-400 bg-amber-500/10 border-amber-500/30",
        });
        setIsProcessing(false);
      }, 700);
      return;
    }

    setIsProcessing(false);
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-sm animate-in fade-in duration-200">
      <div className="bg-slate-900 border border-slate-700/80 rounded-2xl w-full max-w-3xl overflow-hidden shadow-2xl flex flex-col max-h-[90vh]">
        {/* Modal Header */}
        <div className="px-6 py-4 border-b border-slate-800 bg-slate-950/60 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-lg bg-indigo-600/20 border border-indigo-500/30 text-indigo-400 flex items-center justify-center">
              <Phone className="w-5 h-5" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h3 className="font-bold text-white text-sm">
                  Voice Recovery Console &middot; {customer.name}
                </h3>
                <span className="text-xs px-2 py-0.5 rounded bg-slate-800 text-slate-400 font-mono">
                  {customer.customer_id}
                </span>
              </div>
              <p className="text-xs text-slate-400">
                Due: <span className="text-white font-semibold">{formatPaise(customer.amount_paise, customer.currency)}</span> &middot; Reason: {customer.failure_reason.replace("_", " ")}
              </p>
            </div>
          </div>

          <div className="flex items-center gap-2">
            {callActive && (
              <span className="flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-mono bg-emerald-500/10 text-emerald-400 border border-emerald-500/30">
                <span className="w-2 h-2 rounded-full bg-emerald-400 animate-ping"></span>
                {Math.floor(callDuration / 60).toString().padStart(2, "0")}:
                {(callDuration % 60).toString().padStart(2, "0")}
              </span>
            )}
            <button
              onClick={() => {
                if (callActive) endCall();
                onClose();
              }}
              className="p-1.5 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800 transition-colors"
            >
              <X className="w-5 h-5" />
            </button>
          </div>
        </div>

        {/* Tab Controls */}
        <div className="px-6 py-2.5 bg-slate-950/30 border-b border-slate-800/80 flex items-center gap-2 text-xs">
          <button
            onClick={() => setActiveTab("simulation")}
            className={`px-3 py-1.5 rounded-lg font-medium transition-colors ${
              activeTab === "simulation"
                ? "bg-indigo-600 text-white"
                : "text-slate-400 hover:text-slate-200"
            }`}
          >
            Interactive Dialogue Simulator
          </button>
          <button
            onClick={() => setActiveTab("browser")}
            className={`px-3 py-1.5 rounded-lg font-medium transition-colors ${
              activeTab === "browser"
                ? "bg-indigo-600 text-white"
                : "text-slate-400 hover:text-slate-200"
            }`}
          >
            LiveKit WebRTC Audio Session
          </button>
          <button
            onClick={() => setActiveTab("sip")}
            className={`px-3 py-1.5 rounded-lg font-medium transition-colors ${
              activeTab === "sip"
                ? "bg-indigo-600 text-white"
                : "text-slate-400 hover:text-slate-200"
            }`}
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
                <div className="p-4 rounded-xl border border-slate-800 bg-slate-950/40 space-y-3">
                  <div className="flex items-center gap-2 text-xs font-semibold text-slate-300 uppercase tracking-wider">
                    <Zap className="w-3.5 h-3.5 text-indigo-400" />
                    <span>Select Test Scenario to Trigger Outbound Call:</span>
                  </div>
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 text-xs">
                    <button
                      onClick={() =>
                        startCall(
                          "Yes, speaking. My salary just came in today, go ahead and try the payment again."
                        )
                      }
                      className="p-3 rounded-lg border border-emerald-500/30 bg-emerald-500/10 hover:bg-emerald-500/20 text-emerald-300 text-left font-medium transition-all"
                    >
                      <div className="font-bold flex items-center justify-between">
                        <span>Branch A: Retry Payment</span>
                        <span className="text-[10px] px-1.5 py-0.5 rounded bg-emerald-500/20">Maya Shah</span>
                      </div>
                      <p className="text-[11px] text-emerald-400/80 mt-1">
                        Customer agrees &rarr; Tool executes retry &rarr; Status becomes RECOVERED.
                      </p>
                    </button>

                    <button
                      onClick={() =>
                        startCall(
                          "Hi, yes. My credit card expired last month and I got a new replacement card."
                        )
                      }
                      className="p-3 rounded-lg border border-blue-500/30 bg-blue-500/10 hover:bg-blue-500/20 text-blue-300 text-left font-medium transition-all"
                    >
                      <div className="font-bold flex items-center justify-between">
                        <span>Branch B: Card Expired</span>
                        <span className="text-[10px] px-1.5 py-0.5 rounded bg-blue-500/20">Arjun Mehta</span>
                      </div>
                      <p className="text-[11px] text-blue-400/80 mt-1">
                        Zero read-aloud card info &rarr; Dispatches secure SMS payment link.
                      </p>
                    </button>

                    <button
                      onClick={() =>
                        startCall(
                          "Yes, it's Maya. I'm in a client meeting right now. Can you call me back on Friday?"
                        )
                      }
                      className="p-3 rounded-lg border border-purple-500/30 bg-purple-500/10 hover:bg-purple-500/20 text-purple-300 text-left font-medium transition-all"
                    >
                      <div className="font-bold flex items-center justify-between">
                        <span>Branch C: Pay Later</span>
                        <span className="text-[10px] px-1.5 py-0.5 rounded bg-purple-500/20">Riya Patel</span>
                      </div>
                      <p className="text-[11px] text-purple-400/80 mt-1">
                        Schedules future callback in database &rarr; Status becomes SCHEDULED.
                      </p>
                    </button>

                    <button
                      onClick={() =>
                        startCall(
                          "I actually don't use this subscription anymore. Please cancel my account."
                        )
                      }
                      className="p-3 rounded-lg border border-slate-700 bg-slate-800/40 hover:bg-slate-800 text-slate-300 text-left font-medium transition-all"
                    >
                      <div className="font-bold flex items-center justify-between">
                        <span>Branch D: Cancel Subscription</span>
                        <span className="text-[10px] px-1.5 py-0.5 rounded bg-slate-700">Rohan Verma</span>
                      </div>
                      <p className="text-[11px] text-slate-400 mt-1">
                        Zero hard-sell &rarr; Respects intent &rarr; Status CANCEL_REQUESTED.
                      </p>
                    </button>
                  </div>
                </div>
              )}

              {/* Live Transcript Stream */}
              {callActive && (
                <div className="space-y-3">
                  <div className="p-4 rounded-xl border border-slate-800 bg-slate-950/70 space-y-3 min-h-[220px] max-h-[320px] overflow-y-auto">
                    {messages.map((m, idx) => (
                      <div
                        key={idx}
                        className={`flex flex-col ${
                          m.speaker === "Agent" ? "items-start" : "items-end"
                        }`}
                      >
                        <span className="text-[10px] font-mono text-slate-400 mb-0.5">
                          {m.speaker}
                        </span>
                        <div
                          className={`max-w-[85%] rounded-xl px-4 py-2.5 text-xs ${
                            m.speaker === "Agent"
                              ? "bg-indigo-600/20 border border-indigo-500/30 text-indigo-100 rounded-tl-sm"
                              : "bg-slate-800 border border-slate-700 text-white rounded-tr-sm"
                          }`}
                        >
                          {m.text}
                        </div>

                        {m.toolCall && (
                          <div className="mt-1.5 px-3 py-1 rounded bg-slate-900 border border-indigo-500/40 text-[11px] font-mono text-indigo-300 flex items-center gap-1.5">
                            <Zap className="w-3 h-3 text-amber-400" />
                            <span>Tool Result: {m.toolCall.name}() &rarr; {JSON.stringify(m.toolCall.result.status || m.toolCall.result)}</span>
                          </div>
                        )}
                      </div>
                    ))}

                    {currentTool && (
                      <div className="p-2 rounded bg-indigo-950/50 border border-indigo-500/30 text-indigo-300 text-xs font-mono animate-pulse flex items-center gap-2">
                        <Zap className="w-3.5 h-3.5 text-amber-400 animate-spin" />
                        <span>Backend executing: {currentTool}</span>
                      </div>
                    )}
                  </div>

                  {/* Customer Quick Replies during Active Call */}
                  <div className="pt-2 border-t border-slate-800/80">
                    <span className="text-[11px] text-slate-400 block mb-1.5 font-medium">
                      Simulate Customer Spoken Response:
                    </span>
                    <div className="flex flex-wrap gap-2 text-xs">
                      <button
                        onClick={() => handleCustomerTurn("Go ahead and try the charge again.")}
                        disabled={isProcessing}
                        className="px-2.5 py-1.5 rounded-lg bg-emerald-500/20 text-emerald-300 border border-emerald-500/30 hover:bg-emerald-500/30"
                      >
                        &ldquo;Try the charge again&rdquo;
                      </button>
                      <button
                        onClick={() => handleCustomerTurn("My card expired last week.")}
                        disabled={isProcessing}
                        className="px-2.5 py-1.5 rounded-lg bg-blue-500/20 text-blue-300 border border-blue-500/30 hover:bg-blue-500/30"
                      >
                        &ldquo;My card expired&rdquo;
                      </button>
                      <button
                        onClick={() => handleCustomerTurn("I'm driving right now, call me on Friday.")}
                        disabled={isProcessing}
                        className="px-2.5 py-1.5 rounded-lg bg-purple-500/20 text-purple-300 border border-purple-500/30 hover:bg-purple-500/30"
                      >
                        &ldquo;Call me on Friday&rdquo;
                      </button>
                      <button
                        onClick={() => handleCustomerTurn("Please cancel my subscription.")}
                        disabled={isProcessing}
                        className="px-2.5 py-1.5 rounded-lg bg-slate-700 text-slate-300 hover:bg-slate-600"
                      >
                        &ldquo;Cancel subscription&rdquo;
                      </button>
                    </div>
                  </div>
                </div>
              )}

              {/* Completed Outcome Card */}
              {outcomeResult && (
                <div className={`p-4 rounded-xl border ${outcomeResult.statusColor} space-y-2`}>
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <CheckCircle2 className="w-5 h-5 text-emerald-400" />
                      <span className="font-bold text-sm">Call Completed: {outcomeResult.outcome}</span>
                    </div>
                    <span className="text-xs font-mono">{outcomeResult.amount}</span>
                  </div>
                  <p className="text-xs opacity-80">
                    The backend state machine validated the action ({outcomeResult.action}) and logged structured outcome data to disk.
                  </p>
                </div>
              )}
            </>
          )}

          {activeTab === "browser" && (
            <div className="p-6 rounded-xl border border-slate-800 bg-slate-950/60 text-center space-y-4">
              <div className="w-16 h-16 rounded-full bg-indigo-600/20 border border-indigo-500/40 text-indigo-400 flex items-center justify-center mx-auto">
                <Mic className="w-8 h-8" />
              </div>
              <div>
                <h4 className="font-bold text-white text-base">LiveKit WebRTC Voice Session</h4>
                <p className="text-xs text-slate-400 max-w-md mx-auto mt-1">
                  Connect your microphone directly to the LiveKit voice agent room (<code>recovery_{customer.customer_id}</code>).
                  The agent runs real-time STT &rarr; LLM (with strictly bound payment tools) &rarr; TTS with sub-700ms voice response latency.
                </p>
              </div>

              <div className="p-3 rounded-lg bg-slate-900 border border-slate-800 text-xs font-mono max-w-md mx-auto text-slate-300 flex items-center justify-between">
                <span>Customer: <strong className="text-white">{customer.name}</strong></span>
                <span>Overdue: <strong className="text-emerald-400">{formatPaise(customer.amount_paise, customer.currency)}</strong></span>
                <span>Card: <strong className="text-white">•••• {customer.card_last4}</strong></span>
              </div>

              <div className="pt-2 flex justify-center gap-3">
                <button
                  onClick={async () => {
                    try {
                      const res = await initiateCall(customer.customer_id, "browser");
                      alert(`WebRTC session created: ${res.call_id} (Room: ${res.room_name})`);
                      onCallCompleted();
                    } catch (e: any) {
                      alert(`Backend guard rejected call: ${e.message}`);
                    }
                  }}
                  className="px-5 py-2.5 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-bold shadow-lg shadow-indigo-600/30 flex items-center gap-2"
                >
                  <Volume2 className="w-4 h-4" />
                  <span>Connect WebRTC Audio (Recommended)</span>
                </button>
              </div>
            </div>
          )}

          {activeTab === "sip" && (
            <div className="p-6 rounded-xl border border-slate-800 bg-slate-950/60 text-center space-y-4">
              <div className="w-16 h-16 rounded-full bg-amber-500/20 border border-amber-500/40 text-amber-400 flex items-center justify-center mx-auto">
                <Phone className="w-8 h-8" />
              </div>
              <div>
                <h4 className="font-bold text-white text-base">Carrier Trunk Telephony (SIP)</h4>
                <p className="text-xs text-slate-400 max-w-md mx-auto mt-1">
                  Outbound carrier telephony requires a configured SIP trunk (via <code>LIVEKIT_SIP_TRUNK_ID</code>).
                  Without a carrier trunk, requests are cleanly rejected by the backend security boundary.
                </p>
              </div>

              <div className="p-3 rounded-lg bg-slate-900 border border-slate-800 text-xs font-mono max-w-xs mx-auto text-slate-400">
                Carrier Trunk: <span className="text-amber-400 font-semibold">Unconfigured (Optional)</span>
              </div>

              <div className="pt-2 flex justify-center gap-3">
                <button
                  onClick={async () => {
                    try {
                      const res = await initiateCall(customer.customer_id, "sip");
                      alert(`SIP call session created: ${res.call_id}`);
                      onCallCompleted();
                    } catch (e: any) {
                      alert(`Backend guard rejected call: ${e.message} (Carrier trunk not configured). Please use WebRTC Audio Session for real-time voice.`);
                    }
                  }}
                  className="px-5 py-2.5 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs font-bold border border-slate-700 flex items-center gap-2"
                >
                  <Phone className="w-4 h-4" />
                  <span>Test Carrier Trunk Dial</span>
                </button>
              </div>
            </div>
          )}
        </div>

        {/* Modal Footer */}
        <div className="px-6 py-4 border-t border-slate-800 bg-slate-950/60 flex items-center justify-between">
          <div className="flex items-center gap-2 text-xs text-slate-400">
            <Shield className="w-4 h-4 text-indigo-400" />
            <span>Financial Safeguard: Agent never handles raw card or CVV details</span>
          </div>

          <div className="flex items-center gap-3">
            {callActive ? (
              <button
                onClick={() => endCall("manual_hangup")}
                className="px-4 py-2 rounded-xl bg-rose-600 hover:bg-rose-500 text-white text-xs font-semibold flex items-center gap-2 shadow-lg shadow-rose-600/30"
              >
                <PhoneOff className="w-4 h-4" />
                <span>End Call</span>
              </button>
            ) : (
              <button
                onClick={onClose}
                className="px-4 py-2 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs font-medium"
              >
                Close
              </button>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};
