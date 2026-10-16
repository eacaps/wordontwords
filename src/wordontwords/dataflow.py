"""Hamilton dataflow for ingesting used Wordle words.

Each function in this module is a node in the DAG. A node's parameters are
its upstream dependencies (matched by name), so Hamilton wires the graph
automatically:

    source_url ─┐
                ├─> raw_html ─> block_list_text ─> words ─┐
                                                          ├─> word_list_payload
    reference_date ─> last_updated ───────────────────────┘

This mirrors the TypeScript ingestion in eacaps/wordle-words:
  1. fetch HTML from the fiveforks.com block list page
  2. read the inner text of the ``#blist`` element
  3. drop the trailing non-word lines, then split the rest into words
  4. emit ``{"words": [...], "lastUpdated": "YYYY-MM-DD"}``
"""

from __future__ import annotations

import re
from datetime import date, datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

import requests
from bs4 import BeautifulSoup

#: Default page the Wordle block list is scraped from.
DEFAULT_SOURCE_URL = "https://www.fiveforks.com/wordle/block/"

#: CSS id of the element that holds the alphabetical block list of words.
BLOCK_LIST_SELECTOR = "#blist"

#: Wordle answers are 5 uppercase letters. Used to validate parsed tokens.
_WORD_RE = re.compile(r"^[A-Z]{5}$")


def source_url(source_url_override: Optional[str] = None) -> str:
    """The URL to scrape the block list from.

    Pass ``source_url_override`` as an input to point at a different page or a
    saved HTML fixture served over http(s).
    """
    return source_url_override or DEFAULT_SOURCE_URL


def raw_html(source_url: str, request_timeout: float = 30.0) -> str:
    """Fetch the raw HTML of the block list page."""
    response = requests.get(
        source_url,
        timeout=request_timeout,
        headers={"User-Agent": "wordontwords-hamilton-dag/0.1 (+https://github.com/eacaps/wordontwords)"},
    )
    response.raise_for_status()
    return response.text


def block_list_text(raw_html: str) -> str:
    """Extract the inner text of the ``#blist`` element.

    Raises if the element is missing, matching the source project's behaviour.
    """
    soup = BeautifulSoup(raw_html, "lxml")
    block = soup.select_one(BLOCK_LIST_SELECTOR)
    if block is None:
        raise ValueError(f"block list element '{BLOCK_LIST_SELECTOR}' not found in page")
    # separator="\n" reproduces the line-per-row innerText the TS parser relied on.
    return block.get_text(separator="\n")


def words(block_list_text: str) -> List[str]:
    """Parse the block list text into a sorted, de-duplicated list of words.

    The source parser splits on whitespace and keeps non-empty tokens. We add a
    5-uppercase-letter guard so stray markup/footer text can't leak in, then
    sort and de-dupe for a stable, deterministic result.
    """
    found: set[str] = set()
    for line in block_list_text.splitlines():
        for token in line.split():
            candidate = token.strip().upper()
            if _WORD_RE.match(candidate):
                found.add(candidate)
    return sorted(found)


def last_updated(reference_date: Optional[str] = None) -> str:
    """The ingestion date stamp as ``YYYY-MM-DD``.

    Mirrors the source project, which stamps the list with "yesterday" (UTC) to
    reflect that the block list lags one day behind the current puzzle. Pass
    ``reference_date`` (``YYYY-MM-DD``) to override, e.g. for reproducible runs.
    """
    if reference_date is not None:
        # Validate the override is a real date in the expected format.
        datetime.strptime(reference_date, "%Y-%m-%d")
        return reference_date
    yesterday: date = datetime.now(timezone.utc).date() - timedelta(days=1)
    return yesterday.isoformat()


def word_count(words: List[str]) -> int:
    """Number of unique words ingested (handy for logging/metrics)."""
    return len(words)


def word_list_payload(words: List[str], last_updated: str) -> Dict[str, Any]:
    """The final payload, matching the shape produced by eacaps/wordle-words."""
    return {"words": words, "lastUpdated": last_updated}
