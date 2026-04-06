from __future__ import annotations

import time
from collections import deque
from dataclasses import dataclass, field
from typing import Iterable
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup


@dataclass
class FetchedPage:
    url: str
    status_code: int | None
    title: str
    text_snippet: str
    html: str
    links: list[str] = field(default_factory=list)
    error: str | None = None


def same_registrable_domain(url: str, base_netloc: str) -> bool:
    """מאפשר מעקב אחרי קישורים באותו host (כולל www)."""
    p = urlparse(url)
    if not p.netloc:
        return True
    b = urlparse(base_netloc if base_netloc.startswith("http") else f"https://{base_netloc}/")
    a, bb = p.netloc.lower(), b.netloc.lower()
    if a == bb:
        return True
    if a.replace("www.", "") == bb.replace("www.", ""):
        return True
    return False


def normalize_url(base: str, href: str) -> str | None:
    if not href or href.startswith(("#", "javascript:", "mailto:", "tel:")):
        return None
    full = urljoin(base, href)
    p = urlparse(full)
    if p.scheme not in ("http", "https"):
        return None
    return full.split("#")[0].rstrip("/") or full


def fetch_url(session: requests.Session, url: str, timeout: float, user_agent: str) -> FetchedPage:
    try:
        r = session.get(
            url,
            timeout=timeout,
            headers={"User-Agent": user_agent, "Accept-Language": "he,en;q=0.9"},
        )
        ctype = (r.headers.get("Content-Type") or "").lower()
        if "text/html" not in ctype and r.status_code == 200:
            return FetchedPage(
                url=url,
                status_code=r.status_code,
                title="",
                text_snippet="",
                html="",
                links=[],
                error=f"skip non-html: {ctype}",
            )
        r.raise_for_status()
        html = r.text or ""
        soup = BeautifulSoup(html, "lxml")
        title = (soup.title.string or "").strip() if soup.title else ""
        for tag in soup(["script", "style", "noscript"]):
            tag.decompose()
        text = soup.get_text(separator="\n", strip=True)
        snippet = text[:8000] if text else ""
        links: list[str] = []
        for a in soup.find_all("a", href=True):
            nu = normalize_url(url, a["href"])
            if nu:
                links.append(nu)
        return FetchedPage(
            url=url,
            status_code=r.status_code,
            title=title,
            text_snippet=snippet,
            html=html,
            links=links,
        )
    except Exception as e:
        return FetchedPage(
            url=url,
            status_code=None,
            title="",
            text_snippet="",
            html="",
            error=str(e),
        )


def crawl(
    seed_urls: Iterable[str],
    max_pages: int,
    timeout_seconds: float,
    user_agent: str,
    polite_delay_sec: float = 0.4,
) -> list[FetchedPage]:
    session = requests.Session()
    seen: set[str] = set()
    queue: deque[str] = deque()
    for u in seed_urls:
        nu = normalize_url(u, u) or u.rstrip("/")
        if nu:
            queue.append(nu)
    results: list[FetchedPage] = []
    seeds_parsed = [urlparse(normalize_url(s, s) or s) for s in seed_urls]

    while queue and len(results) < max_pages:
        url = queue.popleft()
        if url in seen:
            continue
        seen.add(url)
        page = fetch_url(session, url, timeout_seconds, user_agent)
        results.append(page)
        time.sleep(polite_delay_sec)
        if page.error or not page.html:
            continue
        base_host = urlparse(url).netloc
        allow_follow = any(
            same_registrable_domain(url, f"{sp.scheme}://{sp.netloc}/") for sp in seeds_parsed
        )
        if not allow_follow:
            continue
        for link in page.links:
            if link in seen:
                continue
            if not any(same_registrable_domain(link, f"{sp.scheme}://{sp.netloc}/") for sp in seeds_parsed):
                continue
            if len(seen) + len(queue) < max_pages * 3:
                queue.append(link)

    return results
