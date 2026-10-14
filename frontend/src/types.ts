// Mirrors backend/models.py and main.py's response shapes.

export interface Ticket {
  id: number;
  type: string;
  requester: string;
  subject: string;
  sku: string | null;
  size: string | null;
  qty: number | null;
  lease_id: number | null;
  invoice_id: number | null;
  status: "open" | "resolved";
  notes: string | null;
  created_at: string;
}

export type ApprovalCategory = "payment" | "review" | "payment_pending_confirmation";

export interface AgentReply {
  message: string;
  needs_human_approval: boolean;
  recommended_action: string | null;
  category: ApprovalCategory | null;
  payment_amount: number | null;
  payment_account: string | null;
}

export interface ToolCall {
  tool_name: string;
  args: Record<string, unknown>;
  result?: unknown;
}

export interface AgentEvent {
  ticket_id: number | null;
  agent: string;
  message: string | null;
  needs_human_approval: boolean | null;
  category: ApprovalCategory | null;
  tool_calls: ToolCall[];
  timestamp: string;
}

export interface PendingApproval {
  id: number;
  ticket_id: number;
  message: string;
  recommended_action: string | null;
  category: ApprovalCategory | null;
  payment_amount: number | null;
  payment_account: string | null;
  status: "pending" | "approved" | "rejected";
  created_at: string;
  decided_at: string | null;
  decided_by: string | null;
}

export interface CashBalance {
  name: string;
  balance: number;
  date: string;
}
