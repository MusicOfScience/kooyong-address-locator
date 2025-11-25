"""Utility for downloading PDF files from ParlInfo RSS or XML search results.

Designed for Google Colab usage where you provide the RSS XML (local file or a
URL to fetch). The scraper:

* Parses the RSS feed items to collect ParlInfo item URLs.
* Visits each item page while impersonating a typical browser.
* Extracts likely PDF download links from the HTML.
* Saves PDFs to a chosen output directory with friendly filenames.
* Sleeps between requests and retries on transient failures.

Usage example (inside a Colab cell):

>>> !python parlinfo_pdf_scraper.py \
...     --xml-feed search_results.xml \
...     --output-dir parlinfo_pdfs \
...     --max-files 5

If you want to paste the XML directly instead of saving it to disk, pipe it
through stdin:

>>> xml_content = "<rss ...> ..."
>>> with open("feed.xml", "w") as f:
...     f.write(xml_content)
>>> !python parlinfo_pdf_scraper.py --xml-feed feed.xml --output-dir downloads
"""
from __future__ import annotations

import argparse
import random
import re
import sys
import time
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Optional
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

# Common desktop browser user agents; a random one is used for each session to
# help blend in as a real user.
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15",
    "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:120.0) Gecko/20100101 Firefox/120.0",
]

# Patterns that commonly appear in ParlInfo PDF links.
PDF_HREF_PATTERNS = (
    re.compile(r"\.pdf", re.IGNORECASE),
    re.compile(r"application%2Fpdf", re.IGNORECASE),
    re.compile(r"fileType=application/pdf", re.IGNORECASE),
)


@dataclass
class RssItem:
    """A single RSS item representing a ParlInfo search result."""

    title: str
    link: str
    pub_date: str

    def safe_filename(self) -> str:
        """Create a filesystem-safe filename using the title and pub date."""

        sanitized_title = re.sub(r"[^A-Za-z0-9_-]+", "_", self.title).strip("_")
        date_part = self.pub_date.replace(",", "").split()[0:3]
        date_str = "-".join(date_part) if date_part else "undated"
        return f"{date_str}__{sanitized_title}.pdf"


def parse_rss(xml_path: Path) -> list[RssItem]:
    """Parse an RSS XML file and return the contained items."""

    tree = ET.parse(xml_path)
    root = tree.getroot()
    channel = root.find("channel")
    if channel is None:
        return []

    items: list[RssItem] = []
    for item in channel.findall("item"):
        title = (item.findtext("title") or "untitled").strip()
        link = (item.findtext("link") or "").strip()
        pub_date = (item.findtext("pubDate") or "undated").strip()
        if link:
            items.append(RssItem(title=title, link=link, pub_date=pub_date))
    return items


def load_xml_source(xml_feed: Optional[Path], xml_url: Optional[str]) -> Path:
    """Return a local path containing the XML feed, fetching remote URLs when needed."""

    if xml_url:
        tmp_path = xml_feed if xml_feed else Path("parlinfo_feed.xml")
        print(f"Fetching XML from {xml_url} → {tmp_path}")
        response = _request_with_retries(create_session(), xml_url)
        tmp_path.write_bytes(response.content)
        return tmp_path
    if not xml_feed:
        raise ValueError("Either --xml-feed or --xml-url must be provided")
    return xml_feed


def create_session() -> requests.Session:
    """Create a configured requests session with browser-like headers."""

    session = requests.Session()
    session.headers.update(
        {
            "User-Agent": random.choice(USER_AGENTS),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
            "Cache-Control": "max-age=0",
            "Upgrade-Insecure-Requests": "1",
        }
    )
    session.verify = True
    return session


def _request_with_retries(
    session: requests.Session,
    url: str,
    method: str = "get",
    max_retries: int = 3,
    backoff: tuple[float, float] = (1.0, 3.0),
    **kwargs,
) -> requests.Response:
    """Make an HTTP request with simple jittered backoff and retries."""

    for attempt in range(1, max_retries + 1):
        try:
            response = session.request(method, url, timeout=30, **kwargs)
            response.raise_for_status()
            return response
        except requests.RequestException as exc:  # pragma: no cover - network dependent
            if attempt == max_retries:
                raise
            sleep_for = random.uniform(*backoff)
            print(f"Request failed ({exc}); retrying in {sleep_for:.1f}s...", file=sys.stderr)
            time.sleep(sleep_for)
    raise RuntimeError("Exhausted retries")


def extract_pdf_url(html: str, page_url: str) -> Optional[str]:
    """Find the most likely PDF download URL inside a ParlInfo item page."""

    soup = BeautifulSoup(html, "html.parser")

    def is_pdf_candidate(anchor: "BeautifulSoup") -> bool:
        href = anchor.get("href", "")
        text = anchor.get_text(strip=True) or ""
        link_type = anchor.get("type", "")

        if any(pattern.search(href) for pattern in PDF_HREF_PATTERNS):
            return True
        if "pdf" in text.lower():
            return True
        if "pdf" in link_type.lower():
            return True
        return False

    anchors = soup.find_all("a", href=True)
    for anchor in anchors:
        if is_pdf_candidate(anchor):
            return urljoin(page_url, anchor["href"])

    # Some pages may nest the PDF inside an iframe or object tag
    fallback_sources = []
    for tag in soup.find_all(["iframe", "object", "embed" ]):
        src = tag.get("src") or tag.get("data")
        if src and any(pattern.search(src) for pattern in PDF_HREF_PATTERNS):
            fallback_sources.append(src)

    if fallback_sources:
        return urljoin(page_url, fallback_sources[0])
    return None


def download_pdf(session: requests.Session, url: str, output_path: Path) -> None:
    """Download a PDF to the target path using streaming to limit memory use."""

    output_path.parent.mkdir(parents=True, exist_ok=True)
    response = _request_with_retries(
        session, url, stream=True, headers={"Referer": url}, max_retries=3
    )
    with output_path.open("wb") as fh:
        for chunk in response.iter_content(chunk_size=8192):
            if chunk:
                fh.write(chunk)


def scrape_pdfs(
    xml_path: Path,
    output_dir: Path,
    max_files: Optional[int] = None,
    sleep_range: tuple[float, float] = (3.0, 7.5),
) -> list[Path]:
    """Download PDFs for each item in the provided RSS XML feed."""

    items = parse_rss(xml_path)
    if max_files:
        items = items[:max_files]

    session = create_session()
    saved_paths: list[Path] = []

    for idx, item in enumerate(items, start=1):
        print(f"[{idx}/{len(items)}] Fetching {item.link}")
        try:
            item_response = _request_with_retries(
                session, item.link, headers={"Referer": item.link}
            )
        except requests.RequestException as exc:
            print(f"  ⚠️  Failed to load page: {exc}")
            continue

        pdf_url = extract_pdf_url(item_response.text, item.link)
        if not pdf_url:
            print(f"  ⚠️  No PDF link found for: {item.title}")
            continue

        filename = item.safe_filename()
        target = output_dir / filename
        print(f"  ↳ Downloading PDF from {pdf_url}")
        download_pdf(session, pdf_url, target)
        saved_paths.append(target)

        # Polite delay to mimic a real user session.
        sleep_time = random.uniform(*sleep_range)
        print(f"  ⏳ Sleeping for {sleep_time:.1f}s to appear human...")
        time.sleep(sleep_time)

    return saved_paths


def main(argv: Optional[Iterable[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description="Download ParlInfo PDFs from an RSS XML feed",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--xml-feed",
        required=False,
        type=Path,
        help="Path to the RSS XML feed file exported from ParlInfo",
    )
    parser.add_argument(
        "--xml-url",
        required=False,
        help="Download the RSS XML feed directly from a ParlInfo search URL",
    )
    parser.add_argument(
        "--output-dir",
        required=True,
        type=Path,
        help="Directory where PDF files will be saved",
    )
    parser.add_argument(
        "--max-files",
        type=int,
        default=None,
        help="Limit the number of files to download (useful for testing)",
    )
    parser.add_argument(
        "--min-delay",
        type=float,
        default=3.0,
        help="Minimum delay between downloads (seconds)",
    )
    parser.add_argument(
        "--max-delay",
        type=float,
        default=7.5,
        help="Maximum delay between downloads (seconds)",
    )

    args = parser.parse_args(list(argv) if argv is not None else None)

    try:
        xml_path = load_xml_source(args.xml_feed, args.xml_url)
    except ValueError as exc:
        parser.error(str(exc))

    if args.min_delay > args.max_delay:
        parser.error("--min-delay cannot be greater than --max-delay")

    try:
        saved = scrape_pdfs(
            xml_path=xml_path,
            output_dir=args.output_dir,
            max_files=args.max_files,
            sleep_range=(args.min_delay, args.max_delay),
        )
    except Exception as exc:  # pragma: no cover - runtime convenience
        print(f"Download failed: {exc}", file=sys.stderr)
        return 1

    print(f"Completed. Saved {len(saved)} PDF(s) to {args.output_dir}")
    return 0


if __name__ == "__main__":  # pragma: no cover - CLI entrypoint
    raise SystemExit(main())
