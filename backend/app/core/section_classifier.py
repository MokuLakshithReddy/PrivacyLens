import re
from typing import Dict

SECTION_CATEGORY_KEYWORDS = {
    "Information We Collect": [r"collect", r"gather", r"information we", r"personal data", r"types of data"],
    "How We Use Information": [r"use", r"purpose", r"how we use", r"processing", r"utiliz"],
    "Sharing & Disclosure": [r"share", r"disclos", r"third.?part", r"partners", r"transfer to", r"sale of"],
    "Cookies & Tracking Technologies": [r"cookie", r"tracker", r"beacon", r"pixel", r"local storage", r"web beacon"],
    "Third-Party Services": [r"analytics", r"advertising", r"service provider", r"vendors", r"ad networks"],
    "Data Retention": [r"retain", r"retention", r"how long", r"storage period", r"store your"],
    "Your Rights": [r"rights", r"opt.?out", r"delete", r"access", r"california", r"gdpr", r"choices"],
    "International Transfers": [r"international", r"cross.?border", r"transfer", r"eea", r"overseas"],
    "Children's Privacy": [r"children", r"kids", r"minors", r"under 13", r"under 16", r"coppa"],
    "Security & Contact": [r"security", r"protect", r"safeguard", r"contact", r"inquir"]
}

def classify_section_category(section_title: str, section_preview: str = "") -> str:
    combined = f"{section_title} {section_preview}".lower()

    for category, patterns in SECTION_CATEGORY_KEYWORDS.items():
        for pat in patterns:
            if re.search(pat, combined, re.IGNORECASE):
                return category

    return "General Provisions"
