from __future__ import annotations

import json
import os
from dataclasses import asdict

from zap_onboarding.extract import ExtractedProfile


def _template_client_card(
    customer_display_name: str,
    segment: str,
    prof: ExtractedProfile,
) -> str:
    lines = [
        "## כרטיס לקוח — מפיק זאפ",
        "",
        f"**שם לקוח (פנימי):** {customer_display_name}",
        f"**קטגוריית עסק:** {segment}",
        "",
        "### פרטי קשר שזוהו אוטומטית",
        f"- טלפונים: {', '.join(prof.phones) or 'לא זוהו — לאשר בשיחה'}",
        f"- דוא\"ל: {', '.join(prof.emails) or 'לא זוהה'}",
        f"- וואטסאפ: {', '.join(prof.whatsapp_numbers) or 'לא זוהה'}",
        f"- אזור פעילות (הערה): {prof.region_guess or 'לפי אתר — לאשר'}",
        "",
        "### זיהוי עסק",
        f"- שם עסק (השערה מכותרת): {prof.business_name_guess or 'לא זוהה'}",
        f"- קטגוריות שירות/מוצר: {', '.join(prof.product_categories)}",
        "",
        "### נכסים דיגיטליים שנסרקו",
    ]
    for u in prof.source_urls:
        lines.append(f"- {u}")
    if prof.page_titles:
        lines.extend(["", "### כותרות עמודים", *[f"- {t}" for t in prof.page_titles[:12]]])
    if prof.addresses:
        lines.extend(["", "### כתובות (טיוטה)", *[f"- {a.strip()}" for a in prof.addresses[:5]]])
    if prof.notes:
        lines.extend(["", "### הערות טכניות", *[f"- {n}" for n in prof.notes]])
    lines.extend(
        [
            "",
            "### פעולות המשך למפיק",
            "- לאמת כל פרט קשר מול הלקוח",
            "- לוודא עקביות בין האתר העצמאי למיניסייט בדפי זהב",
            "- לעדכן CRM לאחר השיחה",
        ]
    )
    return "\n".join(lines)


def _template_onboarding_script(
    customer_display_name: str,
    segment: str,
    prof: ExtractedProfile,
) -> str:
    name_line = prof.business_name_guess or customer_display_name
    phone = prof.phones[0] if prof.phones else "[מספר]"
    cats = ", ".join(prof.product_categories)
    region = prof.region_guess or "אזור הקריות והסביבה"

    return f"""שלום, מדברים מזאפ — הגענו אליכם לגבי האתר החדש והמיניסייט בדפי זהב.

פתיחה קצרה:
- אנחנו מלווים את {name_line} בנוכחות הדיגיטלית דרך האינדקס והאתר.
- ראינו שאתם מתמחים ב{cats} — נשמח לוודא שהמידע מוצג נכון ללקוחות באזור {region}.

שאלות לאימות (2–3 דקות):
1. האם מספר הטלפון הראשי לקבלת פניות הוא {phone}? יש מספר נוסף לוואטסאפ או חירום?
2. אילו שירותים הכי חשובים לכם להדגיש החודש — התקנות, תיקונים, או תחזוקה?
3. האם יש תמחור קבוע (למשל ביקור טכנאי) שתרצו שיופיע במפורש?

ציפיות והמשך:
- נעדכן את כרטיס הלקוח במערכת לאחר השיחה ונסנכרן בין העמודים.
- נשלח לכם בוואטסאפ/מייל סיכום קצר של מה שסיכמנו.

תודה רבה, יום טוב."""


def synthesize_with_openai(customer_display_name: str, segment: str, prof: ExtractedProfile) -> tuple[str, str] | None:
    key = os.environ.get("OPENAI_API_KEY")
    if not key:
        return None
    try:
        from openai import OpenAI
    except ImportError:
        return None

    client = OpenAI()
    payload = {
        "customer_display_name": customer_display_name,
        "segment": segment,
        "extracted": asdict(prof),
    }
    sys = (
        "אתה מומחה הצטרפות לקוחות (Onboarding) בחברת זאפ ללקוחות SMB בישראל. "
        "החזר JSON בלבד עם המפתחות: client_card_md, onboarding_call_script. "
        "client_card_md — מארקדאון בעברית למפיק הפנימי. "
        "onboarding_call_script — תסריט שיחה קצר ומכובד לשליחה ללקוח (SMS/מייל/וואטסאפ)."
    )
    user = (
        "להלן נתונים שחולצו מסריקת אתרים. נסח כרטיס לקוח מלא ותסריט מותאם:\n"
        + json.dumps(payload, ensure_ascii=False, indent=2)
    )
    try:
        r = client.chat.completions.create(
            model=os.environ.get("OPENAI_MODEL", "gpt-4o-mini"),
            messages=[{"role": "system", "content": sys}, {"role": "user", "content": user}],
            temperature=0.4,
        )
        text = (r.choices[0].message.content or "").strip()
        if text.startswith("```"):
            text = text.split("\n", 1)[-1].rsplit("```", 1)[0].strip()
        data = json.loads(text)
        return data.get("client_card_md", ""), data.get("onboarding_call_script", "")
    except Exception:
        return None


def build_outputs(
    customer_display_name: str,
    segment: str,
    prof: ExtractedProfile,
) -> tuple[str, str, str]:
    """מחזיר: (כרטיס לקוח, תסריט, מקור_סינתזה)."""
    ai = synthesize_with_openai(customer_display_name, segment, prof)
    if ai and ai[0] and ai[1]:
        return ai[0], ai[1], "openai"
    return (
        _template_client_card(customer_display_name, segment, prof),
        _template_onboarding_script(customer_display_name, segment, prof),
        "template",
    )
