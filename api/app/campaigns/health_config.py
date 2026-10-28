"""Transparent campaign-health thresholds for the current BrandLens data model."""

CAMPAIGN_HEALTH_THRESHOLDS = {
    "stale_after_days": 30,
    "healthy_min_score": 80,
    "warning_min_score": 50,
    "deductions": {
        "expired": 35,
        "not_started": 12,
        "missing_dates": 8,
        "no_assets": 20,
        "missing_channels": 14,
        "scan_unavailable": 15,
        "open_critical": 35,
        "open_high": 25,
        "open_medium": 10,
        "stale_campaign": 8,
    },
}
