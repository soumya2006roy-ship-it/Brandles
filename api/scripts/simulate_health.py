"""Run a non-persistent campaign-health fixture simulation and print its results."""

from datetime import date, timedelta
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.campaigns.health import evaluate_campaign_health


def main() -> None:
    today = date.today()
    scenarios = [
        ("ready", {"asset_channels": ["Instagram", "Email"], "scan_status": "completed", "scan_is_current": True, "open_severities": []}),
        ("expired", {"ends_at": today - timedelta(days=1)}),
        ("missing-assets", {"asset_channels": []}),
        ("channel-gap", {"asset_channels": ["Instagram"]}),
        ("unsupported-finding", {"open_severities": ["high"]}),
        ("stale-scan", {"scan_status": "completed", "scan_is_current": False}),
        ("critical-finding", {"open_severities": ["critical"]}),
        ("future-start", {"starts_at": today + timedelta(days=7)}),
    ]
    report = []
    for org_number in range(1, 4):
        for campaign_number, (scenario, values) in enumerate(scenarios[:5], start=1):
            data = {
                "starts_at": today - timedelta(days=2),
                "ends_at": today + timedelta(days=10),
                "today": today,
                "channels": ["Instagram", "Email"],
                "asset_channels": ["Instagram", "Email"],
                "scan_status": "completed",
                "scan_is_current": True,
                "open_severities": [],
                "days_since_update": 1,
            }
            data.update(values)
            result = evaluate_campaign_health(**data)
            report.append({
                "organisation": f"Simulation Org {org_number}",
                "campaign": f"Campaign {campaign_number}: {scenario}",
                "scenario": scenario,
                "score": result["score"],
                "status": result["status"],
                "recommendations": result["recommendations"],
            })
    print(json.dumps({"persisted": False, "campaign_count": len(report), "results": report}, ensure_ascii=False, indent=2))
    assert len(report) == 15
    assert sum(row["status"] == "healthy" for row in report) == 3
    assert sum(row["status"] == "critical" for row in report) == 3


if __name__ == "__main__":
    main()
