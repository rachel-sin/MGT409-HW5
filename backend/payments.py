"""Applies an approved payment -- the one place in this whole system that
actually moves real money. Everything upstream of this (every MCP tool,
every agent) only reads or recommends; this is the first and only write.

Deliberately NOT called by any agent directly -- it's only ever triggered
by a human clicking "approve" in the dashboard (main.py's approve route),
after approvals.decide() has already recorded who approved it and when.
"""

import sqlite3
from datetime import datetime, timezone

from runtime import REPO_ROOT

DB_PATH = REPO_ROOT / "data" / "campus_customs_new.db"


def apply_payment(amount: float, account: str, kind: str, ref_id: int | None, approved_by: str) -> dict:
    """Deducts `amount` from `account` in cash_accounts and records the
    transaction in payments. Both happen in one transaction -- either both
    succeed or neither does, so cash_accounts and payments can never drift
    out of sync with each other."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        row = conn.execute("SELECT balance FROM cash_accounts WHERE name = ?", (account,)).fetchone()
        if row is None:
            raise ValueError(f"No cash account named {account!r}")
        new_balance = row["balance"] - amount
        now = datetime.now(timezone.utc).isoformat()
        conn.execute(
            "UPDATE cash_accounts SET balance = ?, date = ? WHERE name = ?",
            (new_balance, now[:10], account),
        )
        cursor = conn.execute(
            "INSERT INTO payments (kind, ref_id, amount, account, paid_at, approved_by) VALUES (?, ?, ?, ?, ?, ?)",
            (kind, ref_id, amount, account, now, approved_by),
        )
        conn.commit()
        return {"payment_id": cursor.lastrowid, "account": account, "new_balance": new_balance}
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
