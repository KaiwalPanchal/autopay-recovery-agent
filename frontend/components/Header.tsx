"use client";

import React from "react";
import { RotateCcw, Activity } from "lucide-react";

interface HeaderProps {
  onReset: () => void;
  onRefresh: () => void;
  isResetting: boolean;
}

export const Header: React.FC<HeaderProps> = ({ onReset, onRefresh, isResetting }) => {
  return (
    <header className="border-b border-ink bg-paper sticky top-0 z-30 px-5 sm:px-8 py-5">
      <div className="max-w-6xl mx-auto flex flex-col md:flex-row md:items-end justify-between gap-5">
        <div>
          <div className="flex flex-wrap items-center gap-x-4 gap-y-2">
            <h1 className="font-serif text-3xl sm:text-4xl font-medium tracking-tight leading-none">
              Autopay Recovery System
            </h1>
            <span className="inline-flex items-center gap-2 px-2 py-0.5 border border-ink rounded-sm label !text-ink">
              <span className="w-2 h-2 bg-accent border border-ink" aria-hidden="true"></span>
              Operator Online
            </span>
          </div>
          <p className="label mt-3 normal-case !tracking-wide !text-xs">
            Voice-agent backend demo &middot; Deterministic Financial Guardrails &middot; Simulated payments
          </p>
        </div>

        <div className="flex items-center gap-3">
          <span className="hidden lg:inline label">LLM Intent &middot; Backend Action</span>

          <button onClick={onRefresh} className="btn">
            <Activity className="w-3.5 h-3.5" aria-hidden="true" />
            <span>Sync</span>
          </button>

          <button
            onClick={onReset}
            disabled={isResetting}
            className="btn btn-solid"
            title="Reset all 10 customer records back to payment_failed"
          >
            <RotateCcw className={`w-3.5 h-3.5 ${isResetting ? "animate-spin" : ""}`} aria-hidden="true" />
            <span>Reset Dataset</span>
          </button>
        </div>
      </div>
    </header>
  );
};
