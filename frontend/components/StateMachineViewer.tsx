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

  const nodeClass = (stateName: string, activeColor: string = "border-indigo-500 bg-indigo-500/20 text-indigo-300 shadow-indigo-500/30") => {
    const active = isCurrent(stateName);
    return `px-3 py-1.5 rounded-lg border text-xs font-semibold flex items-center gap-1.5 transition-all ${
      active
        ? `${activeColor} shadow-lg scale-105 ring-2 ring-indigo-400/40`
        : "border-slate-800 bg-slate-900/60 text-slate-400 opacity-70"
    }`;
  };

  return (
    <div className="p-4 rounded-xl border border-slate-800 bg-slate-950/70 backdrop-blur-md">
      <div className="flex items-center justify-between mb-3 pb-2 border-b border-slate-800/80">
        <div className="flex items-center gap-2">
          <span className="text-xs font-semibold text-slate-300 uppercase tracking-wider">
            Deterministic Recovery State Machine
          </span>
          <span className="text-[10px] px-2 py-0.5 rounded bg-slate-800 text-slate-400 font-mono">
            Active: {normState}
          </span>
        </div>
        <span className="text-[11px] text-slate-400 italic">
          LLM determines intent &rarr; Backend enforces valid transitions
        </span>
      </div>

      <div className="space-y-3 pt-1">
        {/* Row 1: Pipeline Entry */}
        <div className="flex flex-wrap items-center gap-2 text-xs">
          <div className={nodeClass("PAYMENT_FAILED", "border-rose-500 bg-rose-500/20 text-rose-300")}>
            <AlertTriangle className="w-3.5 h-3.5" />
            <span>PAYMENT_FAILED</span>
          </div>

          <ArrowRight className="w-3.5 h-3.5 text-slate-600" />

          <div className={nodeClass("CONTACTING", "border-amber-500 bg-amber-500/20 text-amber-300")}>
            <PhoneForwarded className="w-3.5 h-3.5 animate-pulse" />
            <span>CONTACTING</span>
          </div>

          <ArrowRight className="w-3.5 h-3.5 text-slate-600" />

          <div className={nodeClass("CUSTOMER_VERIFIED", "border-indigo-500 bg-indigo-500/20 text-indigo-300")}>
            <CheckCircle2 className="w-3.5 h-3.5" />
            <span>CUSTOMER_VERIFIED</span>
          </div>
        </div>

        {/* Branch Divider */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-2.5 pt-2">
          {/* Branch A: Pay Now -> Recovered */}
          <div className="p-2.5 rounded-lg border border-slate-800/80 bg-slate-900/40 space-y-2">
            <span className="text-[10px] font-mono text-slate-400 block uppercase">Branch A: Pay Now</span>
            <div className={nodeClass("PAY_NOW")}>
              <span>PAY_NOW</span>
            </div>
            <div className="text-center text-slate-600 text-xs">&darr;</div>
            <div className={nodeClass("RECOVERED", "border-emerald-500 bg-emerald-500/20 text-emerald-300 shadow-emerald-500/30")}>
              <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" />
              <span>RECOVERED</span>
            </div>
          </div>

          {/* Branch B: Card Expired -> Link */}
          <div className="p-2.5 rounded-lg border border-slate-800/80 bg-slate-900/40 space-y-2">
            <span className="text-[10px] font-mono text-slate-400 block uppercase">Branch B: Card Expired</span>
            <div className={nodeClass("PAYMENT_LINK_SENT", "border-blue-500 bg-blue-500/20 text-blue-300 shadow-blue-500/30")}>
              <Send className="w-3.5 h-3.5 text-blue-400" />
              <span>PAYMENT_LINK_SENT</span>
            </div>
            <p className="text-[10px] text-slate-400 mt-2 leading-tight">
              Zero read-aloud card numbers. Instant SMS payment link.
            </p>
          </div>

          {/* Branch C: Pay Later -> Scheduled */}
          <div className="p-2.5 rounded-lg border border-slate-800/80 bg-slate-900/40 space-y-2">
            <span className="text-[10px] font-mono text-slate-400 block uppercase">Branch C: Pay Later</span>
            <div className={nodeClass("PAY_LATER")}>
              <span>PAY_LATER</span>
            </div>
            <div className="text-center text-slate-600 text-xs">&darr;</div>
            <div className={nodeClass("SCHEDULED", "border-purple-500 bg-purple-500/20 text-purple-300 shadow-purple-500/30")}>
              <Clock className="w-3.5 h-3.5 text-purple-400" />
              <span>SCHEDULED</span>
            </div>
          </div>

          {/* Branch D/E: Cancel / Decline */}
          <div className="p-2.5 rounded-lg border border-slate-800/80 bg-slate-900/40 space-y-2">
            <span className="text-[10px] font-mono text-slate-400 block uppercase">Branch D/E: Off-Ramps</span>
            <div className={nodeClass("CANCEL_REQUESTED", "border-slate-500 bg-slate-500/20 text-slate-300")}>
              <XCircle className="w-3.5 h-3.5" />
              <span>CANCEL_REQUESTED</span>
            </div>
            <div className={nodeClass("DECLINED", "border-rose-500 bg-rose-500/20 text-rose-300")}>
              <XCircle className="w-3.5 h-3.5" />
              <span>DECLINED</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
