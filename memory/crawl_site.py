"""
Crawl https://vishnesh.netlify.app (SPA) with Playwright — optional/offline utility.

`knowledge.pipeline.build_knowledge_base` can run this before indexing when
`CRAWL_SITE_ON_BUILD=true` (default). Outputs are merged into RAG via
`data/crawled_site.md` (see `rag.document_loader.load_documents`).

Requires: pip install playwright && playwright install chromium

Usage (from repo root):
  python memory/crawl_site.py
  python memory/crawl_site.py --rebuild-index   # rebuild FAISS from current data/ only
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import deque
from pathlib import Path

BASE = "https://vishnesh.netlify.app"


def _normalize_url(url: str) -> str:
    u = url.strip()
    if u.rstrip("/") == BASE.rstrip("/"):
        return BASE
    return u.rstrip("/") if u.startswith(BASE + "/") else u

# Same allowlist as the original JS (including legacy typo).
_SKILL_TOKENS = frozenset(
    {
        "Python",
        "JAVA",
        "HTML",
        "CSS",
        "javascript",
        "Reactjs",
        "Node.js",
        "Bootstarp",
    }
)

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"
OUTPUT_JSON = Path(__file__).resolve().parent / "crawl_output.json"
OUTPUT_MD = DATA_DIR / "crawled_site.md"


def extract_projects(text: str) -> list[dict]:
    blocks = text.split("Title :")
    out: list[dict] = []
    for block in blocks[1:]:
        lines = [ln.strip() for ln in block.split("\n")]
        out.append(
            {
                "title": lines[0] if lines else "",
                "technologies": next((l for l in lines if "Technologies" in l), ""),
                "description": next((l for l in lines if "Description" in l), ""),
            }
        )
    return out


def extract_skills(text: str) -> list[str]:
    return [
        t
        for t in (ln.strip() for ln in text.split("\n"))
        if t in _SKILL_TOKENS
    ]


def extract_certificates(text: str) -> list[str]:
    return [
        t
        for t in (ln.strip() for ln in text.split("\n"))
        if (
            "Data" in t
            or "Python" in t
            or "AI" in t
            or "Java" in t
            or "analytics" in t
        )
    ]


def auto_scroll(page) -> None:
    page.evaluate(
        """async () => {
            await new Promise((resolve) => {
                let totalHeight = 0;
                const distance = 100;
                const timer = setInterval(() => {
                    window.scrollBy(0, distance);
                    totalHeight += distance;
                    if (totalHeight >= document.body.scrollHeight) {
                        clearInterval(timer);
                        resolve();
                    }
                }, 100);
            });
        }"""
    )


def _page_payload(page) -> dict:
    return page.evaluate(
        """() => {
            const clean = (el) => (el && el.innerText ? el.innerText.trim() : "");
            return {
                title: document.title,
                headings: Array.from(document.querySelectorAll("h1,h2,h3"))
                    .map(clean)
                    .filter(Boolean),
                links: Array.from(document.querySelectorAll("a")).map((a) => ({
                    text: (a.innerText || "").trim(),
                    href: a.href,
                })),
                images: Array.from(document.querySelectorAll("img")).map((img) => img.src),
                fullText: document.body ? document.body.innerText : "",
            };
        }"""
    )


def _render_markdown(results: list[dict]) -> str:
    lines = [
        "# Site crawl (generated)",
        "",
        f"Base: {BASE}",
        "",
    ]
    for i, row in enumerate(results, 1):
        url = row.get("url", "")
        title = row.get("title", "")
        lines.append(f"## Page {i}: {title or url}")
        lines.append("")
        lines.append(f"- **URL:** {url}")
        st = row.get("structured") or {}
        projects = st.get("projects") or []
        if projects:
            lines.append("### Projects (parsed)")
            for p in projects:
                lines.append(f"- **{p.get('title', '')}**")
                if p.get("technologies"):
                    lines.append(f"  - {p['technologies']}")
                if p.get("description"):
                    lines.append(f"  - {p['description']}")
            lines.append("")
        skills = st.get("skills") or []
        if skills:
            lines.append("### Skills (parsed)")
            lines.append(", ".join(skills))
            lines.append("")
        certs = st.get("certificates") or []
        if certs:
            lines.append("### Certificates (parsed)")
            for c in certs:
                lines.append(f"- {c}")
            lines.append("")
        headings = row.get("headings") or []
        if headings:
            lines.append("### Headings")
            for h in headings:
                lines.append(f"- {h}")
            lines.append("")
        ft = (row.get("full_text") or "").strip()
        if ft:
            lines.append("### Page text")
            lines.append("")
            lines.append(ft)
            lines.append("")
    return "\n".join(lines).strip() + "\n"


def crawl_site() -> list[dict]:
    from playwright.sync_api import sync_playwright

    visited: set[str] = set()
    results: list[dict] = []
    queue: deque[str] = deque([BASE])

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            args=["--no-sandbox", "--disable-setuid-sandbox"],
        )
        page = browser.new_page()
        try:
            while queue:
                url = _normalize_url(queue.popleft())
                if url in visited:
                    continue
                visited.add(url)
                print("Visiting:", url)
                try:
                    page.goto(url, wait_until="networkidle", timeout=60_000)
                    # Some SPAs keep <body> hidden; attached is enough for text extraction.
                    page.wait_for_selector("body", state="attached", timeout=60_000)
                    auto_scroll(page)
                    page.wait_for_timeout(1500)

                    data = _page_payload(page)
                    structured = {
                        "projects": extract_projects(data["fullText"]),
                        "skills": extract_skills(data["fullText"]),
                        "certificates": extract_certificates(data["fullText"]),
                    }
                    results.append(
                        {
                            "url": url,
                            "title": data["title"],
                            "headings": data["headings"],
                            "links": data["links"],
                            "images": data["images"],
                            "full_text": data["fullText"],
                            "structured": structured,
                        }
                    )

                    for link in data["links"]:
                        href = _normalize_url((link.get("href") or "").strip())
                        if href.startswith(BASE) and href not in visited:
                            queue.append(href)
                except Exception as e:
                    print("Error:", url, e, file=sys.stderr)
        finally:
            browser.close()

    return results


def write_outputs(results: list[dict]) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUT_JSON.write_text(json.dumps(results, indent=2, ensure_ascii=False), encoding="utf-8")
    OUTPUT_MD.write_text(_render_markdown(results), encoding="utf-8")
    print(f"\nWrote {OUTPUT_JSON}")
    print(f"Wrote {OUTPUT_MD}")


def run_crawl_and_write() -> dict:
    """
    Run crawl + write JSON/Markdown. Does not raise; safe for the knowledge pipeline.

    Returns:
        {"success": bool, "pages": int, "error": str | None}
    """
    try:
        results = crawl_site()
        write_outputs(results)
        return {"success": True, "pages": len(results), "error": None}
    except Exception as e:
        return {"success": False, "pages": 0, "error": str(e)}


def main() -> None:
    parser = argparse.ArgumentParser(description="Crawl personal site into data/ for RAG.")
    parser.add_argument(
        "--rebuild-index",
        action="store_true",
        help="Rebuild FAISS index after crawl (uses rag.vector_store.build_vector_store).",
    )
    args = parser.parse_args()

    results = crawl_site()
    write_outputs(results)

    if args.rebuild_index:
        from rag.vector_store import build_vector_store

        build_vector_store()


if __name__ == "__main__":
    main()
