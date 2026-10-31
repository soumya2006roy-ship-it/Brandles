"""Deterministic visual checks. OCR and font identification remain bounded prototypes."""

from __future__ import annotations

from collections import Counter
from io import BytesIO
import math
import re
from typing import Any

from PIL import Image, ImageOps


HEX_COLOR = re.compile(r"^#[0-9a-fA-F]{6}$")


def _lab(hex_color: str) -> tuple[float, float, float]:
    rgb = [int(hex_color[index:index + 2], 16) / 255 for index in (1, 3, 5)]
    linear = [((value + 0.055) / 1.055) ** 2.4 if value > 0.04045 else value / 12.92 for value in rgb]
    x = (linear[0] * 0.4124 + linear[1] * 0.3576 + linear[2] * 0.1805) / 0.95047
    y = (linear[0] * 0.2126 + linear[1] * 0.7152 + linear[2] * 0.0722)
    z = (linear[0] * 0.0193 + linear[1] * 0.1192 + linear[2] * 0.9505) / 1.08883
    f = lambda value: value ** (1 / 3) if value > 0.008856 else 7.787 * value + 16 / 116
    fx, fy, fz = f(x), f(y), f(z)
    return 116 * fy - 16, 500 * (fx - fy), 200 * (fy - fz)


def delta_e_2000(left: str, right: str) -> float:
    """CIEDE2000 perceptual distance for two sRGB hex colours."""
    l1, a1, b1 = _lab(left)
    l2, a2, b2 = _lab(right)
    c1, c2 = math.hypot(a1, b1), math.hypot(a2, b2)
    c_bar = (c1 + c2) / 2
    g = 0.5 * (1 - math.sqrt(c_bar ** 7 / (c_bar ** 7 + 25 ** 7)))
    ap1, ap2 = (1 + g) * a1, (1 + g) * a2
    cp1, cp2 = math.hypot(ap1, b1), math.hypot(ap2, b2)
    hp1 = math.degrees(math.atan2(b1, ap1)) % 360
    hp2 = math.degrees(math.atan2(b2, ap2)) % 360
    dl = l2 - l1
    dc = cp2 - cp1
    dh_angle = 0 if cp1 * cp2 == 0 else hp2 - hp1
    if cp1 * cp2 and dh_angle > 180:
        dh_angle -= 360
    elif cp1 * cp2 and dh_angle < -180:
        dh_angle += 360
    dh = 2 * math.sqrt(cp1 * cp2) * math.sin(math.radians(dh_angle / 2))
    l_bar = (l1 + l2) / 2
    cp_bar = (cp1 + cp2) / 2
    if cp1 * cp2 == 0:
        hp_bar = hp1 + hp2
    elif abs(hp1 - hp2) <= 180:
        hp_bar = (hp1 + hp2) / 2
    elif hp1 + hp2 < 360:
        hp_bar = (hp1 + hp2 + 360) / 2
    else:
        hp_bar = (hp1 + hp2 - 360) / 2
    t = 1 - 0.17 * math.cos(math.radians(hp_bar - 30)) + 0.24 * math.cos(math.radians(2 * hp_bar)) + 0.32 * math.cos(math.radians(3 * hp_bar + 6)) - 0.20 * math.cos(math.radians(4 * hp_bar - 63))
    sl = 1 + 0.015 * (l_bar - 50) ** 2 / math.sqrt(20 + (l_bar - 50) ** 2)
    sc = 1 + 0.045 * cp_bar
    sh = 1 + 0.015 * cp_bar * t
    delta_theta = 30 * math.exp(-((hp_bar - 275) / 25) ** 2)
    rc = 2 * math.sqrt(cp_bar ** 7 / (cp_bar ** 7 + 25 ** 7))
    rt = -rc * math.sin(math.radians(2 * delta_theta))
    return math.sqrt((dl / sl) ** 2 + (dc / sc) ** 2 + (dh / sh) ** 2 + rt * (dc / sc) * (dh / sh))


def normalize_bbox(box: tuple[int, int, int, int], width: int, height: int) -> dict[str, float]:
    left, top, right, bottom = box
    return {"x": round(max(0, min(1, left / width)), 4), "y": round(max(0, min(1, top / height)), 4),
            "width": round(max(0, min(1, (right - left) / width)), 4), "height": round(max(0, min(1, (bottom - top) / height)), 4)}


def dominant_palette(image_bytes: bytes, limit: int = 5) -> list[dict[str, Any]]:
    image = ImageOps.exif_transpose(Image.open(BytesIO(image_bytes))).convert("RGB")
    image.thumbnail((256, 256))
    quantized = image.quantize(colors=limit, method=Image.Quantize.MEDIANCUT)
    palette = quantized.getpalette() or []
    pixel_values = quantized.get_flattened_data() if hasattr(quantized, "get_flattened_data") else quantized.getdata()
    counts = Counter(pixel_values)
    total = sum(counts.values()) or 1
    return [{"hex": "#%02x%02x%02x" % tuple(palette[index * 3:index * 3 + 3]), "share": round(count / total, 4)}
            for index, count in counts.most_common(limit)]


def confidence_outcome(confidence: float, threshold: float) -> dict[str, Any]:
    bounded = round(max(0.0, min(1.0, confidence)), 3)
    return {"confidence": bounded, "needs_human_review": bounded < threshold}


def visual_findings(*, image_bytes: bytes, color_rules: list[tuple[Any, Any]], logo_matches: list[dict[str, Any]], disclaimer_rules: list[tuple[Any, Any]], ocr_text: str | None, threshold: float = 0.65) -> dict[str, Any]:
    image = ImageOps.exif_transpose(Image.open(BytesIO(image_bytes))).convert("RGB")
    width, height = image.size
    full_bbox = normalize_bbox((0, 0, width, height), width, height)
    palette = dominant_palette(image_bytes)
    findings: list[dict[str, Any]] = []
    palette_result: dict[str, Any] = {"status": "not_configured", "detected": palette, "approved": []}
    color_outliers: list[dict[str, Any]] = []
    color_rule: Any = None
    color_passage: Any = None
    for rule, passage in color_rules:
        colors = [str(value).upper() for value in (rule.parameters or {}).get("colors", []) if isinstance(value, str) and HEX_COLOR.fullmatch(value)]
        if not colors:
            continue
        tolerance = float((rule.parameters or {}).get("tolerance_delta_e", 12))
        comparisons = [{"detected": item["hex"], "share": item["share"], "closest_approved": min(colors, key=lambda color: delta_e_2000(item["hex"], color)), "delta_e": round(min(delta_e_2000(item["hex"], color) for color in colors), 2)} for item in palette]
        outliers = [item for item in comparisons if item["delta_e"] > tolerance and item["share"] >= 0.08]
        palette_result = {"status": "review" if outliers else "pass", "detected": palette, "approved": colors, "tolerance_delta_e": tolerance, "comparisons": comparisons}
        if outliers:
            color_outliers.extend(outliers)
            color_rule, color_passage = rule, passage
    if color_outliers and color_rule and color_passage:
        tolerance = float((color_rule.parameters or {}).get("tolerance_delta_e", 12))
        confidence = min(0.99, 0.55 + max(item["delta_e"] - tolerance for item in color_outliers) / 40)
        findings.append({"finding_type": "brand_color_deviation", "severity": "medium" if confidence >= threshold else "info", "rule_id": color_rule.id, "source_passage_id": color_passage.id, "quoted_excerpt": color_passage.text, "confidence": confidence, "bounding_box": full_bbox, "needs_human_review": confidence < threshold, "explanation": f"Dominant image colours differ from approved colours by more than Delta E {tolerance:g}.", "suggested_fix": "Adjust the image palette to the approved colours and review the poster visually."})

    matching_logo = next((match for match in logo_matches if match.get("matched") and not match.get("deprecated")), None)
    deprecated_logo = next((match for match in logo_matches if match.get("matched") and match.get("deprecated")), None)
    if deprecated_logo:
        findings.append({"finding_type": "deprecated_logo", "severity": "high", "rule_id": deprecated_logo.get("rule_id"), "source_passage_id": deprecated_logo.get("passage_id"), "quoted_excerpt": deprecated_logo.get("quoted_excerpt"), "confidence": deprecated_logo["similarity"], "bounding_box": full_bbox, "needs_human_review": deprecated_logo["similarity"] < threshold, "explanation": f"The image resembles deprecated logo version {deprecated_logo['logo_version']}.", "suggested_fix": "Replace it with a current approved logo version."})
    elif logo_matches and not matching_logo:
        closest = logo_matches[0]
        findings.append({"finding_type": "logo_mismatch", "severity": "medium", "rule_id": closest.get("rule_id"), "source_passage_id": closest.get("passage_id"), "quoted_excerpt": closest.get("quoted_excerpt"), "confidence": min(0.6, closest["similarity"]), "bounding_box": full_bbox, "needs_human_review": True, "explanation": "No current approved logo version matched the image-level perceptual comparison.", "suggested_fix": "Inspect the logo placement and compare it with the approved source manually."})

    typography = {"status": "not_verifiable", "note": "Font family and style cannot be identified reliably from this local image analysis."}
    disclaimer = {"status": "not_configured" if not disclaimer_rules else "not_verifiable", "note": "OCR is optional; text and layout cannot be checked without a configured OCR provider."}
    if ocr_text is not None:
        for rule, passage in disclaimer_rules:
            required = str((rule.parameters or {}).get("value", "")).strip()
            if not required:
                continue
            if required.casefold() in ocr_text.casefold():
                disclaimer = {"status": "pass", "required_text": required}
            else:
                confidence = 0.82
                needs_review = confidence < threshold
                disclaimer = {"status": "review", "required_text": required, "confidence": confidence}
                findings.append({"finding_type": "missing_disclaimer", "severity": "high" if not needs_review else "info", "rule_id": rule.id, "source_passage_id": passage.id, "quoted_excerpt": passage.text, "confidence": confidence, "bounding_box": None, "needs_human_review": needs_review, "explanation": "Configured OCR did not find the exact required disclaimer text.", "suggested_fix": f"Add this required text clearly: {required}"})
            break
    return {"palette": palette_result, "logo": {"status": "deprecated" if deprecated_logo else "pass" if matching_logo else "review" if logo_matches else "not_configured", "matches": logo_matches}, "typography": typography, "disclaimer": disclaimer, "findings": findings, "maturity": "local visual prototype; validate on real brand assets"}
