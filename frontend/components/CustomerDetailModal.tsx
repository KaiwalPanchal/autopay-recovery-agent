"use client";

import React, { useState, useEffect } from "react";
import {
  X,
  Phone,
  CreditCard,
  Calendar,
  AlertTriangle,
  CheckCircle2,
  ExternalLink,
  Clock,
  FileText,
} from "lucide-react";
import { Customer, formatPaise } from "../lib/api";
import { StateMachineViewer } from "./StateMachineViewer";

interface CustomerDetailModalProps {
  customer: Customer | null;
  onClose: () => void;
  onCallCustomer: (customer: Customer) => void;
}

export const CustomerDetailModal: React.FC<CustomerDetailModalProps> = ({
  customer,
  onClose,
  onCallCustomer,
}) => {
  if (!customer) return null;

  const currency = customer.currency === "INR" ? "₹" : "$";

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-sm animate-in fade-in duration-200">
      <div className="bg-slate-900 border border-slate-700/80 rounded-2xl w-full max-w-4xl overflow-hidden shadow-2xl flex flex-col max-h-[90vh]">
        {/* Header */}
        <div className="px-6 py-4 border-b border-slate-800 bg-slate-950/60 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-indigo-600/20 border border-indigo-500/30 text-indigo-400 flex items-center justify-center font-bold">
              {customer.name.charAt(0)}
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h3 className="font-bold text-white text-base">{customer.name}</h3>
                <span className="text-xs px-2 py-0.5 rounded bg-slate-800 text-slate-400 font-mono">
                  {customer.customer_id}
                </span>
              </div>
              <p className="text-xs text-slate-400">
                {customer.subscription} &middot; Card ending in {customer.card_last4}
              </p>
            </div>
          </div>

          <div className="flex items-center gap-2">
            <button
              onClick={() => onCallCustomer(customer)}
              className="px-3.5 py-1.5 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-semibold shadow-md shadow-indigo-600/30 flex items-center gap-1.5"
            >
              <Phone className="w-3.5 h-3.5" />
              <span>Initiate Call</span>
            </button>
            <button
              onClick={onClose}
              className="p-1.5 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800 transition-colors"
            >
              <X className="w-5 h-5" />
            </button>
          </div>
        </div>

        {/* Content */}
        <div className="p-6 overflow-y-auto space-y-6">
          {/* Top Attributes Grid */}
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-xs">
            <div className="p-3 rounded-xl border border-slate-800 bg-slate-950/50">
              <span className="text-slate-400 block mb-1">Amount Due</span>
              <span className="text-lg font-bold text-white">
                {formatPaise(customer.amount_paise, customer.currency)}
              </span>
            </div>

            <div className="p-3 rounded-xl border border-slate-800 bg-slate-950/50">
              <span className="text-slate-400 block mb-1">Failure Reason</span>
              <span className="font-semibold text-rose-300 capitalize flex items-center gap-1">
                <AlertTriangle className="w-3.5 h-3.5 text-rose-400" />
                {customer.failure_reason.replace("_", " ")}
              </span>
            </div>

            <div className="p-3 rounded-xl border border-slate-800 bg-slate-950/50">
              <span className="text-slate-400 block mb-1">Card on File</span>
              <span className="font-semibold text-slate-200 flex items-center gap-1">
                <CreditCard className="w-3.5 h-3.5 text-slate-400" />
                Ending in {customer.card_last4}
              </span>
            </div>

            <div className="p-3 rounded-xl border border-slate-800 bg-slate-950/50">
              <span className="text-slate-400 block mb-1">Simulated Gate</span>
              <span className="font-mono text-indigo-300 font-semibold">
                {customer.simulated_outcome}
              </span>
            </div>
          </div>

          {/* Recovery State Machine Visualization */}
          <div>
            <StateMachineViewer currentState={customer.current_state || customer.status} />
          </div>

          {/* Additional details: payment link or scheduled callback */}
          {customer.recovery_link && (
            <div className="p-3.5 rounded-xl border border-blue-500/30 bg-blue-500/10 flex items-center justify-between text-xs">
              <div className="flex items-center gap-2 text-blue-300">
                <ExternalLink className="w-4 h-4" />
                <span>
                  <strong>Active Recovery Link:</strong> {customer.recovery_link}
                </span>
              </div>
              <span className="text-[11px] text-blue-400">Expires in 48h</span>
            </div>
          )}

          {customer.scheduled_at && (
            <div className="p-3.5 rounded-xl border border-purple-500/30 bg-purple-500/10 flex items-center justify-between text-xs">
              <div className="flex items-center gap-2 text-purple-300">
                <Clock className="w-4 h-4" />
                <span>
                  <strong>Scheduled Callback:</strong> {customer.scheduled_at}
                </span>
              </div>
              <span className="text-[11px] text-purple-400">Callback Queued</span>
            </div>
          )}

          {/* Call History / Outcomes for this Customer */}
          <div className="space-y-3">
            <h4 className="text-xs font-bold uppercase tracking-wider text-slate-400 flex items-center gap-2">
              <FileText className="w-4 h-4" />
              <span>Call History &amp; Structured Outcomes</span>
            </h4>

            {customer.status !== "payment_failed" ? (
              <div className="p-4 rounded-xl border border-slate-800 bg-slate-950/60 text-xs space-y-2">
                <div className="flex items-center justify-between">
                  <span className="font-bold text-white capitalize flex items-center gap-1.5">
                    <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" />
                    Outcome / State: {customer.current_state.replace("_", " ")}
                  </span>
                  <span className="text-[11px] font-mono text-slate-400">
                    Status: {customer.status}
                  </span>
                </div>
                {customer.last_call_at && (
                  <p className="text-[11px] text-slate-400">Last contact: {customer.last_call_at}</p>
                )}
                {customer.notes && (
                  <p className="text-[11px] text-slate-400">Notes: {customer.notes}</p>
                )}
              </div>
            ) : (
              <div className="p-6 rounded-xl border border-slate-800 bg-slate-950/40 text-center text-xs text-slate-500">
                No active recovery outcome recorded yet for this customer. Click &ldquo;Initiate Call&rdquo; to test.
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};
