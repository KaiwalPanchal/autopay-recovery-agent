"use client";

import React, { useState } from "react";
import { Phone, Info, CheckCircle2, Clock, Link2, XCircle, AlertCircle, ArrowUpRight } from "lucide-react";
import { Customer, formatPaise } from "../lib/api";

interface CustomerTableProps {
  customers: Customer[];
  onSelectCustomer: (customer: Customer) => void;
  onCallCustomer: (customer: Customer) => void;
}

export const CustomerTable: React.FC<CustomerTableProps> = ({
  customers,
  onSelectCustomer,
  onCallCustomer,
}) => {
  const [filter, setFilter] = useState<string>("ALL");

  const getStatusBadge = (status: string, state: string) => {
    const s = status.toLowerCase();
    if (s === "recovered") {
      return (
        <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md text-xs font-semibold bg-emerald-500/10 text-emerald-400 border border-emerald-500/30">
          <CheckCircle2 className="w-3.5 h-3.5" />
          RECOVERED
        </span>
      );
    }
    if (s === "payment_link_sent") {
      return (
        <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md text-xs font-semibold bg-blue-500/10 text-blue-400 border border-blue-500/30">
          <Link2 className="w-3.5 h-3.5" />
          LINK SENT
        </span>
      );
    }
    if (s === "scheduled") {
      return (
        <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md text-xs font-semibold bg-purple-500/10 text-purple-400 border border-purple-500/30">
          <Clock className="w-3.5 h-3.5" />
          SCHEDULED
        </span>
      );
    }
    if (s === "cancel_requested") {
      return (
        <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md text-xs font-semibold bg-slate-500/10 text-slate-300 border border-slate-500/30">
          <XCircle className="w-3.5 h-3.5" />
          CANCEL REQUESTED
        </span>
      );
    }
    if (s === "declined") {
      return (
        <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md text-xs font-semibold bg-amber-500/10 text-amber-400 border border-amber-500/30">
          <XCircle className="w-3.5 h-3.5" />
          DECLINED
        </span>
      );
    }
    if (s === "in_progress") {
      return (
        <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md text-xs font-semibold bg-indigo-500/10 text-indigo-400 border border-indigo-500/30 animate-pulse">
          <Phone className="w-3.5 h-3.5" />
          IN PROGRESS
        </span>
      );
    }
    return (
      <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md text-xs font-semibold bg-rose-500/10 text-rose-400 border border-rose-500/30">
        <AlertCircle className="w-3.5 h-3.5" />
        PAYMENT FAILED
      </span>
    );
  };

  const filteredCustomers = customers.filter((c) => {
    if (filter === "ALL") return true;
    if (filter === "FAILED") return c.status === "payment_failed";
    if (filter === "RECOVERED") return c.status === "recovered";
    if (filter === "LINKS") return c.status === "payment_link_sent";
    if (filter === "SCHEDULED") return c.status === "scheduled";
    if (filter === "OFFRAMP") return c.status === "cancel_requested" || c.status === "declined";
    return true;
  });

  return (
    <div className="rounded-xl border border-slate-800 bg-slate-900/60 backdrop-blur-md overflow-hidden">
      {/* Table Header Controls */}
      <div className="px-6 py-4 border-b border-slate-800 flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h2 className="text-base font-bold text-white tracking-wide">
            CUSTOMER RECOVERY QUEUE
          </h2>
          <p className="text-xs text-slate-400">
            10 Authentic customer personas with simulated payment failures &amp; deterministic outcomes
          </p>
        </div>

        {/* Filter Pills */}
        <div className="flex flex-wrap items-center gap-1.5 text-xs">
          {[
            { id: "ALL", label: `All (${customers.length})` },
            { id: "FAILED", label: "Failed" },
            { id: "RECOVERED", label: "Recovered" },
            { id: "LINKS", label: "Links" },
            { id: "SCHEDULED", label: "Scheduled" },
            { id: "OFFRAMP", label: "Off-ramps" },
          ].map((tab) => (
            <button
              key={tab.id}
              onClick={() => setFilter(tab.id)}
              className={`px-2.5 py-1 rounded-lg text-xs font-medium transition-colors ${
                filter === tab.id
                  ? "bg-indigo-600 text-white shadow-sm shadow-indigo-500/30"
                  : "bg-slate-800/80 text-slate-400 hover:text-slate-200"
              }`}
            >
              {tab.label}
            </button>
          ))}
        </div>
      </div>

      {/* Table View */}
      <div className="overflow-x-auto">
        <table className="w-full text-left text-sm text-slate-300">
          <thead className="bg-slate-950/60 text-xs uppercase font-medium text-slate-400 border-b border-slate-800">
            <tr>
              <th className="py-3 px-5">Customer &amp; Plan</th>
              <th className="py-3 px-4">Overdue Amount (₹)</th>
              <th className="py-3 px-4">Failure Reason</th>
              <th className="py-3 px-4">Recovery Status</th>
              <th className="py-3 px-4">Retries</th>
              <th className="py-3 px-5 text-right">Actions</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-800/70">
            {filteredCustomers.length === 0 ? (
              <tr>
                <td colSpan={6} className="py-8 text-center text-slate-500 text-xs">
                  No customers match the current filter.
                </td>
              </tr>
            ) : (
              filteredCustomers.map((c) => {
                return (
                  <tr
                    key={c.customer_id}
                    className="hover:bg-slate-800/40 transition-colors group cursor-pointer"
                    onClick={() => onSelectCustomer(c)}
                  >
                    <td className="py-3.5 px-5">
                      <div className="font-semibold text-white group-hover:text-indigo-300 transition-colors flex items-center gap-2">
                        {c.name}
                        <span className="text-[10px] font-mono text-slate-500">
                          {c.customer_id}
                        </span>
                      </div>
                      <div className="text-xs text-slate-400 flex items-center gap-2">
                        <span>{c.subscription}</span>
                        <span>&middot;</span>
                        <span>Card on file: •••• {c.card_last4}</span>
                      </div>
                    </td>

                    <td className="py-3.5 px-4 font-semibold text-emerald-400">
                      {formatPaise(c.amount_paise, c.currency)}
                    </td>

                    <td className="py-3.5 px-4">
                      <span className="px-2 py-0.5 rounded text-xs bg-slate-800 text-slate-300 capitalize border border-slate-700/50">
                        {c.failure_reason.replace("_", " ")}
                      </span>
                    </td>

                    <td className="py-3.5 px-4">
                      {getStatusBadge(c.status, c.current_state)}
                    </td>

                    <td className="py-3.5 px-4 text-xs text-slate-400 font-mono">
                      {c.retry_count} {c.retry_count === 1 ? "attempt" : "attempts"}
                    </td>

                    <td className="py-3.5 px-5 text-right" onClick={(e) => e.stopPropagation()}>
                      <div className="flex items-center justify-end gap-2">
                        <button
                          onClick={() => onCallCustomer(c)}
                          className="px-3 py-1.5 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-semibold shadow-md shadow-indigo-600/30 transition-all flex items-center gap-1.5"
                        >
                          <Phone className="w-3.5 h-3.5" />
                          <span>Call</span>
                        </button>
                        <button
                          onClick={() => onSelectCustomer(c)}
                          className="p-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 transition-colors"
                          title="View Customer Details & State"
                        >
                          <ArrowUpRight className="w-4 h-4" />
                        </button>
                      </div>
                    </td>
                  </tr>
                );
              })
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
};
