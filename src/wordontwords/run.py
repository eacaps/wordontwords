"""CLI runner for the wordontwords Hamilton DAG.

Builds a Hamilton driver from :mod:`wordontwords.dataflow`, executes the
requested outputs, and writes the resulting word list to JSON.

Examples
--------
Run with defaults (writes ./dist/word-list.json)::

    python -m wordontwords.run

Point at a different source and output, pin the date, and draw the DAG::

    python -m wordontwords.run \\
        --source-url https://www.fiveforks.com/wordle/block/ \\
        --output out/word-list.json \\
        --reference-date 2026-10-14 \\
        --visualize dist/dag.png
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Optional

from hamilton import driver

from wordontwords import dataflow

DEFAULT_OUTPUT = Path("dist/word-list.json")


def build_driver() -> "driver.Driver":
    """Construct the Hamilton driver for the ingestion dataflow."""
    return driver.Builder().with_modules(dataflow).build()


def run(
    source_url_override: Optional[str] = None,
    reference_date: Optional[str] = None,
    request_timeout: float = 30.0,
) -> dict:
    """Execute the DAG and return the ``{"words", "lastUpdated"}`` payload."""
    dr = build_driver()
    inputs = {"request_timeout": request_timeout}
    if source_url_override is not None:
        inputs["source_url_override"] = source_url_override
    if reference_date is not None:
        inputs["reference_date"] = reference_date

    results = dr.execute(
        final_vars=["word_list_payload", "word_count"],
        inputs=inputs,
    )
    payload = results["word_list_payload"]
    print(f"Ingested {results['word_count']} words (lastUpdated={payload['lastUpdated']})")
    return payload


def write_payload(payload: dict, output: Path) -> None:
    """Write the payload to ``output`` as pretty-printed JSON."""
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {output}")


def visualize(output: Path) -> None:
    """Render the DAG to an image file (requires the 'viz' extra)."""
    dr = build_driver()
    output.parent.mkdir(parents=True, exist_ok=True)
    dr.display_all_functions(str(output))
    print(f"Wrote DAG visualization to {output}")


def parse_args(argv: Optional[list[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Ingest used Wordle words via a Hamilton DAG.")
    parser.add_argument(
        "--source-url",
        dest="source_url",
        default=None,
        help="Override the block list page to scrape.",
    )
    parser.add_argument(
        "--reference-date",
        dest="reference_date",
        default=None,
        help="Pin the lastUpdated stamp (YYYY-MM-DD) for reproducible runs.",
    )
    parser.add_argument(
        "--request-timeout",
        dest="request_timeout",
        type=float,
        default=30.0,
        help="HTTP request timeout in seconds (default: 30).",
    )
    parser.add_argument(
        "--output",
        dest="output",
        type=Path,
        default=DEFAULT_OUTPUT,
        help=f"Where to write the word list JSON (default: {DEFAULT_OUTPUT}).",
    )
    parser.add_argument(
        "--visualize",
        dest="visualize",
        type=Path,
        default=None,
        help="Also render the DAG to this image path (requires the 'viz' extra).",
    )
    return parser.parse_args(argv)


def main(argv: Optional[list[str]] = None) -> int:
    args = parse_args(argv)
    try:
        payload = run(
            source_url_override=args.source_url,
            reference_date=args.reference_date,
            request_timeout=args.request_timeout,
        )
        write_payload(payload, args.output)
        if args.visualize is not None:
            visualize(args.visualize)
    except Exception as exc:  # surface a clean message, non-zero exit for CI
        print(f"error: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
