"use client";

import React, { useState, useEffect } from "react";
import { Header } from "../components/Header";
import { StatsCards } from "../components/StatsCards";
import { CustomerTable } from "../components/CustomerTable";
import { CallModal } from "../components/CallModal";
import { CustomerDetailModal } from "../components/CustomerDetailModal";
import { Customer, StatsSummary, fetchCustomers, fetchStats, resetCustomers } from "../lib/api";
import { ShieldAlert, Terminal } from "lucide-react";

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
    <div className="min-h-screen flex flex-col bg-paper text-ink">
      <Header
        onReset={handleReset}
        onRefresh={loadData}
        isResetting={isResetting}
      />

      <main className="flex-1 max-w-6xl w-full mx-auto px-5 sm:px-8 py-12 space-y-14">
        {/* Architectural Principle Callout */}
        <section className="border-t border-ink pt-5 grid gap-6 md:grid-cols-[1fr_auto] md:items-end">
          <div className="max-w-2xl">
            <h2 className="label flex items-center gap-2">
              <ShieldAlert className="w-3.5 h-3.5" aria-hidden="true" />
              Core Safety Principle: Separation of Concerns
            </h2>
            <p className="font-serif text-2xl sm:text-3xl leading-tight tracking-tight mt-3">
              <strong className="font-medium underline decoration-accent decoration-[3px] underline-offset-4">LLM decides what the customer means.</strong>{" "}
              <span className="text-mute">Backend decides what the system is allowed to do. The voice model never invents amounts, links, or outcomes.</span>
            </p>
          </div>

          <div className="flex items-center gap-2 label shrink-0">
            <Terminal className="w-3.5 h-3.5" aria-hidden="true" />
            <span>FastAPI &middot; LiveKit Agents &middot; WebRTC / SIP</span>
          </div>
        </section>

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
      <footer className="border-t border-line px-5 sm:px-8 py-6 text-center label">
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
