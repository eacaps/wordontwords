# wordontwords

A [Hamilton](https://hamilton.dagworks.io/) DAG that ingests the list of
already-used Wordle words. It mirrors the ingestion done by
[eacaps/wordle-words](https://github.com/eacaps/wordle-words): scrape the
[fiveforks.com block list](https://www.fiveforks.com/wordle/block/), parse out
the words, and emit a `{"words": [...], "lastUpdated": "YYYY-MM-DD"}` payload.

## The DAG

Each function in `src/wordontwords/dataflow.py` is a node; a node's parameters
are its upstream dependencies, so Hamilton wires the graph automatically:

```
source_url ──> raw_html ──> block_list_text ──> words ──┐
                                                        ├──> word_list_payload
reference_date ──> last_updated ────────────────────────┘
```

| Node | What it does |
| --- | --- |
| `source_url` | Resolves the page to scrape (defaults to the fiveforks block list; override with `source_url_override`). |
| `raw_html` | `GET`s the page HTML. |
| `block_list_text` | Reads the inner text of the `#blist` element. |
| `words` | Splits the text into tokens, keeps 5-letter uppercase words, de-dupes and sorts them. |
| `last_updated` | Stamps the run with yesterday's date (UTC), matching the source project. Override with `reference_date`. |
| `word_count` | Count of unique words (useful for logging/metrics). |
| `word_list_payload` | Final `{"words", "lastUpdated"}` dict. |

## Install

This project uses [uv](https://docs.astral.sh/uv/) for dependency and
environment management. [Install uv](https://docs.astral.sh/uv/getting-started/installation/)
first, then:

```bash
# create .venv and install everything from uv.lock (incl. this package)
uv sync

# optional, for DAG visualization (requires graphviz on your system):
# uv sync --extra viz
```

For a reproducible, lockfile-is-law install (e.g. in CI), use:

```bash
uv sync --locked
```

## Run

```bash
# writes ./dist/word-list.json using the live source
uv run wordontwords

# or invoke the module directly
uv run python -m wordontwords.run
```

Useful flags:

```bash
uv run wordontwords \
  --source-url https://www.fiveforks.com/wordle/block/ \
  --output out/word-list.json \
  --reference-date 2026-10-14 \
  --visualize dist/dag.png
```

| Flag | Purpose |
| --- | --- |
| `--source-url` | Scrape a different page or a saved HTML fixture served over http(s). |
| `--reference-date` | Pin the `lastUpdated` stamp (`YYYY-MM-DD`) for reproducible runs. |
| `--request-timeout` | HTTP timeout in seconds (default 30). |
| `--output` | Where to write the JSON (default `dist/word-list.json`). |
| `--visualize` | Also render the DAG to an image (needs the `viz` extra + graphviz). |

## Using the DAG from Python

Run this inside the project environment (e.g. `uv run python script.py`, or
after `source .venv/bin/activate`):

```python
from hamilton import driver
from wordontwords import dataflow

dr = driver.Builder().with_modules(dataflow).build()
payload = dr.execute(["word_list_payload"])["word_list_payload"]
print(len(payload["words"]), payload["lastUpdated"])
```
