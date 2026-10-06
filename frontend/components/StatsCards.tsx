"use client";

import React from "react";
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
      marker: false,
    },
    {
      title: "Recovered",
      value: stats?.recovered_count ?? 0,
      subtext: `Total: ${recoveredAmountFormatted}`,
      marker: true,
    },
    {
      title: "Payment Links",
      value: stats?.payment_links_count ?? 0,
      subtext: "Self-Serve SMS Links",
      marker: false,
    },
    {
      title: "Scheduled",
      value: stats?.scheduled_count ?? 0,
      subtext: "Future Callbacks",
      marker: false,
    },
    {
      title: "Declined / Cancel",
      value: (stats?.declined_count ?? 0) + (stats?.cancel_requested_count ?? 0),
      subtext: `${stats?.cancel_requested_count ?? 0} cancelled, ${stats?.declined_count ?? 0} declined`,
      marker: false,
    },
    {
      title: "Unreachable",
      value: stats?.unreachable_count ?? 0,
      subtext: "No Answer / Retry Later",
      marker: false,
    },
  ];

  return (
    <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-x-6 gap-y-10">
      {cards.map((card, idx) => (
        <div key={idx} className="border-t border-ink pt-3 flex flex-col justify-between min-w-0">
          <span className="label flex items-center gap-2">
            {card.marker && <span className="w-2 h-2 bg-accent border border-ink shrink-0" aria-hidden="true"></span>}
            {card.title}
          </span>
          <div className="numeral text-6xl mt-6 mb-3">{card.value}</div>
          <div className="text-xs text-mute truncate">{card.subtext}</div>
        </div>
      ))}
    </div>
  );
};
