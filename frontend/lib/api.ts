/** API client and interfaces for Autopay Recovery Voice Agent v2 */

export interface Customer {
  customer_id: string;
  name: string;
  phone?: string;
  amount_paise: number;
  currency: string;
  failure_reason: string;
  retry_count: number;
  status: string;
  subscription: string;
  card_last4: string;
  simulated_outcome: string;
  due_date?: string;
  notes?: string;
  last_call_at?: string;
  recovery_link?: string;
  scheduled_at?: string;
  current_state: string;
}

export interface StatsSummary {
  total_customers: number;
  recovered_count: number;
  recovered_amount_paise: number;
  payment_links_count: number;
  scheduled_count: number;
  declined_count: number;
  cancel_requested_count: number;
  unreachable_count: number;
  currency: string;
}

export function formatPaise(paise?: number, currency = "INR"): string {
  const amount = (paise ?? 0) / 100;
  const symbol = currency === "INR" ? "₹" : "$";
  return `${symbol}${amount.toLocaleString("en-IN")}`;
}

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

// Operator token for the backend's /api/* routes. NEXT_PUBLIC_* values are compiled into the
// browser bundle, so this is only acceptable for a local demo. A real deployment needs a login
// or a server-side proxy that holds the token.
const OPERATOR_TOKEN = process.env.NEXT_PUBLIC_OPERATOR_TOKEN || "";

function authHeaders(extra: Record<string, string> = {}): Record<string, string> {
  return OPERATOR_TOKEN ? { ...extra, Authorization: `Bearer ${OPERATOR_TOKEN}` } : extra;
}

export async function fetchCustomers(): Promise<Customer[]> {
  const res = await fetch(`${API_BASE}/api/customers`, { cache: "no-store", headers: authHeaders() });
  if (!res.ok) throw new Error("Failed to fetch customers");
  return res.json();
}

export async function fetchCustomer(id: string): Promise<Customer> {
  const res = await fetch(`${API_BASE}/api/customers/${id}`, { cache: "no-store", headers: authHeaders() });
  if (!res.ok) throw new Error(`Failed to fetch customer ${id}`);
  return res.json();
}

export async function fetchStats(): Promise<StatsSummary> {
  const res = await fetch(`${API_BASE}/api/stats`, { cache: "no-store", headers: authHeaders() });
  if (!res.ok) throw new Error("Failed to fetch stats");
  return res.json();
}

export async function resetCustomers(): Promise<Customer[]> {
  const res = await fetch(`${API_BASE}/api/customers/reset`, { method: "POST", headers: authHeaders() });
  if (!res.ok) throw new Error("Failed to reset customers");
  return res.json();
}

export async function initiateCall(id: string, mode: "browser" | "sip" = "browser", phoneOverride?: string): Promise<any> {
  const res = await fetch(`${API_BASE}/api/calls`, {
    method: "POST",
    headers: authHeaders({ "Content-Type": "application/json" }),
    body: JSON.stringify({ customer_id: id, mode, phone_number_override: phoneOverride }),
  });
  const data = await res.json();
  if (!res.ok) {
    const detail = typeof data.detail === "string" ? data.detail : data.detail?.code;
    throw new Error(detail || data.message || "Failed to initiate call");
  }
  return data;
}
