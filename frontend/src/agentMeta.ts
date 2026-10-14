// Every agent in this system is required to run on the same model --
// there's no per-agent/per-event field for this since it's a fixed,
// system-wide fact, not something that varies per run.
export const MODEL_NAME = "gpt-6-luna";
export const MODEL_PROVIDER = "Portkey";

export const AGENT_LABELS: Record<string, string> = {
  boss: "Boss",
  inventory: "Inventory",
  accounting: "Accounting",
  facilities: "Facilities",
  customer_service: "Customer Service",
  system: "System",
};

export const AGENT_COLORS: Record<string, string> = {
  boss: "#00356b",
  inventory: "#4a7a4f",
  accounting: "#b5791f",
  facilities: "#6b5f4f",
  customer_service: "#a24a3c",
  system: "#8a8072",
};

export function agentLabel(agent: string): string {
  return AGENT_LABELS[agent] ?? agent;
}

export function agentColor(agent: string): string {
  return AGENT_COLORS[agent] ?? "#6b5f4f";
}

export const PLAIN_ENGLISH_QUESTION: Record<number, string> = {
  101: "A customer wants to buy the white Bulldog tee in size S. Can we actually fill this order — and if that size is out of stock, is anything already being done to get more?",
  102: "Our landlord says rent is due in 2 days. How much do we actually owe, do we have enough cash to cover it, and has it already been paid?",
  103: "A student org wants to buy 20 navy hoodies in size M and is asking for a bulk discount. Can we even fill an order that big, and if not fully, is a discount still worth offering on what we do have?",
};
