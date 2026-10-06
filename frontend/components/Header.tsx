"use client";

import React from "react";
import { RotateCcw, ShieldCheck, Activity, PhoneCall } from "lucide-react";

interface HeaderProps {
  onReset: () => void;
  onRefresh: () => void;
  isResetting: boolean;
}

export const Header: React.FC<HeaderProps> = ({ onReset, onRefresh, isResetting }) => {
  return (
    <header className="border-b border-slate-800 bg-slate-900/80 backdrop-blur-md sticky top-0 z-30 px-6 py-4">
      <div className="max-w-7xl mx-auto flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-tr from-indigo-600 to-violet-500 flex items-center justify-center text-white shadow-lg shadow-indigo-500/20">
              <PhoneCall className="w-5 h-5" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h1 className="text-xl font-bold tracking-tight text-white">
                  AUTOPAY RECOVERY SYSTEM
                </h1>
                <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-medium bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                  <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse"></span>
                  OPERATOR ONLINE
                </span>
              </div>
              <p className="text-xs text-slate-400 mt-0.5">
                Voice-agent backend demo &middot; Deterministic Financial Guardrails &middot; Simulated payments
              </p>
            </div>
          </div>
        </div>

        <div className="flex items-center gap-3">
          <div className="hidden sm:flex items-center gap-2 px-3 py-1.5 rounded-lg bg-slate-800/80 border border-slate-700/60 text-xs text-slate-300">
            <ShieldCheck className="w-4 h-4 text-indigo-400" />
            <span>LLM Intent &middot; Backend Action</span>
          </div>

          <button
            onClick={onRefresh}
            className="px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-medium border border-slate-700 transition-colors flex items-center gap-1.5"
          >
            <Activity className="w-3.5 h-3.5" />
            <span>Sync</span>
          </button>

          <button
            onClick={onReset}
            disabled={isResetting}
            className="px-3.5 py-1.5 rounded-lg bg-rose-500/10 hover:bg-rose-500/20 text-rose-300 text-xs font-medium border border-rose-500/30 transition-colors flex items-center gap-1.5 disabled:opacity-50"
            title="Reset all 10 customer records back to payment_failed"
          >
            <RotateCcw className={`w-3.5 h-3.5 ${isResetting ? "animate-spin" : ""}`} />
            <span>Reset Dataset</span>
          </button>
        </div>
      </div>
    </header>
  );
};
