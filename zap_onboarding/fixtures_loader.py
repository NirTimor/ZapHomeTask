from __future__ import annotations

from pathlib import Path

from bs4 import BeautifulSoup

from zap_onboarding.crawler import FetchedPage


def load_html_fixtures(fixtures_dir: Path) -> list[FetchedPage]:
    """טוען קבצי HTML מקומיים (הדגמה ללא רשת)."""
    out: list[FetchedPage] = []
    if not fixtures_dir.is_dir():
        return out
    for path in sorted(fixtures_dir.glob("*.html")):
        html = path.read_text(encoding="utf-8")
        soup = BeautifulSoup(html, "lxml")
        title = (soup.title.string or "").strip() if soup.title else path.stem
        for tag in soup(["script", "style", "noscript"]):
            tag.decompose()
        text = soup.get_text(separator="\n", strip=True)
        links: list[str] = []
        from urllib.parse import urljoin

        fake_base = f"https://fixture.local/{path.name}"
        for a in soup.find_all("a", href=True):
            full = urljoin(fake_base, a["href"])
            if full.startswith("http"):
                links.append(full)
        out.append(
            FetchedPage(
                url=fake_base,
                status_code=200,
                title=title,
                text_snippet=(text[:8000] if text else ""),
                html=html,
                links=links,
            )
        )
    return out
