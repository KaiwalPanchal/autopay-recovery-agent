"use client";

import React, { useState, useEffect } from "react";
import { Header } from "../components/Header";
import { StatsCards } from "../components/StatsCards";
import { CustomerTable } from "../components/CustomerTable";
import { CallModal } from "../components/CallModal";
import { CustomerDetailModal } from "../components/CustomerDetailModal";
import { Customer, StatsSummary, fetchCustomers, fetchStats, resetCustomers } from "../lib/api";
import { ShieldAlert, Sparkles, Terminal } from "lucide-react";

export default function DashboardPage() {
  const [customers, setCustomers] = useState<Customer[]>([]);
  const [stats, setStats] = useState<StatsSummary | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [isResetting, setIsResetting] = useState<boolean>(false);

  const [callingCustomer, setCallingCustomer] = useState<Customer | null>(null);
  const [selectedCustomer, setSelectedCustomer] = useState<Customer | null>(null);

  const loadData = async () => {
    try {
      const [custList, statsData] = await Promise.all([
        fetchCustomers(),
        fetchStats(),
      ]);
      setCustomers(custList);
      setStats(statsData);
    } catch (err) {
      console.error("Error loading dashboard data:", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
    const interval = setInterval(loadData, 2000); // Polling every 2s for live updates
    return () => clearInterval(interval);
  }, []);

  const handleReset = async () => {
    if (confirm("Reset all 10 customer records back to payment_failed initial state?")) {
      setIsResetting(true);
      try {
        await resetCustomers();
        await loadData();
      } catch (err) {
        console.error("Error resetting data:", err);
      } finally {
        setIsResetting(false);
      }
    }
  };

  return (
    <div className="min-h-screen flex flex-col bg-slate-950 text-slate-100">
      <Header
        onReset={handleReset}
        onRefresh={loadData}
        isResetting={isResetting}
      />

      <main className="flex-1 max-w-7xl w-full mx-auto px-6 py-8 space-y-6">
        {/* Architectural Principle Callout */}
        <div className="p-4 rounded-xl border border-indigo-500/20 bg-indigo-950/20 backdrop-blur-md flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded-lg bg-indigo-600/20 border border-indigo-500/30 text-indigo-400 flex items-center justify-center shrink-0">
              <Sparkles className="w-4 h-4" />
            </div>
            <div>
              <h2 className="text-xs font-bold text-white uppercase tracking-wider">
                Core Safety Principle: Separation of Concerns
              </h2>
              <p className="text-xs text-indigo-200/80">
                <strong>LLM decides what the customer means.</strong> Backend decides what the system is allowed to do. The voice model never invents amounts, links, or outcomes.
              </p>
            </div>
          </div>

          <div className="flex items-center gap-2 text-[11px] font-mono text-slate-400 shrink-0">
            <Terminal className="w-3.5 h-3.5 text-indigo-400" />
            <span>FastAPI &middot; LiveKit Agents &middot; WebRTC / SIP</span>
          </div>
        </div>

        {/* Stats KPIs */}
        <StatsCards stats={stats} />

        {/* Customers Table */}
        <CustomerTable
          customers={customers}
          onSelectCustomer={(c) => setSelectedCustomer(c)}
          onCallCustomer={(c) => setCallingCustomer(c)}
        />
      </main>

      {/* Footer */}
      <footer className="border-t border-slate-900 bg-slate-950 px-6 py-4 text-center text-xs text-slate-500">
        Autopay Recovery System &middot; LiveKit Voice Agent &middot; 10 Fictional Customer Dataset &middot; Deterministic Simulation
      </footer>

      {/* Call Modal */}
      {callingCustomer && (
        <CallModal
          customer={callingCustomer}
          onClose={() => setCallingCustomer(null)}
          onCallCompleted={() => {
            loadData();
          }}
        />
      )}

      {/* Customer Detail Drawer/Modal */}
      {selectedCustomer && (
        <CustomerDetailModal
          customer={selectedCustomer}
          onClose={() => setSelectedCustomer(null)}
          onCallCustomer={(c) => {
            setSelectedCustomer(null);
            setCallingCustomer(c);
          }}
        />
      )}
    </div>
  );
}
