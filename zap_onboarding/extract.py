from __future__ import annotations

import re
from dataclasses import dataclass, field

from zap_onboarding.crawler import FetchedPage


_PHONE_RE = re.compile(
    r"\b05\d(?:\s*|-)?\d{7}\b|"
    r"\b0(?:2|3|4|8|9)(?:\s*|-)?\d{3}(?:\s*|-)?\d{4}\b|"
    r"\b07\d(?:\s*|-)?\d{3}(?:\s*|-)?\d{4}\b|"
    r"(?:\+972)(?:\s*|-)?(?:5\d)(?:\s*|-)?\d{3}(?:\s*|-)?\d{4}\b"
)
_EMAIL_RE = re.compile(r"[a-zA-Z0-9_.%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}")
_WA_ME_RE = re.compile(r"(?:https?://)?(?:wa\.me|api\.whatsapp\.com)/(?:send\?phone=)?(\d+)", re.I)
_WA_CONTEXT_RE = re.compile(r"(?:whatsapp|וואטסאפ)[^\d]{0,20}(9725\d{8}|05\d{8})", re.I)

_CATEGORY_HINTS_HE = [
    ("התקנת מזגנים", ["התקנה", "install"]),
    ("תיקון ושירות", ["תיקון", "שירות", "repair", "service"]),
    ("מיזוג מסחרי", ["מסחר", "commercial", "עסק", "משרד"]),
    ("מיזוג ביתי", ["בית", "דירה", "home", "residential"]),
    ("תכנון וביצוע", ["תכנון", "ביצוע", "פרויקט"]),
    ("חידוש/החלפה", ["חידוש", "החלפה", "upgrade"]),
    ("אחר", []),
]


def _normalize_phone(raw: str) -> str:
    digits = re.sub(r"\D", "", raw)
    if digits.startswith("972"):
        digits = "0" + digits[3:]
    return digits


@dataclass
class ExtractedProfile:
    phones: list[str] = field(default_factory=list)
    emails: list[str] = field(default_factory=list)
    whatsapp_numbers: list[str] = field(default_factory=list)
    addresses: list[str] = field(default_factory=list)
    business_name_guess: str = ""
    region_guess: str = ""
    product_categories: list[str] = field(default_factory=list)
    page_titles: list[str] = field(default_factory=list)
    source_urls: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)


def _dedupe_preserve(seq: list[str]) -> list[str]:
    out, seen = [], set()
    for x in seq:
        k = x.strip()
        if k and k not in seen:
            seen.add(k)
            out.append(k)
    return out


def extract_from_pages(pages: list[FetchedPage], region_hint: str = "") -> ExtractedProfile:
    prof = ExtractedProfile()
    all_text_parts: list[str] = []
    for p in pages:
        if p.error or not p.text_snippet:
            if p.error:
                prof.notes.append(f"שגיאה ב-{p.url}: {p.error}")
            continue
        prof.source_urls.append(p.url)
        if p.title:
            prof.page_titles.append(p.title)
        blob = f"{p.title}\n{p.text_snippet}"
        all_text_parts.append(blob)
        html_blob = p.html or ""

        scan = f"{blob}\n{html_blob[:200000]}"
        for m in _PHONE_RE.findall(scan):
            prof.phones.append(_normalize_phone(m))
        for m in _EMAIL_RE.findall(scan):
            prof.emails.append(m.lower())
        for m in _WA_ME_RE.finditer(scan):
            if m.group(1):
                prof.whatsapp_numbers.append(_normalize_phone(m.group(1)))
        for m in _WA_CONTEXT_RE.findall(scan):
            if m:
                prof.whatsapp_numbers.append(_normalize_phone(m))

    big = "\n".join(all_text_parts)
    if region_hint:
        prof.region_guess = region_hint

    # ניחוי שם עסק מכותרת דף ראשונה עם "|" או מקף
    for t in prof.page_titles:
        if not t:
            continue
        parts = re.split(r"\s*[|\-–]\s*", t, maxsplit=1)
        cand = parts[0].strip()
        if 3 < len(cand) < 80:
            prof.business_name_guess = cand
            break

    # כתובות פשוטות (מילות מפתח ישראל)
    addr_kw = re.findall(
        r"([א-ת\d\s\.'\-]{10,80}(?:רחוב|שדרות|כיכר|דרך)[א-ת\d\s\.'\-]{5,80})",
        big,
    )
    prof.addresses.extend(addr_kw[:5])

    # קטגוריות לפי מילות מפתח
    low = big.lower()
    cats: list[str] = []
    for label, keys in _CATEGORY_HINTS_HE:
        if label == "אחר":
            continue
        for k in keys:
            if k.lower() in low or k in big:
                cats.append(label)
                break
    if not cats:
        cats = ["שירותי מיזוג אוויר (כללי)"]
    prof.product_categories = _dedupe_preserve(cats)

    prof.phones = _dedupe_preserve(prof.phones)
    prof.emails = _dedupe_preserve(prof.emails)
    prof.whatsapp_numbers = _dedupe_preserve(prof.whatsapp_numbers)
    prof.page_titles = _dedupe_preserve(prof.page_titles)
    prof.source_urls = _dedupe_preserve(prof.source_urls)
    prof.addresses = _dedupe_preserve(prof.addresses)[:8]

    return prof
