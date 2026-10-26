"""
Rights and Safety Guardrails module for YouTube Shorts creation.
Enforces copyright compliance, detects licenses (Creative Commons vs Standard YouTube),
calculates Content-ID claim risk for music/major labels, and auto-generates
compliant attribution strings.
"""

from typing import Dict, Any, Optional
import re


MAJOR_LABELS_AND_CORPS = [
    "vevo", "warner", "sony music", "universal music", "columbia records",
    "atlantic records", "def jam", "republic records", "interscope",
    "bighit", "sm entertainment", "yg entertainment", "jyp", "disney",
    "netflix", "hbo", "paramount", "nba", "fifa", "uefa", "nfl"
]


def assess_rights_and_safety(
    video_meta: Dict[str, Any],
    user_rights_declaration: Optional[str] = None
) -> Dict[str, Any]:
    """
    Evaluates copyright risks, detects license terms, and generates
    attribution requirements for the given video metadata.
    
    user_rights_declaration: One of ['own', 'permission', 'creative_commons', 'fair_use_commentary']
    """
    title = (video_meta.get("title") or "").lower()
    uploader = (video_meta.get("uploader") or "").lower()
    channel = (video_meta.get("channel") or "").lower()
    description = (video_meta.get("description") or "").lower()
    license_type = video_meta.get("license") or ""
    
    # Check if explicitly Creative Commons
    is_creative_commons = False
    if "creative commons" in license_type.lower() or "cc-by" in description or "creative commons" in description:
        is_creative_commons = True

    # Content-ID Risk Assessment
    risk_level = "LOW"
    risk_reasons = []

    for corp in MAJOR_LABELS_AND_CORPS:
        if corp in uploader or corp in channel or corp in title:
            risk_level = "HIGH"
            risk_reasons.append(f"Content from or associated with major media entity '{corp.upper()}' has automated Content-ID detection enabled.")
            break

    # Music video detection
    if any(k in title for k in ["official music video", "official audio", "lyric video", "feat.", "ft."]):
        if risk_level != "HIGH":
            risk_level = "MEDIUM"
        risk_reasons.append("Audio appears to contain commercial music tracks prone to Content-ID copyright claims.")

    # Standard YouTube license warning
    if not is_creative_commons and user_rights_declaration not in ["own", "permission"]:
        if risk_level == "LOW":
            risk_level = "MEDIUM"
        risk_reasons.append("Video is marked under 'Standard YouTube License'. Use transformative commentary, voiceover, or smart editing to satisfy Fair Use.")

    # Attribution Generation
    source_url = video_meta.get("webpage_url") or f"https://www.youtube.com/watch?v={video_meta.get('id', '')}"
    uploader_name = video_meta.get("uploader") or video_meta.get("channel") or "Original Creator"
    video_title = video_meta.get("title") or "Original Video"

    attribution_text = (
        f"Original clip: \"{video_title}\" by {uploader_name}\n"
        f"Source: {source_url}\n"
        f"Created with YouTube Shorts AI Studio under transformative fair use/commentary guidelines."
    )

    return {
        "is_creative_commons": is_creative_commons,
        "license_detected": "Creative Commons (CC-BY)" if is_creative_commons else "Standard YouTube License",
        "risk_level": risk_level,
        "risk_reasons": risk_reasons,
        "attribution_required": True,
        "attribution_text": attribution_text,
        "user_declaration_valid": bool(user_rights_declaration),
        "user_rights_declaration": user_rights_declaration
    }
