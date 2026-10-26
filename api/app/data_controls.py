"""Workspace data lifecycle jobs."""

from datetime import UTC, datetime, timedelta

from sqlalchemy import delete, select

from app.core.db import SessionLocal
from app.db.models import AuditEvent, Organization, Scan


def purge_expired_scan_history() -> int:
    """Purge completed scan/findings/review details after each org's retention window."""
    removed = 0
    now = datetime.now(UTC)
    with SessionLocal() as db:
        organizations = db.scalars(select(Organization).where(Organization.deleted_at.is_(None))).all()
        for organization in organizations:
            cutoff = now - timedelta(days=organization.retention_days)
            scan_ids = db.scalars(select(Scan.id).where(Scan.organization_id == organization.id, Scan.status.in_(["completed", "stale", "failed", "cancelled"]), Scan.created_at < cutoff)).all()
            if not scan_ids:
                continue
            db.execute(delete(Scan).where(Scan.organization_id == organization.id, Scan.id.in_(scan_ids)))
            db.add(AuditEvent(organization_id=organization.id, action="organization.retention_purged", entity_type="scan_history", entity_id=organization.id, details={"scan_count": len(scan_ids), "retention_days": organization.retention_days}))
            removed += len(scan_ids)
        db.commit()
    return removed
