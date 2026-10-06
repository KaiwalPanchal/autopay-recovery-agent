"use client";

import React from "react";
import {
  X,
  Phone,
  CreditCard,
  AlertTriangle,
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
    <div
      className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/40"
      role="dialog"
      aria-modal="true"
      aria-label={`Customer details for ${customer.name}`}
    >
      <div className="bg-white border border-ink rounded-sm w-full max-w-4xl overflow-hidden flex flex-col max-h-[90vh]">
        {/* Header */}
        <div className="px-6 py-5 border-b border-ink flex items-start justify-between gap-4">
          <div>
            <div className="flex flex-wrap items-baseline gap-3">
              <h3 className="font-serif text-3xl font-medium tracking-tight leading-none">{customer.name}</h3>
              <span className="label">{customer.customer_id}</span>
            </div>
            <p className="text-xs text-mute mt-2">
              {customer.subscription} &middot; Card ending in {customer.card_last4}
            </p>
          </div>

          <div className="flex items-center gap-2 shrink-0">
            <button onClick={() => onCallCustomer(customer)} className="btn btn-primary">
              <Phone className="w-3.5 h-3.5" aria-hidden="true" />
              <span>Initiate Call</span>
            </button>
            <button onClick={onClose} className="btn !px-2" aria-label="Close">
              <X className="w-4 h-4" aria-hidden="true" />
            </button>
          </div>
        </div>

        {/* Content */}
        <div className="p-6 overflow-y-auto space-y-8">
          {/* Top Attributes Grid */}
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-x-6 gap-y-5">
            <div className="border-t border-ink pt-2">
              <span className="label block mb-2">Amount Due</span>
              <span className="numeral text-4xl block">
                {formatPaise(customer.amount_paise, customer.currency)}
              </span>
            </div>

            <div className="border-t border-ink pt-2">
              <span className="label block mb-2">Failure Reason</span>
              <span className="text-sm font-medium capitalize flex items-center gap-1.5">
                <AlertTriangle className="w-3.5 h-3.5" aria-hidden="true" />
                {customer.failure_reason.replace("_", " ")}
              </span>
            </div>

            <div className="border-t border-ink pt-2">
              <span className="label block mb-2">Card on File</span>
              <span className="text-sm font-medium flex items-center gap-1.5">
                <CreditCard className="w-3.5 h-3.5" aria-hidden="true" />
                Ending in {customer.card_last4}
              </span>
            </div>

            <div className="border-t border-ink pt-2">
              <span className="label block mb-2">Simulated Gate</span>
              <span className="font-mono text-sm font-medium">
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
            <div className="py-3 border-y border-line flex flex-wrap items-center justify-between gap-2 text-xs">
              <div className="flex items-center gap-2">
                <ExternalLink className="w-4 h-4" aria-hidden="true" />
                <span>
                  <strong className="font-semibold">Active Recovery Link:</strong> {customer.recovery_link}
                </span>
              </div>
              <span className="label">Expires in 48h</span>
            </div>
          )}

          {customer.scheduled_at && (
            <div className="py-3 border-y border-line flex flex-wrap items-center justify-between gap-2 text-xs">
              <div className="flex items-center gap-2">
                <Clock className="w-4 h-4" aria-hidden="true" />
                <span>
                  <strong className="font-semibold">Scheduled Callback:</strong> {customer.scheduled_at}
                </span>
              </div>
              <span className="label">Callback Queued</span>
            </div>
          )}

          {/* Call History / Outcomes for this Customer */}
          <div className="space-y-3">
            <h4 className="label flex items-center gap-2 border-t border-ink pt-2">
              <FileText className="w-3.5 h-3.5" aria-hidden="true" />
              <span>Call History &amp; Structured Outcomes</span>
            </h4>

            {customer.status !== "payment_failed" ? (
              <div className="text-xs space-y-2">
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <span className="font-semibold capitalize flex items-center gap-2">
                    <span className="w-2 h-2 bg-accent border border-ink" aria-hidden="true"></span>
                    Outcome / State: {customer.current_state.replace("_", " ")}
                  </span>
                  <span className="text-[11px] font-mono text-mute">
                    Status: {customer.status}
                  </span>
                </div>
                {customer.last_call_at && (
                  <p className="text-[11px] text-mute">Last contact: {customer.last_call_at}</p>
                )}
                {customer.notes && (
                  <p className="text-[11px] text-mute">Notes: {customer.notes}</p>
                )}
              </div>
            ) : (
              <div className="py-6 border border-dashed border-line text-center text-xs text-mute">
                No active recovery outcome recorded yet for this customer. Click &ldquo;Initiate Call&rdquo; to test.
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};
