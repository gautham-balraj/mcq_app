import base64
import json
import sqlite3
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from mcq import config  # noqa: E402

_PNG = base64.b64decode(  # 1x1 PNG
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChwGA60e6kgAAAABJRU5ErkJggg=="
)


def _row(chapter: int, number: int, status: str, correct: str = "B", image: str | None = None):
    stem = f"Question {number} in chapter {chapter}.\n\n" + ("{{image}}\n\n" if image else "") + "**Which one?**"
    options = {k: f"Option {k}" for k in config.LETTERS}
    return (chapter, number, stem, image, json.dumps(options), correct,
            f"Explanation {chapter}.{number}\n\n| a | b |\n|---|---|\n| 1 | 2 |", None, status)


@pytest.fixture()
def bank(tmp_path, monkeypatch):
    """A throwaway question bank: chapter 1 has 5 verified + 2 draft, chapter 2 has 4 verified + 1 needs_review."""
    db = tmp_path / "qbank.db"
    con = sqlite3.connect(db)
    con.executescript((ROOT / "scripts" / "schema.sql").read_text())
    rows = [_row(1, n, "verified", image="images/ch01/q001.png" if n == 1 else None) for n in range(1, 6)]
    rows += [_row(1, n, "draft") for n in (6, 7)]
    rows += [_row(2, n, "verified", correct="A") for n in range(1, 5)]
    rows += [_row(2, 5, "needs_review")]
    con.executemany(
        "INSERT INTO questions (chapter, number, stem_md, image_path, options_json, correct, explanation_md, review_note, status) "
        "VALUES (?,?,?,?,?,?,?,?,?)", rows)
    con.commit()
    con.close()
    (tmp_path / "images" / "ch01").mkdir(parents=True)
    (tmp_path / "images" / "ch01" / "q001.png").write_bytes(_PNG)
    monkeypatch.setattr(config, "DB_PATH", db)
    monkeypatch.setattr(config, "DATA_DIR", tmp_path)
    return db
