"use client";

import React, { useState } from "react";
import { Phone, Clock, Link2, XCircle, AlertCircle, ArrowUpRight } from "lucide-react";
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

  const chipBase =
    "inline-flex items-center gap-1.5 px-2 py-0.5 rounded-sm border border-ink font-mono text-[11px] uppercase tracking-[0.1em] whitespace-nowrap";

  const getStatusBadge = (status: string, state: string) => {
    const s = status.toLowerCase();
    if (s === "recovered") {
      return (
        <span className={chipBase}>
          <span className="w-2 h-2 bg-accent border border-ink" aria-hidden="true"></span>
          Recovered
        </span>
      );
    }
    if (s === "payment_link_sent") {
      return (
        <span className={chipBase}>
          <Link2 className="w-3 h-3" aria-hidden="true" />
          Link sent
        </span>
      );
    }
    if (s === "scheduled") {
      return (
        <span className={chipBase}>
          <Clock className="w-3 h-3" aria-hidden="true" />
          Scheduled
        </span>
      );
    }
    if (s === "cancel_requested") {
      return (
        <span className={`${chipBase} border-dashed text-mute`}>
          <XCircle className="w-3 h-3" aria-hidden="true" />
          Cancel requested
        </span>
      );
    }
    if (s === "declined") {
      return (
        <span className={`${chipBase} line-through`}>
          <XCircle className="w-3 h-3" aria-hidden="true" />
          Declined
        </span>
      );
    }
    if (s === "in_progress") {
      return (
        <span className={chipBase}>
          <span className="w-2 h-2 bg-accent border border-ink animate-pulse" aria-hidden="true"></span>
          In progress
        </span>
      );
    }
    return (
      <span className={`${chipBase} bg-ink text-paper`}>
        <AlertCircle className="w-3 h-3" aria-hidden="true" />
        Payment failed
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
    <section>
      {/* Table Header Controls */}
      <div className="border-t border-ink pt-4 pb-5 flex flex-col lg:flex-row lg:items-end justify-between gap-5">
        <div>
          <h2 className="font-serif text-3xl font-medium tracking-tight">
            Customer Recovery Queue
          </h2>
          <p className="text-xs text-mute mt-2 max-w-xl">
            10 Authentic customer personas with simulated payment failures &amp; deterministic outcomes
          </p>
        </div>

        {/* Filter Tabs */}
        <div className="flex flex-wrap items-center gap-x-5 gap-y-2" role="group" aria-label="Filter customers">
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
              aria-pressed={filter === tab.id}
              className={`label !text-xs py-1 border-b-[3px] transition-colors ${
                filter === tab.id
                  ? "!text-ink border-accent"
                  : "border-transparent hover:!text-ink"
              }`}
            >
              {tab.label}
            </button>
          ))}
        </div>
      </div>

      {/* Table View */}
      <div className="overflow-x-auto">
        <table className="w-full text-left text-sm text-ink tabular-nums">
          <thead className="border-y border-ink">
            <tr className="label">
              <th className="py-3 pr-4 font-normal">Customer &amp; Plan</th>
              <th className="py-3 px-4 font-normal">Overdue Amount (₹)</th>
              <th className="py-3 px-4 font-normal">Failure Reason</th>
              <th className="py-3 px-4 font-normal">Recovery Status</th>
              <th className="py-3 px-4 font-normal">Retries</th>
              <th className="py-3 pl-4 font-normal text-right">Actions</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-line border-b border-ink">
            {filteredCustomers.length === 0 ? (
              <tr>
                <td colSpan={6} className="py-10 text-center text-mute text-xs">
                  No customers match the current filter.
                </td>
              </tr>
            ) : (
              filteredCustomers.map((c) => {
                return (
                  <tr
                    key={c.customer_id}
                    className="hover:bg-ink/[0.04] transition-colors group cursor-pointer"
                    onClick={() => onSelectCustomer(c)}
                  >
                    <td className="py-4 pr-4">
                      <div className="font-serif text-lg leading-tight flex items-baseline gap-2">
                        {c.name}
                        <span className="text-[10px] font-mono text-mute">
                          {c.customer_id}
                        </span>
                      </div>
                      <div className="text-xs text-mute flex items-center gap-2 mt-0.5">
                        <span>{c.subscription}</span>
                        <span>&middot;</span>
                        <span>Card on file: •••• {c.card_last4}</span>
                      </div>
                    </td>

                    <td className="py-4 px-4 font-mono font-medium">
                      {formatPaise(c.amount_paise, c.currency)}
                    </td>

                    <td className="py-4 px-4 text-xs capitalize text-mute">
                      {c.failure_reason.replace("_", " ")}
                    </td>

                    <td className="py-4 px-4">
                      {getStatusBadge(c.status, c.current_state)}
                    </td>

                    <td className="py-4 px-4 text-xs text-mute font-mono">
                      {c.retry_count} {c.retry_count === 1 ? "attempt" : "attempts"}
                    </td>

                    <td className="py-4 pl-4 text-right" onClick={(e) => e.stopPropagation()}>
                      <div className="flex items-center justify-end gap-2">
                        <button onClick={() => onCallCustomer(c)} className="btn btn-primary">
                          <Phone className="w-3.5 h-3.5" aria-hidden="true" />
                          <span>Call</span>
                        </button>
                        <button
                          onClick={() => onSelectCustomer(c)}
                          className="btn !px-2"
                          title="View Customer Details & State"
                          aria-label={`View details for ${c.name}`}
                        >
                          <ArrowUpRight className="w-4 h-4" aria-hidden="true" />
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
    </section>
  );
};
