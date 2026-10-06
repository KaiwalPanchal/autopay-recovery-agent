"use client";

import React from "react";
import { Users, CheckCircle2, Link2, Calendar, XCircle, PhoneOff } from "lucide-react";
import { StatsSummary, formatPaise } from "../lib/api";

interface StatsCardsProps {
  stats: StatsSummary | null;
}

export const StatsCards: React.FC<StatsCardsProps> = ({ stats }) => {
  const recoveredAmountFormatted = formatPaise(stats?.recovered_amount_paise, stats?.currency);

  const cards = [
    {
      title: "Customers",
      value: stats?.total_customers ?? 10,
      subtext: "Failed Autopay Dataset",
      icon: Users,
      color: "text-slate-300",
      bg: "bg-slate-800/60 border-slate-700/60",
    },
    {
      title: "Recovered",
      value: stats?.recovered_count ?? 0,
      subtext: `Total: ${recoveredAmountFormatted}`,
      icon: CheckCircle2,
      color: "text-emerald-400",
      bg: "bg-emerald-500/10 border-emerald-500/20",
    },
    {
      title: "Payment Links",
      value: stats?.payment_links_count ?? 0,
      subtext: "Self-Serve SMS Links",
      icon: Link2,
      color: "text-blue-400",
      bg: "bg-blue-500/10 border-blue-500/20",
    },
    {
      title: "Scheduled",
      value: stats?.scheduled_count ?? 0,
      subtext: "Future Callbacks",
      icon: Calendar,
      color: "text-purple-400",
      bg: "bg-purple-500/10 border-purple-500/20",
    },
    {
      title: "Declined / Cancel",
      value: (stats?.declined_count ?? 0) + (stats?.cancel_requested_count ?? 0),
      subtext: `${stats?.cancel_requested_count ?? 0} cancelled, ${stats?.declined_count ?? 0} declined`,
      icon: XCircle,
      color: "text-amber-400",
      bg: "bg-amber-500/10 border-amber-500/20",
    },
    {
      title: "Unreachable",
      value: stats?.unreachable_count ?? 0,
      subtext: "No Answer / Retry Later",
      icon: PhoneOff,
      color: "text-rose-400",
      bg: "bg-rose-500/10 border-rose-500/20",
    },
  ];

  return (
    <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-3.5 mb-8">
      {cards.map((card, idx) => {
        const Icon = card.icon;
        return (
          <div
            key={idx}
            className={`p-4 rounded-xl border backdrop-blur-md flex flex-col justify-between transition-all hover:scale-[1.02] ${card.bg}`}
          >
            <div className="flex items-center justify-between mb-2">
              <span className="text-xs font-medium text-slate-400">{card.title}</span>
              <Icon className={`w-4 h-4 ${card.color}`} />
            </div>
            <div>
              <div className="text-2xl font-bold tracking-tight text-white mb-0.5">
                {card.value}
              </div>
              <div className="text-[11px] text-slate-400 truncate">
                {card.subtext}
              </div>
            </div>
          </div>
        );
      })}
    </div>
  );
};
