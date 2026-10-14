// Thin wrapper over backend/main.py's routes. No mock data below this line.

import type { AgentEvent, AgentReply, CashBalance, PendingApproval, Ticket } from "./types";

const BASE_URL = "http://localhost:8000";

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE_URL}${path}`, options);
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body.detail ?? `${res.status} ${res.statusText}`);
  }
  return res.json();
}

export function getTickets(): Promise<Ticket[]> {
  return request("/api/tickets");
}

export function runTicket(ticketId: number): Promise<AgentReply> {
  return request(`/api/tickets/${ticketId}/run`, { method: "POST" });
}

export function getEvents(limit = 50): Promise<AgentEvent[]> {
  return request(`/api/events?limit=${limit}`);
}

export interface LiveRunStatus {
  running: boolean;
  steps: { agent: string; message: string | null; tool_calls: { tool_name: string }[] }[];
}

export function getLiveRun(ticketId: number): Promise<LiveRunStatus> {
  return request(`/api/tickets/${ticketId}/live`);
}

export function getApprovals(ticketId?: number): Promise<PendingApproval[]> {
  const query = ticketId != null ? `?ticket_id=${ticketId}` : "";
  return request(`/api/approvals${query}`);
}

export function approvePayment(approvalId: number, decidedBy: string): Promise<{ approval: PendingApproval; payment: unknown }> {
  return request(`/api/approvals/${approvalId}/approve`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ decided_by: decidedBy }),
  });
}

export function confirmPaymentStatus(
  approvalId: number,
  alreadyPaid: boolean,
  decidedBy: string,
): Promise<{ approval: PendingApproval; payment: unknown }> {
  return request(`/api/approvals/${approvalId}/confirm-payment-status`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ already_paid: alreadyPaid, decided_by: decidedBy }),
  });
}

export function getCash(accountName = "checking"): Promise<CashBalance> {
  return request(`/api/cash?account_name=${accountName}`);
}

export function resetDesk(): Promise<{ archived_to: string }> {
  return request("/api/reset", { method: "POST" });
}

/** Events from the most recent run of one ticket -- /api/events is a flat,
 * global recent-activity feed, so this filters to one ticket and keeps
 * only the latest run's events (every event from one run shares the same
 * timestamp, since main.py stamps them from their parent audit entry). */
export function latestRunEvents(allEvents: AgentEvent[], ticketId: number): AgentEvent[] {
  const forTicket = allEvents.filter((e) => e.ticket_id === ticketId);
  if (forTicket.length === 0) return [];
  const latestTimestamp = forTicket.reduce((max, e) => (e.timestamp > max ? e.timestamp : max), forTicket[0].timestamp);
  return forTicket.filter((e) => e.timestamp === latestTimestamp);
}

/** output/audit_trail.json is permanent and never cleared, even across a
 * reset (by design) -- a reset marker just gets appended to it. So
 * restoring "this ticket's current result" from /api/events has to ignore
 * everything before the most recent reset, or a freshly-reset ticket would
 * incorrectly show its old, pre-reset answer. main.py surfaces a reset as
 * an event with agent: "system". */
export function sinceLastReset(allEvents: AgentEvent[]): AgentEvent[] {
  const resets = allEvents.filter((e) => e.agent === "system");
  if (resets.length === 0) return allEvents;
  const lastReset = resets.reduce((max, e) => (e.timestamp > max ? e.timestamp : max), resets[0].timestamp);
  return allEvents.filter((e) => e.timestamp > lastReset);
}
