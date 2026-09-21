"""Read-only access to the question bank. This is the only module that contains SQL."""
from __future__ import annotations

import json
import sqlite3
from contextlib import closing
from typing import Iterable

from . import config
from .models import Question

# Which question statuses may be served. 'needs_review' is never served.
_STATUSES = {False: ("verified",), True: ("verified", "draft")}


class QuestionBankError(RuntimeError):
    """The question database is missing or unreadable."""


def _connect() -> sqlite3.Connection:
    path = config.DB_PATH
    if not path.is_file():
        raise QuestionBankError(
            f"Question database not found at {path}. "
            "Run `python scripts/create_db.py` and `python scripts/load_data.py` first."
        )
    con = sqlite3.connect(f"{path.resolve().as_uri()}?mode=ro", uri=True)  # read-only: safe on read-only hosts
    con.row_factory = sqlite3.Row
    return con


def chapter_counts(include_unverified: bool) -> dict[int, int]:
    """Number of servable questions per chapter."""
    statuses = _STATUSES[include_unverified]
    marks = ",".join("?" * len(statuses))
    with closing(_connect()) as con:
        rows = con.execute(
            f"SELECT chapter, COUNT(*) AS n FROM questions WHERE status IN ({marks}) "
            "GROUP BY chapter ORDER BY chapter",
            statuses,
        ).fetchall()
    return {r["chapter"]: r["n"] for r in rows}


def load_questions(chapters: Iterable[int], include_unverified: bool) -> list[Question]:
    """All servable questions in the given chapters (random selection happens in service.py)."""
    chapters = list(chapters)
    if not chapters:
        return []
    statuses = _STATUSES[include_unverified]
    ch_marks = ",".join("?" * len(chapters))
    st_marks = ",".join("?" * len(statuses))
    with closing(_connect()) as con:
        rows = con.execute(
            "SELECT id, chapter, number, stem_md, image_path, options_json, correct, explanation_md "
            f"FROM questions WHERE chapter IN ({ch_marks}) AND status IN ({st_marks}) "
            "ORDER BY chapter, number",
            [*chapters, *statuses],
        ).fetchall()
    return [
        Question(
            id=r["id"],
            chapter=r["chapter"],
            number=r["number"],
            stem_md=r["stem_md"],
            image_path=r["image_path"],
            options=json.loads(r["options_json"]),
            correct=r["correct"],
            explanation_md=r["explanation_md"],
        )
        for r in rows
    ]
