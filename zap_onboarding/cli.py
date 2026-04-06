from __future__ import annotations

import argparse
import sys
from pathlib import Path

import yaml

from zap_onboarding.crawler import crawl
from zap_onboarding.crm import log_event
from zap_onboarding.extract import extract_from_pages
from zap_onboarding.fixtures_loader import load_html_fixtures
from zap_onboarding.synthesize import build_outputs


def main(argv: list[str] | None = None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(encoding="utf-8")
        except Exception:
            pass
    p = argparse.ArgumentParser(description="אוטומציית Onboarding — סריקה, חילוץ, כרטיס לקוח ותסריט")
    p.add_argument("--config", default="config.yaml", help="קובץ YAML (העתק מ-config.example.yaml)")
    p.add_argument(
        "--fixtures",
        default=None,
        help="תיקייה עם קבצי .html במקום סריקת רשת (הדגמה)",
    )
    p.add_argument("--out-dir", default="output", help="תיקיית פלט")
    p.add_argument("--crm-log", default="data/crm_events.jsonl", help="קובץ JSONL לרישום CRM")
    args = p.parse_args(argv)

    cfg_path = Path(args.config)
    if not cfg_path.is_file():
        print(f"חסר קובץ config: {cfg_path} — העתק config.example.yaml ל-config.yaml", file=sys.stderr)
        return 2

    cfg = yaml.safe_load(cfg_path.read_text(encoding="utf-8")) or {}
    customer = cfg.get("customer") or {}
    seeds = cfg.get("seed_urls") or []
    crawl_cfg = cfg.get("crawl") or {}

    if not args.fixtures and not seeds:
        print("אין seed_urls בקונפיגורציה (או השתמשו ב- --fixtures).", file=sys.stderr)
        return 2

    display = customer.get("display_name", "לקוח")
    segment = customer.get("segment", "SMB")
    region = customer.get("region", "אזור הקריות")
    max_pages = int(crawl_cfg.get("max_pages", 12))
    timeout = float(crawl_cfg.get("timeout_seconds", 15))
    ua = str(crawl_cfg.get("user_agent", "ZapOnboardingBot/1.0"))

    if args.fixtures:
        pages = load_html_fixtures(Path(args.fixtures))
        if not pages:
            print(f"לא נמצאו קבצי HTML ב-{args.fixtures}", file=sys.stderr)
            return 2
    else:
        pages = crawl(
            seed_urls=seeds,
            max_pages=max_pages,
            timeout_seconds=timeout,
            user_agent=ua,
        )
    profile = extract_from_pages(pages, region_hint=region)
    card, script, synth_source = build_outputs(display, segment, profile)

    out = Path(args.out_dir)
    out.mkdir(parents=True, exist_ok=True)
    (out / "client_card.md").write_text(card, encoding="utf-8")
    (out / "onboarding_message.txt").write_text(script, encoding="utf-8")

    log_event(
        Path(args.crm_log),
        event_type="onboarding_pack_generated",
        customer_key=display,
        payload={
            "synth_source": synth_source,
            "pages_scanned": len(pages),
            "source_urls": profile.source_urls,
            "has_phones": bool(profile.phones),
        },
    )

    print(f"נשמר: {out / 'client_card.md'}")
    print(f"נשמר: {out / 'onboarding_message.txt'}")
    print(f"נרשם CRM: {args.crm_log}")
    print(f"מקור ניסוח: {synth_source}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
