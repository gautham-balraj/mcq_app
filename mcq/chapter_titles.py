"""Optional chapter titles, read from data/chapters.json, e.g. {"1": "Pituitary Gland and Hypothalamus"}.

A missing file, a malformed file or a chapter without an entry simply falls back to "Chapter N".
"""
import json

from . import config


def load() -> dict[int, str]:
    path = config.DATA_DIR / "chapters.json"
    if not path.is_file():
        return {}
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    if not isinstance(raw, dict):
        return {}
    return {int(k): str(v).strip() for k, v in raw.items() if str(k).strip().isdigit() and str(v).strip()}


def label(chapter: int, n_questions: int, titles: dict[int, str]) -> str:
    """'1. Pituitary Gland and Hypothalamus · 64 questions', or 'Chapter 1 · 64 questions' if untitled."""
    title = titles.get(chapter)
    prefix = f"{chapter}. {title}" if title else f"Chapter {chapter}"
    return f"{prefix} · {n_questions} questions"