"""Shared delegation plumbing so every agent can hand work to every other
agent (full connectivity) without the 5 agent modules importing each other
directly -- that would require boss.py to import inventory.py and
inventory.py to import boss.py, a straight circular import. Instead, every
agent file only imports this module and runtime.py; team.py is the one
place that knows about all 5 agents and wires the cross-delegation tools.
"""

from dataclasses import dataclass, field

# Belt-and-suspenders loop guard: `chain` blocks an agent from being asked
# twice in the same ticket (the exact-cycle case, e.g. Boss -> Inventory ->
# Boss), and MAX_CHAIN_LENGTH caps total hops regardless, in case five
# agents each delegate once in a long-but-technically-non-repeating chain.
MAX_CHAIN_LENGTH = 4


@dataclass
class DelegationDeps:
    """Tracks which agents have already touched the current ticket. Starts
    fresh with just the entry agent (see team.py's run_ticket) and grows by
    one name each time a delegation tool hands off to another agent -- never
    shared or mutated across separate ticket runs.

    `audit` is the one exception to "never shared": it's the SAME list
    object passed down through every delegation in one ticket's call tree
    (team.py explicitly carries it forward rather than letting a fresh
    DelegationDeps default to a new empty list), so every agent's tool
    calls -- Boss's own and every specialist it delegates to -- land in one
    ordered trace for that ticket."""

    chain: tuple[str, ...] = ()
    audit: list[dict] = field(default_factory=list)
