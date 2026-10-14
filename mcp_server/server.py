"""Campus Customs MCP server.

Exposes read-only tools over data/campus_customs_new.db so every agent in
this assignment reads the shop's real data instead of inventing it.
"""

from pathlib import Path
import sqlite3

from fastmcp import FastMCP

DB_PATH = Path(__file__).resolve().parent.parent / "data" / "campus_customs_new.db"

mcp = FastMCP("campus-customs")


def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


@mcp.tool
def get_inventory_level(sku: str, size: str) -> dict:
    """Look up the real on-hand quantity for one SKU/size in the inventory table.

    Use this before saying an item is in or out of stock. Never guess a
    quantity -- if the SKU/size pair has no row, this says so explicitly
    instead of assuming it's zero or unavailable.
    """
    with _connect() as conn:
        row = conn.execute(
            "SELECT sku, name, size, qty, location FROM inventory WHERE sku = ? AND size = ?",
            (sku, size),
        ).fetchone()
    if row is None:
        return {
            "found": False,
            "sku": sku,
            "size": size,
            "message": "No inventory record for this SKU/size.",
        }
    return {"found": True, **dict(row)}


@mcp.tool
def get_lease_details(lease_id: int) -> dict:
    """Look up the real rent amount, due date, and landlord for one lease.

    Use this to confirm what a rent-related ticket actually owes and when.
    Never invent a rent figure -- if the lease_id doesn't exist, this says
    so explicitly.
    """
    with _connect() as conn:
        row = conn.execute(
            "SELECT id, space_name, landlord, monthly_rent, next_due, notes FROM leases WHERE id = ?",
            (lease_id,),
        ).fetchone()
    if row is None:
        return {"found": False, "lease_id": lease_id, "message": "No lease with this id."}
    return {"found": True, **dict(row)}


@mcp.tool
def get_invoice_details(invoice_id: int) -> dict:
    """Look up the real amount, due date, status, and description for one invoice.

    Use this to confirm whether a vendor invoice linked to a ticket is real,
    paid or open, and overdue. Never invent invoice data -- if the
    invoice_id doesn't exist, this says so explicitly.
    """
    with _connect() as conn:
        row = conn.execute(
            "SELECT id, vendor_id, amount, due_date, status, description FROM invoices WHERE id = ?",
            (invoice_id,),
        ).fetchone()
    if row is None:
        return {"found": False, "invoice_id": invoice_id, "message": "No invoice with this id."}
    return {"found": True, **dict(row)}


@mcp.tool
def get_pricing(sku: str) -> dict:
    """Look up the real unit cost and list price for one SKU.

    Use this to evaluate whether a discount request still leaves a healthy
    margin. Never invent a cost or price -- if the sku doesn't exist, this
    says so explicitly.
    """
    with _connect() as conn:
        row = conn.execute(
            "SELECT sku, unit_cost, list_price FROM pricing WHERE sku = ?",
            (sku,),
        ).fetchone()
    if row is None:
        return {"found": False, "sku": sku, "message": "No pricing record for this SKU."}
    return {"found": True, **dict(row)}


@mcp.tool
def get_cash_balance(account_name: str) -> dict:
    """Look up the real balance and as-of date for one cash account.

    Use this to confirm whether the shop can actually afford a payment
    before recommending it. Never invent a balance -- if the account name
    doesn't exist, this says so explicitly.
    """
    with _connect() as conn:
        row = conn.execute(
            "SELECT name, balance, date FROM cash_accounts WHERE name = ?",
            (account_name,),
        ).fetchone()
    if row is None:
        return {"found": False, "account_name": account_name, "message": "No cash account with this name."}
    return {"found": True, **dict(row)}


@mcp.tool
def get_vendor_details(vendor_id: int) -> dict:
    """Look up the real name, specialty, and lead time for one vendor.

    Use this to tell a customer or ticket a real restock/reprint timeline
    instead of guessing one. Never invent a vendor or lead time -- if the
    vendor_id doesn't exist, this says so explicitly.
    """
    with _connect() as conn:
        row = conn.execute(
            "SELECT id, name, specialty, lead_days FROM vendors WHERE id = ?",
            (vendor_id,),
        ).fetchone()
    if row is None:
        return {"found": False, "vendor_id": vendor_id, "message": "No vendor with this id."}
    return {"found": True, **dict(row)}


if __name__ == "__main__":
    mcp.run()
