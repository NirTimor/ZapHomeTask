# אב־טיפוס: אוטומציית Onboarding ללקוח עסקי חדש (זאפ)

מטלת בית בתחום חווית הלקוח — תהליך הקמה ללקוח בסגמנט **טכנאי מזגנים** עם **אתר של חמישה עמודים** ו־**מיניסייט בדפי זהב** (אזור הקריות).

## מה הכלי עושה

1. **סריקת נכסים דיגיטליים** — אוסף עמודי HTML מאתר הלקוח (ולמיניסייט באתר אינדקס נפרד), ב־BFS מוגבל ומנומס (User-Agent, timeout, השהיה קצרה בין בקשות).
2. **חילוץ מידע** — זיהוי שפתי ודפוסיRegexp לטלפונים (נייד, קווי, בינלאומי), דוא"ל, קישורי וואטסאפ (`wa.me` גם מתוך `href`), כתובות טקסטואליות פשוטות, והיסק **קטגוריות שירות** לפי מילות מפתח (התקנה, תיקון, מסחרי, ביתי וכו׳).
3. **כרטיס לקוח + תסריט Onboarding** — ניסוח אוטומטי:
   - **ללא API**: תבניות מלאות בעברית (מסמך Markdown למפיק + הודעת פתיחה/תסריט ללקוח).
   ⚙️ **עם `OPENAI_API_KEY`** (ואופציונית `pip install openai`): ניסוח עשיר יותר באמצעות מודל שמחזיר JSON (`client_card_md`, `onboarding_call_script`).
4. **רישום CRM** — אירוע `onboarding_pack_generated` נכתב ל־`data/crm_events.jsonl` (זמן UTC, מזהה לקוח, מטא־דאטה).

## התקנה

```bash
python -m venv .venv
# Windows:
.\.venv\Scripts\pip install -r requirements.txt
# macOS/Linux:
# source .venv/bin/activate && pip install -r requirements.txt
```

לשימוש ב־OpenAI (אופציונלי):

```bash
pip install openai
set OPENAI_API_KEY=...          # Windows cmd
# $env:OPENAI_API_KEY="..."   # PowerShell
```

## הרצה

**הדגמה מקומית (ללא אינטרנט)** — קבצי HTML לדוגמה מדמים אתר + מיניסייט:

```bash
python -m zap_onboarding --config config.demo.yaml --fixtures fixtures/sample_ac --out-dir output/demo
```

**לקוח אמיתי** — העתק `config.example.yaml` ל־`config.yaml`, מלא `seed_urls` (דף הבית של האתר העצמאי + כתובת המיניסייט), והרץ:

```bash
python -m zap_onboarding --config config.yaml --out-dir output/run1
```

## פלט

| קובץ | תיאור |
|------|--------|
| `output/.../client_card.md` | כרטיס לקוח למפיק בזאפ |
| `output/.../onboarding_message.txt` | תסריט/הודעה ללקוח (SMS / מייל / וואטסאפ) |
| `data/crm_events.jsonl` | תיעוד אוטומטי ב־CRM (פורמט שורות JSON) |

## גישה שבחרתי (חשיבה על דאטה ו־AI)

- **Pipeline מפורש**: סריקה → חילוץ מובנה (שדות קבועים) → סינתזה. כך קל לבדוק, ללמד מחדש קטגוריות, ולחבר עומד (Human-in-the-loop) לפני שליחה ללקוח.
- **שילוב חוקים + LLM**: חוקים מבטיחים פרטי קשר וזיהוי בסיסי גם בלי עלות API; ה־LLM משמש רק לשכבת ניסוח כשיש מפתח — מתאים לפרודקשן עם fallback.
- **אתיקה וריבוד**: השהיות בין בקשות, כיבוד `robots`/תנאי שימוש באחריות המפעיל, ואי־סתימה של אתרים זרים (רק דומיינים שנגזרו מ־seed).

## מבנה תיקיות

```
zap_onboarding/   # סריקה, חילוץ, סינתזה, CRM, CLI
fixtures/sample_ac/  # דמו: עמודי אתר + עמוד מיניסייט דמה
config.demo.yaml
config.example.yaml
```.
