"""wordontwords: a Hamilton DAG that ingests used Wordle words.

Mirrors the ingestion done by https://github.com/eacaps/wordle-words:
scrape the fiveforks.com block list, parse out the words, and emit a
``{"words": [...], "lastUpdated": "YYYY-MM-DD"}`` payload.
"""

__version__ = "0.1.0"
