from datetime import date
from typing import Any

from app.campaigns.health_config import CAMPAIGN_HEALTH_THRESHOLDS as THRESHOLDS

_MESSAGES = {
    "en": {
        "date_expired": ("The campaign end date has passed.", "Update the campaign dates before using these assets."),
        "date_future": ("The campaign is scheduled to start in the future.", "Confirm assets and approved offers are valid for the planned launch date."),
        "date_missing": ("The campaign date window is incomplete.", "Add both start and end dates so validity checks have a clear window."),
        "date_ok": ("The campaign is within its configured date window.", ""),
        "assets_none": ("No current assets have been added.", "Add an asset for each campaign channel."),
        "assets_missing": ("No current asset is present for: {channels}.", "Add or restore an asset for every selected channel."),
        "assets_ok": ("Current assets cover all {count} selected channel(s).", ""),
        "scan_missing": ("No current completed scan is available.", "Run a fresh campaign scan before submitting for review."),
        "scan_stale": ("The latest scan is {status} or no longer matches current assets and rules.", "Run a fresh campaign scan before submitting for review."),
        "scan_ok": ("A completed scan matches the current assets and rules.", ""),
        "findings_critical": ("Open Critical findings remain on the latest scan.", "Resolve or dismiss the Critical findings, then rescan."),
        "findings_high": ("Open High findings remain on the latest scan.", "Review and resolve the High findings before review."),
        "findings_medium": ("Open Medium findings remain on the latest scan.", "Review the open findings and record a decision."),
        "findings_ok": ("No open High or Critical findings were found on the latest scan.", ""),
        "freshness_old": ("The campaign has not been updated in {days} days.", "Confirm that dates, assets, and approved guidance are still current."),
        "freshness_ok": ("Campaign activity is within the freshness window.", ""),
    },
    "hi": {
        "date_expired": ("अभियान की समाप्ति तिथि बीत चुकी है।", "इन एसेट का उपयोग करने से पहले अभियान की तारीखें अपडेट करें।"),
        "date_future": ("अभियान भविष्य में शुरू होने वाला है।", "पुष्टि करें कि एसेट और स्वीकृत ऑफ़र लॉन्च की तारीख पर वैध हों।"),
        "date_missing": ("अभियान की तारीख सीमा अधूरी है।", "वैधता जाँच के लिए शुरू और समाप्ति दोनों तारीखें जोड़ें।"),
        "date_ok": ("अभियान निर्धारित तारीख सीमा के भीतर है।", ""),
        "assets_none": ("अभी कोई वर्तमान एसेट नहीं जोड़ा गया है।", "हर अभियान चैनल के लिए एक एसेट जोड़ें।"),
        "assets_missing": ("इन चैनलों के लिए वर्तमान एसेट नहीं है: {channels}।", "हर चुने हुए चैनल के लिए एसेट जोड़ें या पुनर्स्थापित करें।"),
        "assets_ok": ("वर्तमान एसेट सभी {count} चुने हुए चैनलों को कवर करते हैं।", ""),
        "scan_missing": ("कोई वर्तमान पूर्ण स्कैन उपलब्ध नहीं है।", "समीक्षा के लिए भेजने से पहले नया अभियान स्कैन चलाएँ।"),
        "scan_stale": ("नवीनतम स्कैन {status} है या वर्तमान एसेट और नियमों से मेल नहीं खाता।", "समीक्षा के लिए भेजने से पहले नया अभियान स्कैन चलाएँ।"),
        "scan_ok": ("पूर्ण स्कैन वर्तमान एसेट और नियमों से मेल खाता है।", ""),
        "findings_critical": ("नवीनतम स्कैन में गंभीर निष्कर्ष खुले हैं।", "गंभीर निष्कर्षों को हल या खारिज करें, फिर दोबारा स्कैन करें।"),
        "findings_high": ("नवीनतम स्कैन में उच्च प्राथमिकता के निष्कर्ष खुले हैं।", "समीक्षा से पहले उच्च प्राथमिकता के निष्कर्षों की जाँच और समाधान करें।"),
        "findings_medium": ("नवीनतम स्कैन में मध्यम प्राथमिकता के निष्कर्ष खुले हैं।", "खुले निष्कर्षों की जाँच करें और निर्णय दर्ज करें।"),
        "findings_ok": ("नवीनतम स्कैन में कोई खुला उच्च या गंभीर निष्कर्ष नहीं मिला।", ""),
        "freshness_old": ("अभियान {days} दिनों से अपडेट नहीं हुआ है।", "पुष्टि करें कि तारीखें, एसेट और स्वीकृत दिशानिर्देश अब भी सही हैं।"),
        "freshness_ok": ("अभियान की गतिविधि हाल की है।", ""),
    },
    "mr": {
        "date_expired": ("मोहीमेची समाप्ती तारीख निघून गेली आहे.", "हे ॲसेट वापरण्यापूर्वी मोहीमेच्या तारखा अपडेट करा."),
        "date_future": ("मोहीम भविष्यात सुरू होणार आहे.", "ॲसेट आणि मंजूर ऑफर नियोजित लॉन्च तारखेला वैध आहेत याची खात्री करा."),
        "date_missing": ("मोहीमेची तारीख मर्यादा अपूर्ण आहे.", "वैधता तपासण्यासाठी सुरू आणि समाप्ती या दोन्ही तारखा जोडा."),
        "date_ok": ("मोहीम तिच्या निश्चित तारीख मर्यादेत आहे.", ""),
        "assets_none": ("सध्याचे कोणतेही ॲसेट जोडलेले नाहीत.", "प्रत्येक मोहीम चॅनेलसाठी ॲसेट जोडा."),
        "assets_missing": ("या चॅनेलसाठी सध्याचे ॲसेट नाहीत: {channels}.", "प्रत्येक निवडलेल्या चॅनेलसाठी ॲसेट जोडा किंवा पुनर्संचयित करा."),
        "assets_ok": ("सध्याचे ॲसेट सर्व {count} निवडलेली चॅनेल कव्हर करतात.", ""),
        "scan_missing": ("सध्याचा पूर्ण स्कॅन उपलब्ध नाही.", "पुनरावलोकनासाठी पाठवण्यापूर्वी नवीन मोहीम स्कॅन चालवा."),
        "scan_stale": ("नवीनतम स्कॅन {status} आहे किंवा सध्याच्या ॲसेट आणि नियमांशी जुळत नाही.", "पुनरावलोकनासाठी पाठवण्यापूर्वी नवीन मोहीम स्कॅन चालवा."),
        "scan_ok": ("पूर्ण झालेला स्कॅन सध्याच्या ॲसेट आणि नियमांशी जुळतो.", ""),
        "findings_critical": ("नवीनतम स्कॅनमध्ये गंभीर निष्कर्ष खुले आहेत.", "गंभीर निष्कर्ष सोडवा किंवा फेटाळा आणि पुन्हा स्कॅन करा."),
        "findings_high": ("नवीनतम स्कॅनमध्ये उच्च प्राधान्याचे निष्कर्ष खुले आहेत.", "पुनरावलोकनापूर्वी उच्च प्राधान्याचे निष्कर्ष तपासून सोडवा."),
        "findings_medium": ("नवीनतम स्कॅनमध्ये मध्यम प्राधान्याचे निष्कर्ष खुले आहेत.", "खुले निष्कर्ष तपासा आणि निर्णय नोंदवा."),
        "findings_ok": ("नवीनतम स्कॅनमध्ये खुले उच्च किंवा गंभीर निष्कर्ष आढळले नाहीत.", ""),
        "freshness_old": ("मोहीम {days} दिवसांपासून अपडेट झालेली नाही.", "तारखा, ॲसेट आणि मंजूर मार्गदर्शन अजून योग्य आहे याची खात्री करा."),
        "freshness_ok": ("मोहीमेची अलीकडील हालचाल योग्य आहे.", ""),
    },
}


def evaluate_campaign_health(
    *,
    starts_at: date | None,
    ends_at: date | None,
    today: date,
    channels: list[str],
    asset_channels: list[str],
    scan_status: str | None,
    scan_is_current: bool,
    open_severities: list[str],
    days_since_update: int,
    locale: str = "en",
) -> dict[str, Any]:
    """Score only facts currently stored by BrandLens; no invented budget or reach data."""
    checks: list[dict[str, str]] = []
    deductions = THRESHOLDS["deductions"]
    messages = _MESSAGES.get(locale.split(",", 1)[0].split("-", 1)[0].strip().lower(), _MESSAGES["en"])
    score = 100

    def add(key: str, outcome: str, message_key: str, deduction_key: str | None = None, **values: Any) -> None:
        nonlocal score
        if deduction_key:
            score -= deductions[deduction_key]
        detail, recommendation = messages.get(message_key, _MESSAGES["en"][message_key])
        detail = detail.format(**values)
        recommendation = recommendation.format(**values)
        checks.append({"key": key, "status": outcome, "detail": detail, "recommendation": recommendation or ""})

    if ends_at and ends_at < today:
        add("date_window", "fail", "date_expired", "expired")
    elif starts_at and starts_at > today:
        add("date_window", "warning", "date_future", "not_started")
    elif not starts_at or not ends_at:
        add("date_window", "warning", "date_missing", "missing_dates")
    else:
        add("date_window", "pass", "date_ok")

    expected = {channel.casefold() for channel in channels}
    provided = {channel.casefold() for channel in asset_channels}
    missing = [channel for channel in channels if channel.casefold() not in provided]
    if not asset_channels:
        add("assets", "warning", "assets_none", "no_assets")
    elif missing:
        add("assets", "warning", "assets_missing", "missing_channels", channels=", ".join(missing))
    else:
        add("assets", "pass", "assets_ok", count=len(expected))

    if scan_status != "completed" or not scan_is_current:
        key = "scan_missing" if not scan_status else "scan_stale"
        add("scan", "warning", key, "scan_unavailable", status=(scan_status or "unknown").replace("_", " "))
    else:
        add("scan", "pass", "scan_ok")

    severities = [item.casefold() for item in open_severities]
    if "critical" in severities:
        add("findings", "fail", "findings_critical", "open_critical")
    elif "high" in severities:
        add("findings", "warning", "findings_high", "open_high")
    elif "medium" in severities:
        add("findings", "warning", "findings_medium", "open_medium")
    else:
        add("findings", "pass", "findings_ok")

    if days_since_update > THRESHOLDS["stale_after_days"]:
        add("freshness", "warning", "freshness_old", "stale_campaign", days=days_since_update)
    else:
        add("freshness", "pass", "freshness_ok")

    score = max(0, min(100, score))
    if any(check["key"] == "date_window" and check["status"] == "fail" for check in checks) or "critical" in severities or score < THRESHOLDS["warning_min_score"]:
        status = "critical"
    elif score < THRESHOLDS["healthy_min_score"] or any(check["status"] == "warning" for check in checks):
        status = "warning"
    else:
        status = "healthy"
    return {"score": score, "status": status, "checks": checks, "recommendations": [check["recommendation"] for check in checks if check["recommendation"]]}
