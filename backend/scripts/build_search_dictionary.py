"""Build the bundled SQLite lexicon from npm pack wordnet-db@3.1.14."""
import sqlite3
import sys
import tarfile
from itertools import takewhile
from pathlib import Path

destination = Path(__file__).resolve().parents[1] / "app" / "search_data"
destination.mkdir(exist_ok=True)
with tarfile.open(sys.argv[1]) as archive, sqlite3.connect(destination / "wordnet.lexicon") as db:
    db.execute("DROP TABLE IF EXISTS synonym")
    db.execute("CREATE TABLE synonym (word TEXT PRIMARY KEY, terms TEXT NOT NULL) WITHOUT ROWID")
    for pos in ("noun", "verb", "adj", "adv"):
        data = {}
        for line in archive.extractfile(f"package/dict/data.{pos}"):
            if line.startswith(b" "):
                continue
            parts = line.decode().split(" | ")[0].split()
            count = int(parts[3], 16)
            data[parts[0]] = [w.lower() for w in parts[4:4 + 2 * count:2] if w.isalpha()]
        for line in archive.extractfile(f"package/dict/index.{pos}"):
            if line.startswith(b" "):
                continue
            parts = line.decode().split()
            word = parts[0]
            if not word.isalpha():
                continue
            # First sense is the most frequent. Limit broad or ambiguous expansions.
            offset = parts[6 + int(parts[3])]
            terms = list(dict.fromkeys(w for w in data[offset] if w != word))[:6]
            if terms:
                db.execute("INSERT OR IGNORE INTO synonym VALUES (?, ?)", (word, " ".join(terms)))
    with archive.extractfile("package/dict/data.noun") as source:
        notice = [line.decode().lstrip().split(" ", 1)[-1].rstrip() for line in takewhile(lambda line: line.startswith(b"  "), source)]
    (destination / "WORDNET-LICENSE.txt").write_text("\n".join(notice) + "\n\n" +
        archive.extractfile("package/LICENSE").read().decode(), encoding="utf-8")
