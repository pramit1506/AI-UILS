"""Local, bounded query expansion. Reads vocabulary only, never document data."""
import sqlite3
from contextlib import closing
from functools import lru_cache
from pathlib import Path

LEXICON = Path(__file__).resolve().parents[1] / "search_data" / "wordnet.lexicon"
TOPICS = (
    ("medicine", "medical", "healthcare", "clinical", "medication"),
    ("cardio", "cardiac", "cardiology", "cardiovascular"),
    ("invoice", "billing", "bill"),
    ("resume", "résumé", "cv"),
)


@lru_cache(maxsize=4096)
def related_terms(word: str) -> list[str]:
    words = [word]
    if word.isascii() and word.isalpha() and len(word) >= 3:
        with closing(sqlite3.connect(LEXICON.as_uri() + "?mode=ro&immutable=1", uri=True)) as db:
            row = db.execute("SELECT terms FROM synonym WHERE word = ?", (word,)).fetchone()
        if row:
            words.extend(row[0].split())
    for group in TOPICS:
        if word in group:
            words.extend(group)
    return list(dict.fromkeys(words))
