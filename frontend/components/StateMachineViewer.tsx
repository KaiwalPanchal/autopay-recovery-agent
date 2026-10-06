"use client";

import React from "react";
import { ArrowRight, CheckCircle2, Clock, AlertTriangle, XCircle, Send, PhoneForwarded } from "lucide-react";

interface StateMachineViewerProps {
  currentState?: string;
}

export const StateMachineViewer: React.FC<StateMachineViewerProps> = ({
  currentState = "PAYMENT_FAILED",
}) => {
  const normState = currentState?.toUpperCase() || "PAYMENT_FAILED";

  const isCurrent = (stateName: string) => normState === stateName;

  const nodeClass = (stateName: string) => {
    const active = isCurrent(stateName);
    return `px-2.5 py-1.5 rounded-sm border text-[11px] font-mono uppercase tracking-[0.08em] flex items-center gap-1.5 ${
      active
        ? "border-ink bg-accent text-ink font-semibold"
        : "border-line bg-white text-mute"
    }`;
  };

  const branch = "p-3 border border-line rounded-sm space-y-2";

  return (
    <div className="border-t border-ink pt-2">
      <div className="flex flex-wrap items-center justify-between gap-2 mb-4">
        <div className="flex flex-wrap items-center gap-3">
          <span className="label !text-ink">
            Deterministic Recovery State Machine
          </span>
          <span className="font-mono text-[10px] px-1.5 py-0.5 border border-ink rounded-sm">
            Active: {normState}
          </span>
        </div>
        <span className="text-[11px] text-mute italic font-serif">
          LLM determines intent &rarr; Backend enforces valid transitions
        </span>
      </div>

      <div className="space-y-3 pt-1">
        {/* Row 1: Pipeline Entry */}
        <div className="flex flex-wrap items-center gap-2 text-xs">
          <div className={nodeClass("PAYMENT_FAILED")}>
            <AlertTriangle className="w-3.5 h-3.5" aria-hidden="true" />
            <span>PAYMENT_FAILED</span>
          </div>

          <ArrowRight className="w-3.5 h-3.5 text-faint" aria-hidden="true" />

          <div className={nodeClass("CONTACTING")}>
            <PhoneForwarded className="w-3.5 h-3.5" aria-hidden="true" />
            <span>CONTACTING</span>
          </div>

          <ArrowRight className="w-3.5 h-3.5 text-faint" aria-hidden="true" />

          <div className={nodeClass("CUSTOMER_VERIFIED")}>
            <CheckCircle2 className="w-3.5 h-3.5" aria-hidden="true" />
            <span>CUSTOMER_VERIFIED</span>
          </div>
        </div>

        {/* Branch Divider */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-3 pt-2">
          {/* Branch A: Pay Now -> Recovered */}
          <div className={branch}>
            <span className="label block">Branch A: Pay Now</span>
            <div className={nodeClass("PAY_NOW")}>
              <span>PAY_NOW</span>
            </div>
            <div className="text-center text-faint text-xs" aria-hidden="true">&darr;</div>
            <div className={nodeClass("RECOVERED")}>
              <CheckCircle2 className="w-3.5 h-3.5" aria-hidden="true" />
              <span>RECOVERED</span>
            </div>
          </div>

          {/* Branch B: Card Expired -> Link */}
          <div className={branch}>
            <span className="label block">Branch B: Card Expired</span>
            <div className={nodeClass("PAYMENT_LINK_SENT")}>
              <Send className="w-3.5 h-3.5" aria-hidden="true" />
              <span>PAYMENT_LINK_SENT</span>
            </div>
            <p className="text-[11px] text-mute mt-2 leading-snug">
              Zero read-aloud card numbers. Instant SMS payment link.
            </p>
          </div>

          {/* Branch C: Pay Later -> Scheduled */}
          <div className={branch}>
            <span className="label block">Branch C: Pay Later</span>
            <div className={nodeClass("PAY_LATER")}>
              <span>PAY_LATER</span>
            </div>
            <div className="text-center text-faint text-xs" aria-hidden="true">&darr;</div>
            <div className={nodeClass("SCHEDULED")}>
              <Clock className="w-3.5 h-3.5" aria-hidden="true" />
              <span>SCHEDULED</span>
            </div>
          </div>

          {/* Branch D/E: Cancel / Decline */}
          <div className={branch}>
            <span className="label block">Branch D/E: Off-Ramps</span>
            <div className={nodeClass("CANCEL_REQUESTED")}>
              <XCircle className="w-3.5 h-3.5" aria-hidden="true" />
              <span>CANCEL_REQUESTED</span>
            </div>
            <div className={nodeClass("DECLINED")}>
              <XCircle className="w-3.5 h-3.5" aria-hidden="true" />
              <span>DECLINED</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
