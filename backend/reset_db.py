"""Resets the working database to a fresh copy of the original seed,
without ever touching the permanent audit trail.

What "reset" means here, by design (discussed with the student): the audit
trail (output/audit_trail.json) is never cleared or truncated -- it's meant
to be the permanent record across every run, including resets. Instead,
the mutated working database and any pending approvals are moved (not
deleted) into a timestamped archive folder, a fresh working copy is made
from the untouched original seed, and one marker entry is appended to the
audit trail noting that an archive/reset happened and where the old files
went.
"""

import json
import shutil
from datetime import datetime, timezone

from runtime import REPO_ROOT

ORIGINAL_DB_PATH = REPO_ROOT / "data" / "campus_customs.db"
WORKING_DB_PATH = REPO_ROOT / "data" / "campus_customs_new.db"
PENDING_APPROVALS_PATH = REPO_ROOT / "output" / "pending_approvals.json"
AUDIT_LOG_PATH = REPO_ROOT / "output" / "audit_trail.json"
ARCHIVE_ROOT = REPO_ROOT / "output" / "archive"


def _append_audit_marker(archive_dir: str) -> None:
    entries = []
    if AUDIT_LOG_PATH.exists():
        try:
            entries = json.loads(AUDIT_LOG_PATH.read_text())
        except (json.JSONDecodeError, OSError):
            entries = []
    entries.append(
        {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "event": "reset",
            "archived_to": archive_dir,
        }
    )
    AUDIT_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    AUDIT_LOG_PATH.write_text(json.dumps(entries, indent=2, default=str))


def reset_database() -> dict:
    """Archive the current working db + pending approvals, then rebuild a
    fresh working copy from the untouched original seed. Returns the
    archive folder path so a caller (e.g. the dashboard) can show it."""
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H-%M-%S")
    archive_dir = ARCHIVE_ROOT / f"reset_{timestamp}"
    archive_dir.mkdir(parents=True, exist_ok=True)

    if WORKING_DB_PATH.exists():
        shutil.move(str(WORKING_DB_PATH), str(archive_dir / WORKING_DB_PATH.name))
    if PENDING_APPROVALS_PATH.exists():
        shutil.move(str(PENDING_APPROVALS_PATH), str(archive_dir / PENDING_APPROVALS_PATH.name))

    shutil.copyfile(ORIGINAL_DB_PATH, WORKING_DB_PATH)
    PENDING_APPROVALS_PATH.write_text("[]")

    _append_audit_marker(str(archive_dir.relative_to(REPO_ROOT)))

    return {"archived_to": str(archive_dir.relative_to(REPO_ROOT))}
