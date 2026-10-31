"""Brand Health analytics built from persisted scans, findings, reviews and audit events.

Scores are governance indicators, not measurements of audience or campaign outcomes.
"""

from collections import Counter, defaultdict
from datetime import date, datetime, timedelta
from statistics import median
from typing import Any


SEVERITY_WEIGHTS = {"critical": 25, "high": 15, "medium": 8, "low": 3}
OPEN_STATES = {"open", "clarification_requested"}


def compliance_score(findings: list[Any], asset_count: int) -> int:
    """Return 0–100 based on open severity-weighted issues per current asset.

    A maximum of 40 weighted points per asset maps to a zero score. Resolved and
    dismissed items are excluded because they no longer represent open risk.
    """
    capacity = max(1, asset_count) * 40
    penalty = sum(SEVERITY_WEIGHTS.get(item.severity, 0) for item in findings if item.status in OPEN_STATES)
    return max(0, round(100 * (1 - min(penalty, capacity) / capacity)))


def median_minutes(values: list[float]) -> float | None:
    return round(median(values), 1) if values else None


def make_trend(scans: list[Any], findings_by_scan: dict[str, list[Any]], assets_by_campaign: dict[str, int], start: date, end: date, granularity: str) -> list[dict[str, Any]]:
    buckets: dict[str, list[tuple[int, int]]] = defaultdict(list)
    for scan in scans:
        created = scan.created_at.date()
        if granularity == "weekly":
            created = created - timedelta(days=created.weekday())
        key = created.isoformat()
        campaign_key = scan.campaign_id or "unassigned"
        findings = findings_by_scan.get(scan.id, [])
        buckets[key].append((compliance_score(findings, assets_by_campaign.get(campaign_key, 1)), 1))
    output: list[dict[str, Any]] = []
    cursor = start
    if granularity == "weekly":
        cursor = cursor - timedelta(days=cursor.weekday())
    while cursor <= end:
        key = cursor.isoformat()
        rows = buckets.get(key, [])
        output.append({"date": key, "compliance_score": round(sum(score for score, _ in rows) / len(rows)) if rows else None, "scans": len(rows)})
        cursor += timedelta(days=7 if granularity == "weekly" else 1)
    return output


def aggregate_analytics(*, scans: list[Any], findings: list[Any], assets: list[Any], reviews: list[Any], audit_events: list[Any], start: date, end: date, granularity: str = "daily") -> dict[str, Any]:
    """Build stable analytics payload. Callers must pass tenant- and filter-scoped rows."""
    findings_by_scan: dict[str, list[Any]] = defaultdict(list)
    scans_by_id = {scan.id: scan for scan in scans}
    for finding in findings:
        findings_by_scan[finding.scan_id].append(finding)
    assets_by_campaign = Counter(asset.campaign_id for asset in assets)

    total = len(findings)
    violation_counts = Counter(item.finding_type for item in findings)
    violations = [{"type": kind, "count": count, "percentage": round(count * 100 / total, 1) if total else 0,
                   "open_count": sum(1 for item in findings if item.finding_type == kind and item.status in OPEN_STATES)}
                  for kind, count in violation_counts.most_common()]
    open_findings = sum(1 for item in findings if item.status in OPEN_STATES)

    scores = [compliance_score(findings_by_scan.get(scan.id, []), assets_by_campaign.get(scan.campaign_id or "unassigned", 1)) for scan in scans if scan.status == "completed"]
    scan_durations: list[float] = []
    findings_by_id = {item.id: item for item in findings}
    for event in audit_events:
        if event.action not in {"finding.resolved", "finding.dismissed"}:
            continue
        finding = findings_by_id.get(event.entity_id)
        scan = scans_by_id.get(finding.scan_id) if finding else None
        if scan:
            scan_durations.append(max(0.0, (event.created_at - scan.created_at).total_seconds() / 60))
    review_durations: list[float] = []
    reviewer_durations: dict[str, list[float]] = defaultdict(list)
    for review in reviews:
        scan = scans_by_id.get(review.scan_id)
        if scan and review.decision in {"approved", "rejected", "changes_requested"}:
            duration = max(0.0, (review.created_at - scan.created_at).total_seconds() / 60)
            review_durations.append(duration)
            if review.reviewer_user_id:
                reviewer_durations[review.reviewer_user_id].append(duration)
    all_turnaround = scan_durations + review_durations

    by_rule: dict[str, list[Any]] = defaultdict(list)
    resolved_at: dict[str, datetime] = {}
    for event in audit_events:
        if event.action in {"finding.resolved", "finding.dismissed"} and event.entity_id in findings_by_id:
            resolved_at[event.entity_id] = event.created_at
    for item in findings:
        by_rule[item.rule_id or item.finding_type].append(item)
    confusing_rules = []
    for rule_id, rows in by_rule.items():
        dismissed = sum(1 for item in rows if item.status == "dismissed")
        # Repeat heuristic: count findings created after a same-rule finding had already
        # been resolved or dismissed. This is a recurring-flag signal, not proof that a
        # person reintroduced the exact same content or that the rule is wrong.
        rule_resolutions = [resolved_at[item.id] for item in rows if item.id in resolved_at]
        repeat_count = sum(1 for item in rows if any(when < item.created_at for when in rule_resolutions))
        dismissal_rate = round(dismissed * 100 / len(rows), 1) if rows else 0
        repeat_rate = round(repeat_count * 100 / len(rows), 1) if rows else 0
        if dismissal_rate >= 25 or repeat_rate >= 30:
            action = "Review evidence and wording" if dismissal_rate >= 25 else "Consider refresher guidance"
            confusing_rules.append({"rule_id": rule_id, "finding_type": rows[0].finding_type, "count": len(rows), "dismissal_rate": dismissal_rate, "repeat_rate": repeat_rate, "suggested_action": action})
    confusing_rules.sort(key=lambda row: (row["dismissal_rate"] + row["repeat_rate"], row["count"]), reverse=True)

    campaign_map: dict[str, dict[str, Any]] = {}
    for asset in assets:
        campaign_map.setdefault(asset.campaign_id, {"campaign_id": asset.campaign_id, "campaign_name": asset.campaign_name,
            "channels": set(), "asset_count": 0, "scan_ids": set(), "findings": []})
        campaign_map[asset.campaign_id]["channels"].add(asset.channel)
        campaign_map[asset.campaign_id]["asset_count"] += 1
    scan_campaigns: dict[str, list[Any]] = defaultdict(list)
    for scan in scans:
        if scan.campaign_id:
            scan_campaigns[scan.campaign_id].append(scan)
            if scan.campaign_id in campaign_map:
                campaign_map[scan.campaign_id]["scan_ids"].add(scan.id)
    for item in findings:
        if item.campaign_id in campaign_map:
            campaign_map[item.campaign_id]["findings"].append(item)
    turnaround_by_campaign: dict[str, list[float]] = defaultdict(list)
    for event in audit_events:
        finding = findings_by_id.get(event.entity_id)
        if finding and finding.campaign_id:
            scan = scans_by_id.get(finding.scan_id)
            if scan:
                turnaround_by_campaign[finding.campaign_id].append(max(0.0, (event.created_at - scan.created_at).total_seconds() / 60))
    for review in reviews:
        scan = scans_by_id.get(review.scan_id)
        if scan and scan.campaign_id and review.decision in {"approved", "rejected", "changes_requested"}:
            turnaround_by_campaign[scan.campaign_id].append(max(0.0, (review.created_at - scan.created_at).total_seconds() / 60))
    campaigns = []
    for campaign_id, row in campaign_map.items():
        campaign_scans = scan_campaigns.get(campaign_id, [])
        campaign_scores = [compliance_score(findings_by_scan.get(scan.id, []), row["asset_count"]) for scan in campaign_scans if scan.status == "completed"]
        campaigns.append({"campaign_id": campaign_id, "campaign_name": row["campaign_name"], "channels": sorted(row["channels"]),
            "assets": row["asset_count"], "scans": len(campaign_scans), "compliance_score": round(sum(campaign_scores) / len(campaign_scores)) if campaign_scores else None,
            "violation_rate": round(len({item.asset_id for item in row["findings"] if item.asset_id}) * 100 / max(1, row["asset_count"]), 1),
            "open_findings": sum(1 for item in row["findings"] if item.status in OPEN_STATES),
            "average_turnaround_minutes": round(sum(turnaround_by_campaign[campaign_id]) / len(turnaround_by_campaign[campaign_id]), 1) if turnaround_by_campaign[campaign_id] else None})
    campaigns.sort(key=lambda row: row["campaign_name"].casefold())

    return {"period": {"from": start.isoformat(), "to": end.isoformat(), "granularity": granularity},
        "summary": {"compliance_score": round(sum(scores) / len(scores)) if scores else None, "open_findings": open_findings,
            "open_findings_percentage": round(open_findings * 100 / total, 1) if total else 0,
            "average_review_minutes": round(sum(all_turnaround) / len(all_turnaround), 1) if all_turnaround else None,
            "scans": len(scans), "completed_scans": sum(1 for scan in scans if scan.status == "completed"), "findings": total},
        "violations": violations, "trend": make_trend(scans, findings_by_scan, assets_by_campaign, start, end, granularity),
        "review_times": {"average_minutes": round(sum(all_turnaround) / len(all_turnaround), 1) if all_turnaround else None,
            "median_minutes": median_minutes(all_turnaround), "resolved_findings": len(scan_durations), "decided_reviews": len(review_durations),
            "by_reviewer": [{"reviewer_id": key, "average_minutes": round(sum(values) / len(values), 1), "decisions": len(values)} for key, values in sorted(reviewer_durations.items())]},
        "confusing_rules": confusing_rules, "campaigns": campaigns}
